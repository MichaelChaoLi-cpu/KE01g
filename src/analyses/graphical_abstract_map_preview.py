"""Data-derived graphical-abstract preview; editable PPTX production remains pending."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator, FuncFormatter
from shapely.geometry import box
import figure_provisional_emergency_toilet_rebalancing_plan as maps

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/exp/revision-comment-4'
ROAD=ROOT/'data/exp/revision-road-comparison'

def main():
    frame=pd.read_parquet(ROOT/'data/processed/shelter_equity_scenarios_preprocessed.parquet')
    base=frame.loc[frame.Municipality.eq(maps.TARGET_MUNICIPALITY)&frame.Scenario.astype(str).eq('base')].reset_index(drop=True)
    screen=maps.construct_screen(base)
    flows,post=maps.full_mobility_flows(screen)
    assert len(screen)==38 and int(flows.Units.sum())==31
    selected=[f for f in json.loads((ROAD/'flows.json').read_text()) if f['scenario']=='full' and f['distance_rule']=='great_circle']
    quantities={(int(f['donor_number']),int(f['recipient_number'])):int(f['units']) for f in selected}
    assert len(quantities)==18 and sum(quantities.values())==31
    routes={ (f['properties']['donor_number'],f['properties']['recipient_number']):f for f in json.loads((ROAD/'selected_nominal_routes.geojson').read_text())['features']}
    vertices=np.concatenate([np.concatenate(routes[k]['geometry']['coordinates']) for k in quantities])
    x0,y0=vertices.min(axis=0);x1,y1=vertices.max(axis=0)
    # Analytical viewport includes all route geometries; this is a local transfer-area map.
    dx=x1-x0;dy=y1-y0
    extent=(x0-.22*dx,x1+.32*dx,y0-.22*dy,y1+.18*dy)
    window=box(extent[0],extent[2],extent[1],extent[3])
    boundaries=maps.load_boundaries()
    ink='#233D4B';teal='#237D81';orange='#B97428';blue='#416E88'
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.fonttype':'none'})
    fig=plt.figure(figsize=(16,6.4),facecolor='white')
    fig.text(.035,.937,'Equity-sensitive shelter sanitation planning',fontsize=23,weight='bold',color=ink)
    fig.text(.035,.889,'Yatsushiro, Japan · Full-mobility scenario',fontsize=12,color='#607783')
    ax=fig.add_axes([.042,.17,.50,.665],facecolor='#EDF5F8')
    for _,r in boundaries.iterrows():
        geom=r['Geometry Object'].intersection(window)
        if geom.is_empty or geom.geom_type not in ['Polygon','MultiPolygon']:continue
        target=r['Municipality Name']==maps.TARGET_MUNICIPALITY
        ax.add_collection(PolyCollection(maps.polygon_exteriors(geom),facecolors='#E2EDE8' if target else '#F5F5F0',edgecolors='#A8B9B6',linewidths=.65,zorder=1))
    for k,q in quantities.items():
        parts=[np.asarray(p) for p in routes[k]['geometry']['coordinates']]
        ax.add_collection(LineCollection(parts,colors=blue,linewidths=1.0+.35*np.sqrt(q),alpha=.85,zorder=3))
        donor=screen.loc[screen['Shelter Number'].eq(k[0])].iloc[0]
        rec=screen.loc[screen['Shelter Number'].eq(k[1])].iloc[0]
        connectors=[[[donor.Longitude,donor.Latitude],parts[0][0]], [parts[-1][-1],[rec.Longitude,rec.Latitude]]]
        ax.add_collection(LineCollection(connectors,colors=blue,linestyles='dotted',linewidths=.9,zorder=3))
    donors=post.loc[post['Transfer Out'].gt(0)];recipients=post.loc[post['Transfer In'].gt(0)]
    ax.scatter(donors.Longitude,donors.Latitude,s=45,marker='s',color=teal,edgecolor='white',linewidth=.8,zorder=5)
    ax.scatter(recipients.Longitude,recipients.Latitude,s=52+recipients['Transfer In']*5,marker='o',color=orange,edgecolor='white',linewidth=.9,zorder=6)
    arena=recipients.loc[recipients['Transfer In'].eq(12)].iloc[0]
    ax.annotate('Yatsushiro Arena  +12',xy=(arena.Longitude,arena.Latitude),xytext=(extent[0]+.03*(extent[1]-extent[0]),extent[2]+.13*(extent[3]-extent[2])),fontsize=10,weight='bold',color=ink,bbox={'boxstyle':'round,pad=.35','fc':'white','ec':'#B8C6CC'},arrowprops={'arrowstyle':'-','color':'#607783','lw':.8},zorder=8)
    ax.set_xlim(extent[:2]);ax.set_ylim(extent[2:]);ax.set_aspect(1/np.cos(np.deg2rad((y0+y1)/2)))
    ax.xaxis.set_major_locator(MaxNLocator(3));ax.yaxis.set_major_locator(MaxNLocator(3))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v,p:f'{v:.2f}°E'));ax.yaxis.set_major_formatter(FuncFormatter(lambda v,p:f'{v:.2f}°N'))
    ax.tick_params(labelsize=9,color='#9EAEB7',length=3)
    for spine in ax.spines.values():spine.set_color('#C2CFD4')
    ax.text(.035,.95,'31 units to 11 recipients',transform=ax.transAxes,va='top',fontsize=13,weight='bold',color=ink,bbox={'fc':'white','ec':'none','pad':5},zorder=9)
    ax.legend(handles=[Line2D([],[],marker='s',ls='',color=teal,label='Donor'),Line2D([],[],marker='o',ls='',color=orange,label='Recipient'),Line2D([],[],color=blue,lw=2,label='Nominal road path')],loc='upper center',bbox_to_anchor=(.5,-.10),ncol=3,frameon=False,fontsize=9,handlelength=1.5,columnspacing=1.3)
    fig.text(.585,.805,'Mobility determines the remaining shortfall',fontsize=15,weight='bold',color=ink)
    fig.text(.585,.76,'Temporary-toilet-only screening units',fontsize=11,color='#607783')
    for y,value,label,width,color in [(.65,31,'No movement',.30,blue),(.49,26,'Empty-site donors only',.30*26/31,teal),(.33,0,'Full reported-surplus mobility',0,orange)]:
        fig.text(.585,y,str(value),fontsize=36,weight='bold',color=color,va='center')
        fig.text(.64,y+.014,label,fontsize=12,color=ink,va='center')
        bar=fig.add_axes([.64,y-.042,.305,.014]);bar.set_xlim(0,.305);bar.set_ylim(0,1);bar.axis('off')
        bar.axhspan(0,1,color='#EEF2F4');bar.fill_between([0,width],0,1,color=color)
    fig.text(.585,.195,'Zero is conditional on full surplus mobility.',fontsize=11,color=orange,weight='bold')
    fig.text(.585,.155,'Usability and access remain unverified.',fontsize=11,color='#607783')
    fig.text(.035,.035,'Planning priorities include female and functional-support needs',fontsize=14,weight='bold',color=teal)
    OUT.mkdir(parents=True,exist_ok=True)
    fig.savefig(OUT/'Graphical_abstract_map_review.png',dpi=166,facecolor='white')
    fig.savefig(OUT/'Graphical_abstract_map_review.svg',facecolor='white')
    plt.close(fig)

if __name__=='__main__':main()
