"""Nominal undirected road sensitivity; never writes final results or manuscript.

Approved under KILA-D-20260920-010. Network-only length selects donors;
off-network geometric connectors are separate diagnostics, not verified access.
"""
from collections import Counter, defaultdict
from heapq import heappop, heappush
from pathlib import Path
import hashlib
import json
import math

import numpy as np
import pandas as pd
from pyproj import Transformer
import shapely
from shapely.ops import substring

from figure_toilet_rebalancing_performance_under_resource_mobility_scenarios import (
    construct_screen, donor_capacity, evaluate_scenario, haversine_km,
)
from figure_provisional_emergency_toilet_rebalancing_plan import full_mobility_flows

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / 'data/processed/revision_road_inputs'
OUT = ROOT / 'data/exp/revision-road-comparison'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shortest(graph, start, targets):
    """Dijkstra retaining parallel segments; stop only after all targets settle."""
    dist = {start: 0.0}
    prev = {}
    queue = [(0.0, start)]
    pending = set(targets)
    while queue and pending:
        cost, node = heappop(queue)
        if cost != dist[node]:
            continue
        pending.discard(node)
        for other, length, segment in graph[node]:
            candidate = cost + length
            if candidate < dist.get(other, math.inf):
                dist[other] = candidate
                prev[other] = (node, segment)
                heappush(queue, (candidate, other))
    return dist, prev


