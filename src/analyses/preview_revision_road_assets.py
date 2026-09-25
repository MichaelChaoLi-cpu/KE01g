"""Render approved Figure 4 / Table 9 designs without changing final assets."""
from pathlib import Path
import argparse
import hashlib
import json
import textwrap

from docx import Document
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

import figure_provisional_emergency_toilet_rebalancing_plan as maps
import figure_provisional_toilet_rebalancing_and_mobility_scenario_performance as combined

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/exp/revision-road-comparison/previews'
RESULT = OUT.parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def route_panel(ax, screen, flows, post, boundaries, target_geometry, extent):
    routes = json.loads((RESULT/'selected_nominal_routes.geojson').read_text())['features']
    index = {(r['properties']['donor_number'],r['properties']['recipient_number']):r for r in routes}
    nominal = [r for r in json.loads((RESULT/'flows.json').read_text())
               if r['scenario']=='full' and r['distance_rule']=='great_circle']
    expected = {(r['donor_number'],r['recipient_number']):r['units'] for r in nominal}
    seen = {}
    maps.draw_base_map(ax,boundaries,target_geometry,extent)
    ax.scatter(screen.Longitude,screen.Latitude,s=13,color='#C7CDD1',edgecolor='white',linewidth=.35,zorder=4)
    for _,flow in flows.iterrows():
        donor = screen.loc[int(flow['Donor Index'])]
        recipient = screen.loc[int(flow['Recipient Index'])]
        key = (int(donor['Shelter Number']),int(recipient['Shelter Number']))
        q = int(flow['Units'])
        assert expected[key] == q
        seen[key] = q
        route = index[key]
        assert route['geometry'] is not None
        parts = [np.asarray(p) for p in route['geometry']['coordinates']]
        ax.add_collection(LineCollection(parts,colors=maps.TRANSFER_COLOR,
                                         linewidths=.65+.32*q,alpha=.72,zorder=5))
        connectors = [np.array([[donor.Longitude,donor.Latitude],parts[0][0]]),
                      np.array([parts[-1][-1],[recipient.Longitude,recipient.Latitude]])]
        ax.add_collection(LineCollection(connectors,colors='#6B6279',linestyles='dashed',linewidths=1.1,zorder=7))
        steps = [(a,b) for part in parts for a,b in zip(part[:-1],part[1:])]
        lengths = np.array([np.linalg.norm(b-a) for a,b in steps])
        target = lengths.sum()*.55
        j = min(int(np.searchsorted(np.cumsum(lengths),target)),len(steps)-1)
        a,b = steps[j]
        direction = b-a
        norm = np.linalg.norm(direction)
        mid = (a+b)/2
        if norm:
            ax.annotate('',xy=b,xytext=a,
                        arrowprops={'arrowstyle':'-|>','color':maps.TRANSFER_COLOR,'lw':1.1,'mutation_scale':7},zorder=6)
        ax.text(mid[0],mid[1],str(q),ha='center',va='center',fontsize=5.8,fontweight='bold',
                color='#36596D',bbox={'boxstyle':'circle,pad=.12','fc':'white','ec':maps.TRANSFER_COLOR,'lw':.45},zorder=7)
    assert seen == expected and len(seen)==18 and sum(seen.values())==31
    donors = post.loc[post['Transfer Out'].gt(0)]
    recipients = post.loc[post['Transfer In'].gt(0)]
    ax.scatter(donors.Longitude,donors.Latitude,s=30+7*donors['Transfer Out'],marker='s',
               color=maps.SURPLUS_COLOR,edgecolor='white',linewidth=.6,zorder=8)
    ax.scatter(recipients.Longitude,recipients.Latitude,s=34+8*recipients['Transfer In'],marker='o',
               color=maps.RESOLVED_COLOR,edgecolor='white',linewidth=.7,zorder=8)
    active = pd.concat([donors,recipients]).drop_duplicates().copy()
    anchor = active.loc[active['Location Resolution'].eq('district anchor fallback')]
    ax.scatter(anchor.Longitude,anchor.Latitude,s=100,marker='D',facecolors='none',edgecolors='#745B87',linewidth=.8,zorder=9)
    active['Map Label'] = np.where(active['Transfer In'].gt(0),
        active['Shelter Number'].map(lambda x:f'Y{int(x):02d}')+'  +'+active['Transfer In'].astype(str),
        active['Shelter Number'].map(lambda x:f'Y{int(x):02d}')+'  −'+active['Transfer Out'].astype(str))
    active['Label Direction'] = np.where(active['Transfer In'].gt(0),'increase','decrease')
    maps.label_column_points(ax,active,extent,'Map Label')
    legend=ax.legend(handles=[
        Line2D([],[],marker='s',color='none',markerfacecolor=maps.SURPLUS_COLOR,label='Donor (−)'),
        Line2D([],[],marker='o',color='none',markerfacecolor=maps.RESOLVED_COLOR,label='Recipient (+)'),
        Line2D([],[],color=maps.TRANSFER_COLOR,lw=2,label='Nominal road path; label = units'),
        Line2D([],[],color='#6B6279',ls='--',label='Unverified connector'),
        Line2D([],[],marker='D',color='none',markerfacecolor='none',markeredgecolor='#745B87',label='District-anchor endpoint')],
        loc='lower center',ncol=2,frameon=True,facecolor='white',edgecolor='#D0D3D6',
        framealpha=.96,fontsize=6.4,handletextpad=.4,columnspacing=.8)
    legend.set_zorder(12)


