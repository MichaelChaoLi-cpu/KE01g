#!/usr/bin/env python3
"""Toilet Rebalancing Performance under Resource-Mobility Scenarios.

Plan: Compare transferred units, unresolved temporary-toilet-only screening
pressure, and resolved-site demand coverage across three predeclared mobility
scenarios.
Framework: Section 5 conditional mitigation sensitivity; Section 6 donor
capacity D, integer transfers x, residual shortfall U, and resolved-site demand
coverage C; Section 7 robustness workflow. Full reported-surplus mobility is a
best-case planning bound, not a verified dispatch result.
"""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator, PercentFormatter
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/processed/shelter_equity_scenarios_preprocessed.parquet"
OUTPUT = (
    ROOT
    / "data/results/figures/"
    "Figure_toilet_rebalancing_performance_under_resource_mobility_scenarios.png"
)

TARGET_MUNICIPALITY = "八代市"
SCENARIOS = ("none", "zero", "full")
SCENARIO_LABELS = (
    "No rebalancing",
    "Zero-occupancy\ndonor only",
    "Full reported-surplus\nmobility (upper bound)",
)
OUTCOME_COLORS = {
    "Transferred units": "#3B73A1",
    "Residual screening shortfall": "#C65345",
    "Shelters with residual shortfall": "#D3A24D",
}
COVERAGE_COLORS = {
    "Observed evacuees": "#607D91",
    "Estimated functional support": "#7A6A9E",
    "Estimated female functional support": "#A45D7B",
}


def add_panel_heading(ax: plt.Axes, label: str, heading: str) -> None:
    ax.text(
        -0.085,
        1.045,
        label,
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
        fontsize=9.5,
        fontweight="bold",
        color="#263746",
    )


def haversine_km(row_a: pd.Series, row_b: pd.Series) -> float:
    lat1, lon1, lat2, lon2 = map(
        radians,
        [row_a["Latitude"], row_a["Longitude"], row_b["Latitude"], row_b["Longitude"]],
    )
    value = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * asin(sqrt(value))


def construct_screen(frame: pd.DataFrame) -> pd.DataFrame:
    screen = frame.copy().reset_index(drop=True)
    screen["Prolonged Requirement"] = np.ceil(screen["Evacuees"] / 20).astype(int)
    screen["Screening Shortfall"] = (
        screen["Prolonged Requirement"] - screen["Temporary Toilets Installed"]
    ).clip(lower=0).astype(int)
    screen["Reported Surplus"] = (
        screen["Temporary Toilets Installed"] - screen["Prolonged Requirement"]
    ).clip(lower=0).astype(int)
    screen["Water Severity"] = screen["Water Status"].astype(str).map(
        {"〇": 0, "○": 0, "△": 1, "×": 2}
    )
    if screen["Water Severity"].isna().any():
        raise ValueError("Unrecognized water-status value")
    screen["No Reported Deployable Unit"] = (
        screen["Temporary Toilets Installed"].eq(0) & screen["Toilet Cars"].eq(0)
    ).astype(int)
    screen["Verification Tier"] = np.select(
        [
            screen["Evacuees"].gt(0)
            & screen["Water Severity"].eq(2)
            & screen["No Reported Deployable Unit"].eq(1),
            screen["Evacuees"].gt(0)
            & screen["Water Severity"].eq(2)
            & screen["Screening Shortfall"].gt(0),
            screen["Evacuees"].gt(0)
            & screen["Water Severity"].eq(1)
            & screen["Screening Shortfall"].gt(0),
            screen["Evacuees"].gt(0)
            & (
                screen["No Reported Deployable Unit"].eq(1)
                | screen["Screening Shortfall"].gt(0)
            ),
            screen["Evacuees"].gt(0),
        ],
        [1, 2, 3, 4, 5],
        default=6,
    ).astype(int)
    return screen


def donor_capacity(screen: pd.DataFrame, scenario: str) -> dict[int, int]:
    capacities: dict[int, int] = {}
    for index, row in screen.iterrows():
        if scenario == "none":
            capacity = 0
        elif scenario == "zero":
            capacity = int(row["Temporary Toilets Installed"]) if row["Evacuees"] == 0 else 0
        elif scenario == "full":
            capacity = int(row["Reported Surplus"])
        else:
            raise ValueError(f"Unknown resource-mobility scenario: {scenario}")
        capacities[int(index)] = capacity
    return capacities