def allocate(screen, scenario, distance):
    capacities = donor_capacity(screen, scenario)
    initial = capacities.copy()
    residual = screen['Screening Shortfall'].astype(int).to_dict()
    recipients = screen.loc[screen['Screening Shortfall'].gt(0)].sort_values(
        ['Verification Tier', 'Screening Shortfall',
         'Estimated Functional Support Evacuees',
         'Estimated Female Functional Support Evacuees', 'Evacuees', 'Shelter Number'],
        ascending=[True, False, False, False, False, True], kind='stable')
    flows = []
    for r in recipients.index:
        while residual[r] > 0:
            eligible = [d for d, cap in capacities.items()
                        if cap > 0 and d != r and math.isfinite(distance[d, r])]
            if not eligible:
                break
            d = min(eligible, key=lambda i: (distance[i, r], int(screen.loc[i, 'Shelter Number'])))
            quantity = min(capacities[d], residual[r])
            capacities[d] -= quantity
            residual[r] -= quantity
            flows.append((int(d), int(r), int(quantity)))
    incoming, outgoing = Counter(), Counter()
    for d, r, q in flows:
        assert q > 0 and isinstance(q, int)
        outgoing[d] += q
        incoming[r] += q
    for i in screen.index:
        assert outgoing[i] <= initial[i]
        assert incoming[i] <= int(screen.loc[i, 'Screening Shortfall'])
        assert residual[i] == int(screen.loc[i, 'Screening Shortfall']) - incoming[i]
        inventory = int(screen.loc[i, 'Temporary Toilets Installed']) + incoming[i] - outgoing[i]
        assert inventory >= 0
        if outgoing[i]:
            assert inventory >= int(screen.loc[i, 'Prolonged Requirement'])
    assert sum(incoming.values()) == sum(outgoing.values())
    assert sum(residual.values()) + sum(incoming.values()) == int(screen['Screening Shortfall'].sum())
    resolved = [i for i in recipients.index if residual[i] == 0]
    transferred = sum(incoming.values())
    metrics = {
        'Scenario': scenario, 'Eligible Donor Units': sum(initial.values()),
        'Transferred Units': transferred, 'Residual Screening Shortfall': sum(residual.values()),
        'Shelters with Residual Shortfall': sum(v > 0 for v in residual.values()),
        'Resolved Shelter Count': len(resolved),
        'Mean Transfer Distance': sum(q * distance[d, r] for d, r, q in flows) / transferred if transferred else 0.0,
        'Maximum Transfer Distance': max((distance[d, r] for d, r, _ in flows), default=0.0),
    }
    for label, column in [('Evacuee Coverage','Evacuees'),
                          ('Functional Support Coverage','Estimated Functional Support Evacuees'),
                          ('Female Functional Support Coverage','Estimated Female Functional Support Evacuees')]:
        denominator = float(screen.loc[recipients.index, column].sum())
        metrics[label] = 100 * float(screen.loc[resolved, column].sum()) / denominator if denominator else None
    return flows, metrics


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = [INPUT / f'kumamoto_routable_road_{k}_preprocessed.parquet' for k in ['edges','nodes']]
    files += [ROOT / 'data/processed/shelter_equity_scenarios_preprocessed.parquet']
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in files}
    audit = json.loads((ROOT / 'data/exp/revision-road-audit/audit.json').read_text())
    for p in audit['provenance']:
        assert hashes[p['copy']] == p['sha256']
    assert hashes[str(files[2].relative_to(ROOT))] == audit['shelter_input_sha256']
    edges, nodes, frame = [pd.read_parquet(p) for p in files]
    base = frame.loc[frame.Municipality.eq('八代市') & frame.Scenario.eq('base')].copy()
    screen = construct_screen(base)
    assert len(screen) == 38 and int(screen['Screening Shortfall'].sum()) == 31
    tx = Transformer.from_crs('EPSG:6668', 'EPSG:6670', always_xy=True)
    lines = shapely.transform(shapely.from_wkb(edges.Geometry.to_numpy()), tx.transform, interleaved=False)
    stx = Transformer.from_crs('EPSG:4326', 'EPSG:6670', always_xy=True)
    xx, yy = stx.transform(screen.Longitude.to_numpy(), screen.Latitude.to_numpy())
    points = shapely.points(xx, yy)
    tree = shapely.STRtree(lines)
    node_index = {x:i for i,x in enumerate(nodes['Network Node ID'])}
    attach = []
    splits = defaultdict(dict)
    next_node = len(nodes)
    for i, point in enumerate(points):
        e = int(min(tree.query_nearest(point, all_matches=True), key=lambda k: edges.iloc[k]['Road Edge ID']))
        pos = float(shapely.line_locate_point(lines[e], point))
        length = float(shapely.length(lines[e]))
        if pos == 0:
            node = node_index[edges.iloc[e]['From Node ID']]
        elif pos == length:
            node = node_index[edges.iloc[e]['To Node ID']]
        else:
            if pos not in splits[e]:
                splits[e][pos] = next_node
                next_node += 1
            node = splits[e][pos]
        attach.append({'node': node, 'edge': e, 'position_m': pos,
                       'connector_m': float(shapely.distance(point, lines[e]))})
    graph = [[] for _ in range(next_node)]
    segments = []
    for e, (a,b) in enumerate(zip(edges['From Node ID'], edges['To Node ID'])):
        length = float(shapely.length(lines[e]))
        stops = [(0.0, node_index[a]), *sorted(splits[e].items()), (length, node_index[b])]
        for (lo,u),(hi,v) in zip(stops[:-1],stops[1:]):
            assert hi > lo
            seg = len(segments)
            segments.append((e,lo,hi,u,v))
            graph[u].append((v,hi-lo,seg))
            graph[v].append((u,hi-lo,seg))
    n = len(screen)
    network = np.full((n,n), math.inf)
    great = np.zeros((n,n))
    sources = sorted(set(a['node'] for a in attach))
    predecessors = {}
    for count, source in enumerate(sources,1):
        distances, prev = shortest(graph, source, sources)
        predecessors[source] = prev
        for i in range(n):
            if attach[i]['node'] == source:
                for j in range(n):
                    network[i,j] = distances.get(attach[j]['node'], math.inf)/1000
        print(f'Completed shortest paths {count}/{len(sources)}', flush=True)
    assert np.allclose(network, network.T) and np.allclose(network.diagonal(), 0)
    for i in range(n):
        for j in range(n):
            great[i,j] = haversine_km(screen.loc[i], screen.loc[j])
    pair_rows = []

    def pair(i,j):
        ai, aj = attach[i], attach[j]
        road = float(network[i,j])
        same = bool(screen.loc[i,'Longitude'] == screen.loc[j,'Longitude'] and screen.loc[i,'Latitude'] == screen.loc[j,'Latitude'])
        anchors = any(screen.loc[k,'Location Resolution'] == 'district anchor fallback' for k in [i,j])
        connectors = (ai['connector_m'] + aj['connector_m']) / 1000
        return {'donor_number':int(screen.loc[i,'Shelter Number']), 'recipient_number':int(screen.loc[j,'Shelter Number']),
                'great_circle_km':float(great[i,j]), 'network_km':road if math.isfinite(road) else None,
                'connector_sum_km':connectors,
                'network_plus_connectors_km':road+connectors if math.isfinite(road) else None,
                'network_to_great_circle_ratio':road/great[i,j] if great[i,j]>0 and math.isfinite(road) else None,
                'anchor_endpoint':anchors, 'both_exact_coordinates':not anchors,
                'shared_coordinates':same, 'reachable_nominally':math.isfinite(road)}

    for i in range(n):
        for j in range(n):
            if i != j:
                pair_rows.append(pair(i,j))
    summaries, flow_rows, changes, checks, used = [], [], [], [], set()
    for scenario in ['none','zero','full']:
        baseline_flows, baseline_metrics = allocate(screen, scenario, great)
        expected = evaluate_scenario(screen, scenario)
        for key,value in expected.items():
            assert baseline_metrics[key] == value if isinstance(value,str) else np.isclose(baseline_metrics[key],value)
        if scenario == 'full':
            old_flows, _ = full_mobility_flows(screen)
            assert baseline_flows == [(int(r['Donor Index']),int(r['Recipient Index']),int(r['Units'])) for _,r in old_flows.iterrows()]
        road_flows, road_metrics = allocate(screen, scenario, network)
        for metric,flows,metrics in [('great_circle',baseline_flows,baseline_metrics),('network',road_flows,road_metrics)]:
            quantities = sum(q for _,_,q in flows)
            def weighted(field):
                return sum(q*pair(d,r)[field] for d,r,q in flows)/quantities if quantities else None
            summaries.append({'distance_rule':metric, **metrics,
                              'mean_network_km_on_selected_links':weighted('network_km'),
                              'mean_connector_sum_km':weighted('connector_sum_km'),
                              'mean_network_plus_connectors_km':weighted('network_plus_connectors_km')})
            exact = [(d,r,q) for d,r,q in flows if pair(d,r)['both_exact_coordinates']]
            exact_units = sum(q for _,_,q in exact)
            summaries[-1].update({
                'both_exact_link_count':len(exact), 'both_exact_transferred_units':exact_units,
                'both_exact_mean_network_km':sum(q*network[d,r] for d,r,q in exact)/exact_units if exact_units else None,
                'shared_coordinate_link_count':sum(pair(d,r)['shared_coordinates'] for d,r,_ in flows),
                'shared_coordinate_transferred_units':sum(q for d,r,q in flows if pair(d,r)['shared_coordinates']),
                'distance_subset_caution':'Exact-coordinate links are descriptive subsets, not an equivalent-inventory experiment.'
            })
            for d,r,q in flows:
                flow_rows.append({'scenario':scenario,'distance_rule':metric,'units':q,**pair(d,r)})
                used.add((d,r))
        bm = {(d,r):q for d,r,q in baseline_flows}
        rm = {(d,r):q for d,r,q in road_flows}
        changed_recipients = sorted({r for d,r in bm.keys() | rm.keys() if bm.get((d,r),0)!=rm.get((d,r),0)})
        changes.append({'scenario':scenario,'changed_recipient_count':len(changed_recipients),
                        'changed_recipient_numbers':[int(screen.loc[r,'Shelter Number']) for r in changed_recipients],
                        'units_assigned_to_different_donor':sum(max(0,q-bm.get(k,0)) for k,q in rm.items()),
                        'baseline_links':len(bm),'network_links':len(rm)})
        checks.append({'scenario':scenario,'original_metric_reproduction':True,'integer_transfers':True,
                       'inventory_conservation':True,'donor_floor':True,'recipient_cap':True})
    reverse = Transformer.from_crs('EPSG:6670','EPSG:4326',always_xy=True)
    features = []
    for d,r in sorted(used):
        source,target = attach[d]['node'],attach[r]['node']
        path = []
        cursor = target
        while cursor != source:
            previous, sid = predecessors[source][cursor]
            path.append((sid, previous, cursor))
            cursor = previous
        path.reverse()
        road_length = sum(segments[sid][2]-segments[sid][1] for sid,_,_ in path)
        assert np.isclose(road_length, network[d,r]*1000, atol=1e-6)
        geometries = []
        for sid,u,v in path:
            e,lo,hi,forward,_ = segments[sid]
            geom = substring(lines[e],lo,hi)
            if u != forward:
                geom = shapely.reverse(geom)
            geom = shapely.transform(geom,reverse.transform,interleaved=False)
            geometries.append(list(map(list,geom.coords)))
        props = pair(d,r)
        props['segment_count'] = len(path)
        props['source_road_edge_ids'] = [str(edges.iloc[segments[sid][0]]['Road Edge ID']) for sid,_,_ in path]
        features.append({'type':'Feature','properties':props,
                         'geometry':{'type':'MultiLineString','coordinates':geometries} if geometries else None})
    report = {'decision_id':'KILA-D-20260920-010','input_sha256':hashes,
              'script_sha256':sha(Path(__file__)), 'scope':'Nominal undirected network, Yatsushiro Base demand, all three mobility scenarios',
              'ranking':'network length only; geometric off-network connectors reported separately',
              'limitations':['No observed road closures or travel times','No vehicle width/direction/access validation',
                             'District anchors and shared coordinates are not verified entrances or co-location'],
              'site_count':n,'unique_projected_nodes':len(sources),
              'unreachable_directed_pairs':sum(not p['reachable_nominally'] for p in pair_rows),
              'shared_coordinate_directed_pairs':sum(p['shared_coordinates'] for p in pair_rows),
              'scenario_summaries':summaries,'allocation_changes':changes,'validation':checks,
              'sites':[{'shelter_number':int(screen.loc[i,'Shelter Number']), 'location_resolution':str(screen.loc[i,'Location Resolution']),
                        'edge_id':str(edges.iloc[a['edge']]['Road Edge ID']), 'connector_m':a['connector_m'], 'projection_position_m':a['position_m']} for i,a in enumerate(attach)]}
    for filename,obj in [('summary.json',report),('pair_distances.json',pair_rows),('flows.json',flow_rows),
                         ('selected_nominal_routes.geojson',{'type':'FeatureCollection','features':features})]:
        (OUT/filename).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    assert hashes == {str(p.relative_to(ROOT)):sha(p) for p in files}
    print(json.dumps({'summaries':summaries,'allocation_changes':changes,'route_count':len(features)},indent=2))


if __name__ == '__main__':
    main()
