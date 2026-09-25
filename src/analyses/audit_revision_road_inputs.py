"""Copy and audit ROAD inputs only; no routing, allocation or manuscript edits."""
from pathlib import Path
import hashlib
import json
import shutil
from collections import Counter

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from pyproj import CRS, Transformer
import shapely

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'data/processed/revision_road_inputs'
OUT = ROOT / 'data/exp/revision-road-audit'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    provenance = []
    frames = []
    for kind in ['edges', 'nodes']:
        name = f'kumamoto_routable_road_{kind}_preprocessed.parquet'
        source = ROOT.parent / 'KE01d/data/processed' / name
        target = DEST / name
        before = digest(source)
        if target.exists() and digest(target) != before:
            raise RuntimeError(f'Refusing to overwrite divergent input: {target}')
        if not target.exists():
            shutil.copy2(source, target)
        assert digest(source) == digest(target) == before
        provenance.append(dict(source=str(source), copy=str(target.relative_to(ROOT)), sha256=before))
        df = pd.read_parquet(target)
        meta = json.loads(pq.read_schema(target).metadata[b'geo'])
        crs = CRS.from_json_dict(meta['columns']['Geometry']['crs'])
        transformer = Transformer.from_crs(crs, 'EPSG:6670', always_xy=True)
        geom = shapely.from_wkb(df['Geometry'].to_numpy())
        projected = shapely.transform(geom, transformer.transform, interleaved=False)
        frames.append((df, projected, crs.to_string()))
    edges, lines, edge_crs = frames[0]
    nodes, points, node_crs = frames[1]
    assert edges['Road Edge ID'].is_unique and nodes['Network Node ID'].is_unique
    assert shapely.is_valid(lines).all() and not shapely.is_empty(lines).any()
    assert shapely.is_valid(points).all() and not shapely.is_empty(points).any()
    assert (edges['Road Length (m)'] > 0).all()
    idx = dict(zip(nodes['Network Node ID'], range(len(nodes))))
    u = np.array([idx[x] for x in edges['From Node ID']])
    v = np.array([idx[x] for x in edges['To Node ID']])
    parent = np.arange(len(nodes))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b in zip(u, v):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    roots = np.array([find(i) for i in range(len(nodes))])
    counts = Counter(roots.tolist())
    degree = np.bincount(np.r_[u, v], minlength=len(nodes))
    stored = pd.DataFrame({'root': roots, 'stored': nodes['Network Component ID']})
    endpoint_errors = np.maximum(
        shapely.distance(shapely.get_point(lines, 0), points[u]),
        shapely.distance(shapely.get_point(lines, -1), points[v]))
    source_sites = ROOT / 'data/processed/shelter_equity_scenarios_preprocessed.parquet'
    shelters = pd.read_parquet(source_sites)
    shelters = shelters.loc[shelters.Scenario.eq('base')].copy()
    assert len(shelters) == 53
    assert shelters[['Municipality', 'Shelter Number']].duplicated().sum() == 0
    assert shelters[['Longitude', 'Latitude']].notna().all().all()
    # Existing shelter pipeline uses longitude/latitude; treat as EPSG:4326
    # for this metre-scale proximity diagnostic, not survey-grade positioning.
    tx = Transformer.from_crs('EPSG:4326', 'EPSG:6670', always_xy=True)
    x, y = tx.transform(shelters.Longitude.to_numpy(), shelters.Latitude.to_numpy())
    site_points = shapely.points(x, y)
    edge_tree, node_tree = shapely.STRtree(lines), shapely.STRtree(points)
    records = []
    for (_, row), point in zip(shelters.iterrows(), site_points):
        candidates = edge_tree.query_nearest(point, all_matches=True)
        e = min(candidates, key=lambda k: edges.iloc[k]['Road Edge ID'])
        n = int(node_tree.nearest(point))
        edge = edges.iloc[e]
        records.append({
            'municipality': str(row.Municipality), 'shelter_number': int(row['Shelter Number']),
            'shelter_name': str(row['Shelter Name']), 'location_resolution': str(row['Location Resolution']),
            'longitude': float(row.Longitude), 'latitude': float(row.Latitude),
            'nearest_edge_id': edge['Road Edge ID'],
            'edge_distance_m': float(shapely.distance(point, lines[e])),
            'nearest_node_distance_m': float(shapely.distance(point, points[n])),
            'component_node_count': counts[int(roots[u[e]])],
            'component_root': int(roots[u[e]]), 'road_state': str(edge['Road State']),
            'width_category': str(edge['Width Category']), 'road_category': str(edge['Road Category']),
            'vertical_level': int(edge['Vertical Level']),
            'eligible_flag': bool(edge['Network Analysis Eligible']),
            'available_flag': bool(edge['Road Available']),
        })
    audit = {
        'scope': 'Input and proximity audit only; no shortest paths or allocation.',
        'provenance': provenance,
        'shelter_input_sha256': digest(source_sites),
        'edge_crs': edge_crs, 'node_crs': node_crs, 'metric_crs': 'EPSG:6670',
        'shelter_crs_assumption': 'EPSG:4326; geographic lon/lat from existing pipeline',
        'edge_count': len(edges), 'node_count': len(nodes),
        'component_count': len(counts), 'largest_components_nodes': counts.most_common(10),
        'isolated_nodes': int((degree == 0).sum()), 'self_loop_edges': int((u == v).sum()),
        'stored_components_consistent': bool(stored.groupby('root').stored.nunique().max() == 1 and stored.groupby('stored').root.nunique().max() == 1),
        'max_endpoint_geometry_error_m': float(endpoint_errors.max()),
        'length_error_m_quantiles': np.quantile(np.abs(shapely.length(lines) - edges['Road Length (m)']), [0, .5, .95, 1]).tolist(),
        'edge_attribute_counts': {c: {str(k): int(v) for k, v in edges[c].value_counts(dropna=False).items()} for c in ['Road State','Road Category','Width Category','Vertical Level','Road Available','Network Analysis Eligible']},
        'sites': records,
        'interpretation': 'Nearest geometric edge is not verified vehicle access. District anchors are not shelter entrances. Availability flags are construction defaults, not observed post-disaster status.'
    }
    (OUT / 'audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:v for k,v in audit.items() if k not in ['sites','edge_attribute_counts']}, ensure_ascii=False, indent=2))
    for city in shelters.Municipality.unique():
        group = [r for r in records if r['municipality'] == city]
        print(city, 'edge distance quantiles', np.quantile([r['edge_distance_m'] for r in group], [0,.5,.95,1]))
        print('largest offsets', sorted(group, key=lambda r:r['edge_distance_m'], reverse=True)[:5])


if __name__ == '__main__':
    main()
