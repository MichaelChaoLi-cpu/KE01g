"""Reuse revised Figure 4 b/c rendering functions in a horizontal review layout."""
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import figure_provisional_emergency_toilet_rebalancing_plan as maps
import figure_toilet_rebalancing_performance_under_resource_mobility_scenarios as performance
from preview_revision_road_assets import route_panel

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/exp/revision-comment-4'

def main():
    frame=pd.read_parquet(ROOT/'data/processed/shelter_equity_scenarios_preprocessed.parquet')
    base=frame.loc[frame.Municipality.eq(maps.TARGET_MUNICIPALITY)&frame.Scenario.astype(str).eq('base')].reset_index(drop=True)
    screen=maps.construct_screen(base)
    flows,post=maps.full_mobility_flows(screen)
    outcomes=pd.DataFrame([performance.evaluate_scenario(screen,s) for s in performance.SCENARIOS])
    performance.validate(base,screen,outcomes)
    assert outcomes['Residual Screening Shortfall'].tolist()==[31,26,0]
    boundaries=maps.load_boundaries();geometry,extent=maps.map_geometry(boundaries)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8.5,'axes.edgecolor':'#4B5563','axes.linewidth':.8,'figure.facecolor':'white','axes.facecolor':'white','xtick.color':'#3F4854','ytick.color':'#3F4854','svg.fonttype':'none'})
    fig=plt.figure(figsize=(14,10))
    ink='#263746'; teal='#237D81'
    overlay=fig.add_axes([0,0,1,1],frameon=False);overlay.set_axis_off()
    title_box={'boxstyle':'round,pad=0.38,rounding_size=0.22',
               'facecolor':'#F0F4F6','edgecolor':'#9AADB8','linewidth':1.0}
    fig.text(.06,.951,'Data and analysis',fontsize=20,weight='bold',color=ink,bbox=title_box)
    fig.text(.97,.954,'11 municipalities · 53 matched shelters',fontsize=11,color=ink,ha='right')
    for x,title,detail in [
        (.06,'Emergency records','Shelter occupancy and reported toilet deployments'),
        (.37,'Population mesh','Residential age–sex composition'),
        (.69,'Administrative statistics','Disability and long-term care')]:
        fig.text(x,.897,title,fontsize=12,weight='bold',color=ink)
        fig.text(x,.870,detail,fontsize=10,color=ink)
    for x,title,detail in [
        (.06,'1  Estimate equity-sensitive demand','Female and functional-support composition scenarios'),
        (.37,'2  Screen needs and priorities','Toilet pressure and verification ranking'),
        (.69,'3  Test conditional reallocation','Donor mobility scenarios and service packages')]:
        fig.text(x,.815,title,fontsize=12,weight='bold',color='black')
        fig.text(x,.787,detail,fontsize=10,color=ink)
    for x1,x2 in [(.333,.36),(.649,.68)]:
        overlay.annotate('',xy=(x2,.818),xytext=(x1,.818),xycoords='axes fraction',
                         arrowprops={'arrowstyle':'->','color':teal,'lw':1.25})
    fig.text(.06,.704,'Conditional reallocation',fontsize=17,weight='bold',color=ink,bbox=title_box)
    fig.text(.555,.704,'Mobility-scenario outcomes',fontsize=17,weight='bold',color=ink,bbox=title_box)
    axmap=fig.add_axes([.06,.07,.415,.581])
    axbar=fig.add_axes([.555,.07,.415,.581])
    route_panel(axmap,screen,flows,post,boundaries,geometry,extent)
    original=performance.add_panel_heading
    performance.add_panel_heading=lambda ax,label,title: None
    try:performance.draw_operational_panel(axbar,outcomes)
    finally:performance.add_panel_heading=original
    handles,labels=axbar.get_legend_handles_labels()
    axbar.legend(handles,labels,loc='upper left',bbox_to_anchor=(0,1.0),ncol=3,
                 frameon=False,fontsize=7.4,handlelength=1.25,columnspacing=.9,labelspacing=.45)
    for label in axbar.get_xticklabels():label.set_fontsize(8)
    OUT.mkdir(parents=True,exist_ok=True)
    fig.savefig(OUT/'Graphical_abstract_data_process_results_review.png',dpi=200,facecolor='white')
    fig.savefig(OUT/'Graphical_abstract_data_process_results_review.svg',facecolor='white')
    plt.close(fig)

if __name__=='__main__':main()