def evaluate_scenario(screen: pd.DataFrame, scenario: str) -> dict[str, float | int | str]:
    capacities = donor_capacity(screen, scenario)
    initial_eligible_units = int(sum(capacities.values()))
    residual = screen["Screening Shortfall"].astype(int).to_dict()
    recipients = screen.loc[screen["Screening Shortfall"].gt(0)].sort_values(
        [
            "Verification Tier",
            "Screening Shortfall",
            "Estimated Functional Support Evacuees",
            "Estimated Female Functional Support Evacuees",
            "Evacuees",
            "Shelter Number",
        ],
        ascending=[True, False, False, False, False, True],
        kind="stable",
    )
    flows: list[tuple[int, int, int, float]] = []
    for recipient_index, recipient in recipients.iterrows():
        while residual[recipient_index] > 0:
            eligible = [
                donor_index
                for donor_index, capacity in capacities.items()
                if capacity > 0 and donor_index != recipient_index
            ]
            if not eligible:
                break
            donor_index = min(
                eligible,
                key=lambda index: (
                    haversine_km(screen.loc[index], recipient),
                    int(screen.loc[index, "Shelter Number"]),
                ),
            )
            quantity = min(capacities[donor_index], residual[recipient_index])
            distance = haversine_km(screen.loc[donor_index], recipient)
            capacities[donor_index] -= quantity
            residual[recipient_index] -= quantity
            flows.append((donor_index, int(recipient_index), int(quantity), float(distance)))

    transferred = int(sum(quantity for _, _, quantity, _ in flows))
    residual_shortfall = int(sum(residual.values()))
    unresolved_shelters = int(sum(value > 0 for value in residual.values()))
    resolved_indices = [
        int(index) for index in recipients.index if residual[int(index)] == 0
    ]
    initial_recipient_indices = list(map(int, recipients.index))

    def resolved_coverage(column: str) -> float:
        denominator = float(screen.loc[initial_recipient_indices, column].sum())
        numerator = float(screen.loc[resolved_indices, column].sum())
        return 100.0 * numerator / denominator if denominator > 0 else np.nan

    mean_distance = (
        sum(quantity * distance for _, _, quantity, distance in flows) / transferred
        if transferred > 0
        else 0.0
    )
    max_distance = max((distance for _, _, _, distance in flows), default=0.0)
    return {
        "Scenario": scenario,
        "Eligible Donor Units": initial_eligible_units,
        "Transferred Units": transferred,
        "Residual Screening Shortfall": residual_shortfall,
        "Shelters with Residual Shortfall": unresolved_shelters,
        "Resolved Shelter Count": len(resolved_indices),
        "Evacuee Coverage": resolved_coverage("Evacuees"),
        "Functional Support Coverage": resolved_coverage(
            "Estimated Functional Support Evacuees"
        ),
        "Female Functional Support Coverage": resolved_coverage(
            "Estimated Female Functional Support Evacuees"
        ),
        "Mean Transfer Distance": mean_distance,
        "Maximum Transfer Distance": max_distance,
    }


