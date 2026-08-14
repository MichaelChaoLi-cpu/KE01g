#!/usr/bin/env python3
"""Provisional Toilet Rebalancing and Mobility-Scenario Performance.

Plan: Combine the current Yatsushiro imbalance map, conditional full-mobility
movements, operational scenario outcomes, and resolved-site demand coverage.
Framework: Section 5 conditional mitigation contrast; Section 6 donor capacity,
integer transfer, residual shortfall, and coverage equations; Section 7
resource-mobility robustness workflow. Every movement is a planning sensitivity,
not a verified dispatch instruction or functional-capacity result.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import figure_provisional_emergency_toilet_rebalancing_plan as map_figure
import figure_toilet_rebalancing_performance_under_resource_mobility_scenarios as performance_figure


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/processed/shelter_equity_scenarios_preprocessed.parquet"
OUTPUT = (
    ROOT
    / "data/results/figures/"
    "Figure_provisional_toilet_rebalancing_and_mobility_scenario_performance.png"
)


def add_performance_heading(ax: plt.Axes, label: str, heading: str) -> None:
    translated_label = {"a": "c", "b": "d"}[label]
    ax.text(
        -0.085,
        1.045,
        translated_label,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=12,
        fontweight="bold",
        color="#263746",
    )
    ax.text(
        -0.015,
        1.045,
        heading,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9.3,
        fontweight="bold",
        color="#263746",
    )


def main() -> None:
    frame = pd.read_parquet(SOURCE)
    required = {
        "Municipality",
        "Shelter Number",
        "Shelter Name",
        "Latitude",
        "Longitude",
        "Location Resolution",
        "Evacuees",
        "Water Status",
        "Temporary Toilets Installed",
        "Toilet Cars",
        "Scenario",
        "Estimated Functional Support Evacuees",
        "Estimated Female Functional Support Evacuees",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")
    base = frame.loc[
        frame["Municipality"].eq(map_figure.TARGET_MUNICIPALITY)
        & frame["Scenario"].astype("string").eq("base")
    ].copy().reset_index(drop=True)
    if len(base) != 38:
        raise ValueError("Expected 38 Yatsushiro shelters in the base scenario")
    if base[list(required.difference({"Municipality", "Scenario"}))].isna().any().any():
        raise ValueError("Required Yatsushiro mitigation fields must be complete")

    screen = map_figure.construct_screen(base)
    flows, post = map_figure.full_mobility_flows(screen)
    if int(screen["Screening Shortfall"].sum()) != 31:
        raise ValueError("Expected a 31-unit current screening shortfall")
    if int(screen["Reported Surplus"].sum()) != 72:
        raise ValueError("Expected 72 reported units above sitewise requirements")
    if int(screen["Screening Shortfall"].gt(0).sum()) != 11:
        raise ValueError("Expected 11 current shortfall shelters")
    if int(flows["Units"].sum()) != 31 or int(post["Residual Shortfall"].sum()) != 0:
        raise ValueError("Full mobility must move 31 units and resolve the screen")
    if int(post["Transfer In"].sum()) != int(post["Transfer Out"].sum()):
        raise ValueError("Transfer inflow and outflow must be conserved")
    donor_rows = post.loc[post["Transfer Out"].gt(0)]
    if (donor_rows["Post-Transfer Inventory"] < donor_rows["Prolonged Requirement"]).any():
        raise ValueError("A donor falls below its protected prolonged requirement")

    performance = pd.DataFrame(
        [
            performance_figure.evaluate_scenario(screen, scenario)
            for scenario in performance_figure.SCENARIOS
        ]
    )
    performance["Scenario"] = pd.Categorical(
        performance["Scenario"],
        categories=performance_figure.SCENARIOS,
        ordered=True,
    )
    performance = performance.sort_values("Scenario").reset_index(drop=True)
    performance_figure.validate(base, screen, performance)

    boundaries = map_figure.load_boundaries()
    target_geometry, extent = map_figure.map_geometry(boundaries)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.edgecolor": "#4B5563",
            "axes.linewidth": 0.8,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "xtick.color": "#3F4854",
            "ytick.color": "#3F4854",
        }
    )
    fig = plt.figure(figsize=(14.2, 11.5))
    grid = fig.add_gridspec(
        2,
        2,
        width_ratios=(1, 1),
        height_ratios=(1.12, 0.78),
        hspace=0.21,
        wspace=0.19,
    )
    current_ax = fig.add_subplot(grid[0, 0])
    transfer_ax = fig.add_subplot(grid[0, 1])
    operational_ax = fig.add_subplot(grid[1, 0])
    coverage_ax = fig.add_subplot(grid[1, 1])

    map_figure.draw_current_panel(
        current_ax, screen, boundaries, target_geometry, extent
    )
    map_figure.draw_transfer_panel(
        transfer_ax, screen, flows, post, boundaries, target_geometry, extent
    )
    map_figure.add_panel_heading(
        current_ax,
        "a",
        "Current screen · 31 shortfall units, 72 reported surplus units",
    )
    map_figure.add_panel_heading(
        transfer_ax,
        "b",
        "Full-mobility sensitivity · 31 moved, residual screen = 0",
    )

    performance_figure.add_panel_heading = add_performance_heading
    performance_figure.draw_operational_panel(operational_ax, performance)
    performance_figure.draw_coverage_panel(coverage_ax, performance)
    fig.subplots_adjust(left=0.07, right=0.985, bottom=0.08, top=0.965)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