def table_preview():
    doc = Document(ROOT/'Rev/revision/KE01g.rev.clean.docx')
    rows = [[c.text for c in row.cells] for row in doc.tables[8].rows]
    assert len(rows)==9 and len(rows[0])==4 and rows[7][0].startswith('Transfer Distance')
    summary=json.loads((RESULT/'summary.json').read_text())
    metrics={(r['Scenario'],r['distance_rule']):r for r in summary['scenario_summaries']}
    flows=json.loads((RESULT/'flows.json').read_text())
    row_baseline=['Baseline great-circle distance\n(mean / maximum km)']
    row_road=['Network distance on baseline links\n(mean / maximum km)']
    row_new=['Network-selected distance\n(mean / maximum km)']
    for scenario in ['none','zero','full']:
        b=metrics[scenario,'great_circle']; n=metrics[scenario,'network']
        if scenario=='none':
            row_baseline.append('—');row_road.append('—');row_new.append('—')
        else:
            subset=[f for f in flows if f['scenario']==scenario and f['distance_rule']=='great_circle']
            row_baseline.append(f"{b['Mean Transfer Distance']:.2f} / {b['Maximum Transfer Distance']:.2f}")
            row_road.append(f"{b['mean_network_km_on_selected_links']:.2f} / {max(f['network_km'] for f in subset):.2f}")
            row_new.append(f"{n['Mean Transfer Distance']:.2f} / {n['Maximum Transfer Distance']:.2f}")
    change=['Donor reassignment\n(units / recipient sites)']+[f"{r['units_assigned_to_different_donor']} / {r['changed_recipient_count']}" for r in summary['allocation_changes']]
    revised=rows[:7]+[row_baseline,row_road,row_new,change]+rows[8:]
    # Proposed correction to an existing unit-label error; final Word change
    # remains subject to the explicit supplemental approval in the bundle.
    revised[3][0]='Recipient Outcomes\n(Receiving Shelters / Still Short)'
    assert len(revised)==12 and all(len(r)==4 for r in revised)
    assert revised[8][1:]==['—','7.34 / 11.35','2.99 / 5.18']
    assert revised[9][1:]==['—','7.34 / 11.35','2.66 / 4.72']
    note=(ROOT/'Rev/docs/revision-design-reviewer-1-comment-1.md').read_text().split('Proposed exact added table note: "',1)[1].split('"',1)[0]
    (OUT/'Table_9_preview.json').write_text(json.dumps({'rows':revised,'note':note},ensure_ascii=False,indent=2)+'\n')
    wrapped=[[ '\n'.join(textwrap.fill(part,width=38 if c==0 else 33,break_long_words=False,break_on_hyphens=False) for part in cell.split('\n')) for c,cell in enumerate(row)] for row in revised]
    line_counts=[max(c.count('\n')+1 for c in row) for row in wrapped]
    heights=np.array([.22*k+.24 for k in line_counts]); heights[0]+=.12
    fig,ax=plt.subplots(figsize=(15,heights.sum()+.25))
    ax.axis('off')
    table=ax.table(cellText=wrapped,cellLoc='center',colWidths=[.31,.20,.245,.245],bbox=[0,0,1,1])
    table.auto_set_font_size(False);table.set_fontsize(10.5)
    for (r,c),cell in table.get_celld().items():
        cell.set_height(heights[r]/heights.sum());cell.set_edgecolor('#B9C1C8');cell.set_linewidth(.55)
        cell.PAD=.07
        cell.set_facecolor('#DCE5EC' if r==0 else ('#EDF3F7' if r in [8,9,10] else ('#F7F8F9' if r%2==0 else 'white')))
        if r==0:cell.set_text_props(weight='bold',color='#263746')
        elif c==0:cell.set_text_props(ha='left',weight='normal')
    fig.subplots_adjust(left=.015,right=.985,top=.98,bottom=.02)
    fig.savefig(OUT/'Table_9_preview.png',dpi=180,facecolor='white',bbox_inches='tight')
    plt.close(fig)
    (OUT/'Table_9_note.md').write_text(note+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--figure-only', action='store_true')
    args = parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    final = ROOT/'data/results/figures/Figure_provisional_toilet_rebalancing_and_mobility_scenario_performance.png'
    before=digest(final)
    original_draw,original_output=maps.draw_transfer_panel,combined.OUTPUT
    original_map_heading = maps.add_panel_heading
    original_performance_heading = combined.add_performance_heading
    titles = {'a': 'Current toilet imbalance', 'b': 'Nominal road routes',
              'c': 'Rebalancing outcomes', 'd': 'Resolved-site demand coverage'}
    try:
        maps.draw_transfer_panel=route_panel
        maps.add_panel_heading = lambda ax, label, heading: original_map_heading(ax, label, titles[label])
        combined.add_performance_heading = lambda ax, label, heading: original_performance_heading(
            ax, label, titles[{'a': 'c', 'b': 'd'}[label]])
        combined.OUTPUT=OUT/'Figure_4_preview.png'
        combined.main()
    finally:
        maps.draw_transfer_panel=original_draw;combined.OUTPUT=original_output
        maps.add_panel_heading = original_map_heading
        combined.add_performance_heading = original_performance_heading
    assert digest(final)==before
    if not args.figure_only:
        table_preview()
    manifest={'decision_id':'KILA-D-20260920-011','final_figure_unchanged_sha256':before,
              'script_sha256':digest(Path(__file__)),
              'outputs':{p.name:digest(p) for p in OUT.iterdir() if p.suffix in ['.png','.json','.md'] and p.name!='manifest.json'},
              'figure_validation':{'baseline_links':18,'transferred_units':31,
                                   'panel_titles':titles, 'other_panels':'existing unchanged data rendering functions'},
              'table_validation':{'rows_including_header':12,'columns':4,'existing_numeric_rows_preserved':True,
                                  'proposed_label_correction':'Received Units -> Receiving Shelters; human approval pending'}}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Figure 4 preview saved; Table 9 unchanged.' if args.figure_only else
          'Figure 4 and Table 9 previews saved; final assets untouched.')


if __name__=='__main__':
    main()