def validate(frame: pd.DataFrame, screen: pd.DataFrame, performance: pd.DataFrame) -> None:
    required = {
        "Municipality",
        "Shelter Number",
        "Latitude",
        "Longitude",
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
    if frame[list(required)].isna().any().any():
        raise ValueError("Required scenario-performance fields must be complete")
    if len(screen) != 38 or int(screen["Screening Shortfall"].sum()) != 31:
        raise ValueError("Expected 38 Yatsushiro shelters and a 31-unit current screen")
    expected = {
        "none": (0, 0, 31, 11),
        "zero": (5, 5, 26, 9),
        "full": (72, 31, 0, 0),
    }
    for _, row in performance.iterrows():
        observed = (
            int(row["Eligible Donor Units"]),
            int(row["Transferred Units"]),
            int(row["Residual Screening Shortfall"]),
            int(row["Shelters with Residual Shortfall"]),
        )
        if observed != expected[str(row["Scenario"])]:
            raise ValueError(f"Unexpected performance for {row['Scenario']}: {observed}")
    full = performance.loc[performance["Scenario"].eq("full")].iloc[0]
    coverage_columns = [
        "Evacuee Coverage",
        "Functional Support Coverage",
        "Female Functional Support Coverage",
    ]
    if not np.allclose(full[coverage_columns].astype(float), 100.0):
        raise ValueError("Full mobility must resolve 100% of initial-recipient demand")


def draw_operational_panel(ax: plt.Axes, performance: pd.DataFrame) -> None:
    x_positions = np.arange(len(SCENARIOS))
    width = 0.23
    metrics = (
        ("Transferred Units", "Transferred units"),
        ("Residual Screening Shortfall", "Residual screening shortfall"),
        ("Shelters with Residual Shortfall", "Shelters with residual shortfall"),
    )
    for metric_index, (column, label) in enumerate(metrics):
        positions = x_positions + (metric_index - 1) * width
        values = performance[column].to_numpy(dtype=float)
        bars = ax.bar(
            positions,
            values,
            width=width * 0.90,
            color=OUTCOME_COLORS[label],
            edgecolor="white",
            linewidth=0.65,
            label=label,
            zorder=3,
        )
        ax.bar_label(bars, labels=[f"{int(value)}" for value in values], padding=3, fontsize=7.6)

    ax.set_xticks(x_positions, SCENARIO_LABELS)
    ax.tick_params(axis="x", labelsize=7.8, length=0, pad=7)
    ax.tick_params(axis="y", labelsize=7.8, length=2.5)
    ax.set_ylabel("Count (units or shelters)", fontsize=8.8, labelpad=7)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6, integer=True))
    ax.set_ylim(0, 39)
    ax.grid(axis="y", color="#D9DDE1", linewidth=0.55, zorder=0)
    for x_position, eligible in zip(
        x_positions, performance["Eligible Donor Units"], strict=True
    ):
        ax.text(
            x_position,
            35.8,
            f"Eligible donor units: {int(eligible)}",
            ha="center",
            va="top",
            fontsize=7.0,
            color="#52606B",
            bbox={"boxstyle": "round,pad=0.18", "fc": "white", "ec": "#CBD0D4", "linewidth": 0.5},
        )
    ax.legend(
        loc="upper left",
        bbox_to_anchor=(0.0, 1.0),
        ncol=3,
        frameon=False,
        fontsize=6.8,
        handlelength=1.35,
        handletextpad=0.35,
        columnspacing=0.75,
    )
    add_panel_heading(ax, "a", "Operational outcomes across resource-mobility assumptions")


def draw_coverage_panel(ax: plt.Axes, performance: pd.DataFrame) -> None:
    x_positions = np.arange(len(SCENARIOS))
    width = 0.23
    metrics = (
        ("Evacuee Coverage", "Observed evacuees"),
        ("Functional Support Coverage", "Estimated functional support"),
        (
            "Female Functional Support Coverage",
            "Estimated female functional support",
        ),
    )
    for metric_index, (column, label) in enumerate(metrics):
        positions = x_positions + (metric_index - 1) * width
        values = performance[column].to_numpy(dtype=float)
        bars = ax.bar(
            positions,
            values,
            width=width * 0.90,
            color=COVERAGE_COLORS[label],
            edgecolor="white",
            linewidth=0.65,
            label=label,
            zorder=3,
        )
        labels = [f"{value:.1f}%" if 0 < value < 100 else f"{int(round(value))}%" for value in values]
        ax.bar_label(bars, labels=labels, padding=3, fontsize=7.6)

    ax.set_xticks(x_positions, SCENARIO_LABELS)
    ax.tick_params(axis="x", labelsize=7.8, length=0, pad=7)
    ax.tick_params(axis="y", labelsize=7.8, length=2.5)
    ax.set_ylabel("Demand at fully resolved recipient sites", fontsize=8.8, labelpad=7)
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=100, decimals=0))
    ax.set_ylim(0, 116)
    ax.set_yticks(np.arange(0, 101, 20))
    ax.grid(axis="y", color="#D9DDE1", linewidth=0.55, zorder=0)
    ax.legend(
        loc="upper left",
        ncol=1,
        frameon=False,
        fontsize=7.5,
        handlelength=1.5,
        handletextpad=0.45,
    )
    add_panel_heading(
        ax,
        "b",
        "Resolved-site demand coverage · denominator is the initial 11-shelter shortfall set",
    )


def main() -> None:
    frame = pd.read_parquet(SOURCE)
    base = frame.loc[
        frame["Municipality"].eq(TARGET_MUNICIPALITY)
        & frame["Scenario"].astype("string").eq("base")
    ].copy()
    screen = construct_screen(base)
    performance = pd.DataFrame(
        [evaluate_scenario(screen, scenario) for scenario in SCENARIOS]
    )
    performance["Scenario"] = pd.Categorical(
        performance["Scenario"], categories=SCENARIOS, ordered=True
    )
    performance = performance.sort_values("Scenario").reset_index(drop=True)
    validate(base, screen, performance)

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
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 6.0), gridspec_kw={"width_ratios": [1, 1]})
    fig.subplots_adjust(left=0.075, right=0.985, bottom=0.18, top=0.91, wspace=0.21)
    draw_operational_panel(axes[0], performance)
    draw_coverage_panel(axes[1], performance)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
