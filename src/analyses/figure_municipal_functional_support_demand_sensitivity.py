#!/usr/bin/env python3
"""Municipal Functional-Support Demand Sensitivity.

Plan: Compare Narrow, Core, and Broad total and female functional-support
demand across the 11 affected municipalities.
Framework: Section 5 scope-sensitivity design; Section 6 municipality
functional-support estimands and rank robustness; Section 7 comparison across
certification scopes. Values are planning proxies, not observed evacuee need.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator, FuncFormatter, NullFormatter
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/processed/municipality_equity_scenarios_preprocessed.parquet"
OUTPUT = (
    ROOT
    / "data/results/figures/"
    "Figure_municipal_functional_support_demand_sensitivity.png"
)

SCENARIOS = ("Narrow", "Core", "Broad")
SCENARIO_STYLE = {
    "Narrow": {"color": "#3B73A1", "marker": "o"},
    "Core": {"color": "#D2644F", "marker": "s"},
    "Broad": {"color": "#3C8D76", "marker": "^"},
}
PANELS = (
    (
        "Municipality Estimated Functional Support Evacuees",
        "Estimated functional-support evacuees (persons, log scale)",
    ),
    (
        "Municipality Estimated Female Functional Support Evacuees",
        "Estimated female functional-support evacuees (persons, log scale)",
    ),
)
TICKS = (0.1, 0.3, 1, 3, 10, 30, 100, 200)


def tick_label(value: float, _position: int) -> str:
    if value < 1:
        return f"{value:g}"
    return f"{value:,.0f}"


def add_panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.055,
        1.025,
        label,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=12,
        fontweight="bold",
        color="#263746",
    )


def main() -> None:
    frame = pd.read_parquet(SOURCE).rename(
        columns={
            "Estimated Functional Support Evacuees": (
                "Municipality Estimated Functional Support Evacuees"
            ),
            "Estimated Female Functional Support Evacuees": (
                "Municipality Estimated Female Functional Support Evacuees"
            ),
        }
    )
    required = {
        "Municipality",
        "Functional Support Scenario",
        "Municipality Estimated Functional Support Evacuees",
        "Municipality Estimated Female Functional Support Evacuees",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")
    if len(frame) != 33 or frame["Municipality"].nunique() != 11:
        raise ValueError("Expected 33 municipality-scenario records for 11 municipalities")
    observed_scenarios = set(frame["Functional Support Scenario"].astype(str))
    if observed_scenarios != set(SCENARIOS):
        raise ValueError(f"Unexpected scenarios: {sorted(observed_scenarios)}")
    if frame[list(required.difference({"Municipality", "Functional Support Scenario"}))].isna().any().any():
        raise ValueError("Sensitivity variables contain missing values")

    pivots = {
        column: frame.pivot(
            index="Municipality",
            columns="Functional Support Scenario",
            values=column,
        ).loc[:, list(SCENARIOS)]
        for column, _label in PANELS
    }
    for column, pivot in pivots.items():
        if not ((pivot["Narrow"] <= pivot["Core"]) & (pivot["Core"] <= pivot["Broad"])).all():
            raise ValueError(f"Scenario scope is not monotonic for {column}")
        if (pivot <= 0).any().any():
            raise ValueError(f"Log-scale values must be positive for {column}")

    order = (
        pivots["Municipality Estimated Functional Support Evacuees"]["Core"]
        .sort_values(ascending=False)
        .index.tolist()
    )
    y_positions = np.arange(len(order))

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.edgecolor": "#4B5563",
            "axes.linewidth": 0.8,
            "xtick.color": "#3F4854",
            "ytick.color": "#263746",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(11.4, 6.2),
        sharey=True,
        constrained_layout=True,
    )
    fig.set_constrained_layout_pads(w_pad=0.04, h_pad=0.04, wspace=0.055, hspace=0.02)

    for panel_index, (ax, (column, x_label)) in enumerate(zip(axes, PANELS, strict=True)):
        pivot = pivots[column].loc[order]
        for row in range(len(order)):
            if row % 2 == 0:
                ax.axhspan(row - 0.5, row + 0.5, color="#F6F7F8", zorder=0)
        ax.hlines(
            y_positions,
            pivot["Narrow"],
            pivot["Broad"],
            color="#A7ADB4",
            linewidth=1.4,
            zorder=2,
        )
        for scenario in SCENARIOS:
            style = SCENARIO_STYLE[scenario]
            ax.scatter(
                pivot[scenario],
                y_positions,
                s=37 if scenario == "Core" else 32,
                color=style["color"],
                marker=style["marker"],
                edgecolor="white",
                linewidth=0.55,
                zorder=4,
            )

        ax.set_xscale("log")
        ax.set_xlim(0.075, 210)
        ax.xaxis.set_major_locator(FixedLocator(TICKS))
        ax.xaxis.set_major_formatter(FuncFormatter(tick_label))
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.grid(axis="x", which="major", color="#D5D8DC", linewidth=0.55, zorder=1)
        ax.grid(axis="x", which="minor", color="#ECEDEF", linewidth=0.35, zorder=1)
        ax.tick_params(axis="x", which="both", labelsize=8.0, length=2.5, pad=2)
        ax.tick_params(axis="y", length=0, pad=6)
        ax.set_xlabel(x_label, fontsize=9.0, labelpad=7)
        ax.set_ylim(len(order) - 0.45, -0.55)
        add_panel_label(ax, chr(ord("a") + panel_index))

    axes[0].set_yticks(y_positions, labels=order, fontsize=8.7)
    axes[1].tick_params(axis="y", labelleft=False)

    legend_handles = [
        Line2D(
            [0],
            [0],
            marker=SCENARIO_STYLE[scenario]["marker"],
            color="none",
            markerfacecolor=SCENARIO_STYLE[scenario]["color"],
            markeredgecolor="white",
            markeredgewidth=0.55,
            markersize=7,
            label=scenario,
        )
        for scenario in SCENARIOS
    ]
    fig.legend(
        handles=legend_handles,
        loc="outside lower center",
        ncol=3,
        frameon=False,
        fontsize=8.5,
        handletextpad=0.45,
        columnspacing=1.6,
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
