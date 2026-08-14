#!/usr/bin/env python3
"""Estimated Female and Intersectional Demand by Shelter.

Plan: Compare scenario-estimated female demand with female functional-support
demand for every matched shelter in Kumamoto City and Yatsushiro City.
Framework: Section 5 synthetic equity-demand screening; Section 6 catchment
shares and low/base/high overlap scenarios; Section 7 shelter comparison.
Values are planning estimates, not observed shelter subgroup composition.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/processed/shelter_equity_scenarios_preprocessed.parquet"
OUTPUT = (
    ROOT
    / "data/results/figures/"
    "Figure_estimated_female_and_intersectional_demand_by_shelter.png"
)

SCENARIOS = ("low", "base", "high")
CITY_STYLE = {
    "八代市": {"label": "Yatsushiro City", "prefix": "Y", "color": "#2F6F9F"},
    "熊本市": {"label": "Kumamoto City", "prefix": "K", "color": "#D2644F"},
}
LOCATION_STYLE = {
    "exact shelter master match": {"marker": "o", "label": "Exact shelter point"},
    "district anchor fallback": {"marker": "^", "label": "District-anchor fallback"},
}


def shelter_code(municipality: str, number: float) -> str:
    return f"{CITY_STYLE[municipality]['prefix']}{int(number):02d}"


def add_panel_heading(ax: plt.Axes, label: str, heading: str) -> None:
    ax.text(
        -0.085,
        1.035,
        label,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=12,
        fontweight="bold",
        color="#263746",
    )
    ax.text(
        -0.025,
        1.035,
        heading,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9.5,
        fontweight="bold",
        color="#263746",
    )


def label_priority_shelters(
    ax: plt.Axes,
    frame: pd.DataFrame,
    x_column: str,
    y_column: str,
) -> None:
    offset_patterns = {
        "八代市": ((-8, 8), (-8, 8), (8, -10)),
        "熊本市": ((8, 8), (-8, 10), (8, -12)),
    }
    for municipality, offsets in offset_patterns.items():
        selected = (
            frame.loc[frame["Municipality"].eq(municipality)]
            .sort_values(y_column, ascending=False)
            .head(3)
            .reset_index(drop=True)
        )
        for (_, row), (dx, dy) in zip(selected.iterrows(), offsets, strict=True):
            ax.annotate(
                row["Shelter Code"],
                xy=(row[x_column], row[y_column]),
                xytext=(dx, dy),
                textcoords="offset points",
                ha="left" if dx >= 0 else "right",
                va="bottom" if dy >= 0 else "top",
                fontsize=7.2,
                color="#263746",
                bbox={
                    "boxstyle": "round,pad=0.13",
                    "fc": "white",
                    "ec": "#71818C",
                    "linewidth": 0.5,
                    "alpha": 0.96,
                },
                arrowprops={
                    "arrowstyle": "-",
                    "color": "#7D8991",
                    "linewidth": 0.5,
                    "shrinkA": 2.0,
                    "shrinkB": 2.0,
                },
                zorder=7,
            )


def main() -> None:
    frame = pd.read_parquet(SOURCE)
    required = {
        "Municipality",
        "Shelter Number",
        "Shelter Name",
        "Evacuees",
        "Location Resolution",
        "Scenario",
        "Estimated Female Evacuees",
        "Estimated Female Functional Support Evacuees",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")
    if len(frame) != 159 or frame["Shelter Name"].nunique() != 53:
        raise ValueError("Expected 159 records for 53 shelters and three scenarios")
    if set(frame["Scenario"].astype(str)) != set(SCENARIOS):
        raise ValueError("Expected low, base, and high scenarios")
    if frame[list(required)].isna().any().any():
        raise ValueError("Required shelter equity-demand fields contain missing values")

    index_columns = [
        "Municipality",
        "Shelter Number",
        "Shelter Name",
        "Evacuees",
        "Location Resolution",
        "Estimated Female Evacuees",
    ]
    pivot = frame.pivot(
        index=index_columns,
        columns="Scenario",
        values="Estimated Female Functional Support Evacuees",
    ).reset_index()
    pivot.columns.name = None
    if len(pivot) != 53:
        raise ValueError("Expected one scenario range for each of 53 shelters")
    if not ((pivot["low"] <= pivot["base"]) & (pivot["base"] <= pivot["high"])).all():
        raise ValueError("Female functional-support scenarios are not monotonic")
    if (pivot[["Evacuees", "Estimated Female Evacuees", *SCENARIOS]] < 0).any().any():
        raise ValueError("Demand estimates cannot be negative")
    if (pivot["Estimated Female Evacuees"] > pivot["Evacuees"] + 1e-9).any():
        raise ValueError("Estimated female evacuees cannot exceed observed evacuees")
    if (pivot["high"] > pivot["Estimated Female Evacuees"] + 1e-9).any():
        raise ValueError("Female functional-support demand cannot exceed female demand")

    pivot["Shelter Code"] = [
        shelter_code(str(municipality), number)
        for municipality, number in zip(
            pivot["Municipality"], pivot["Shelter Number"], strict=True
        )
    ]

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.edgecolor": "#4B5563",
            "axes.linewidth": 0.8,
            "xtick.color": "#3F4854",
            "ytick.color": "#3F4854",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 6.0))
    fig.subplots_adjust(left=0.075, right=0.985, bottom=0.17, top=0.93, wspace=0.20)

    # Panel a: observed demand transferred through the residential female share.
    ax = axes[0]
    for municipality, city_style in CITY_STYLE.items():
        city = pivot.loc[pivot["Municipality"].eq(municipality)]
        for resolution, location_style in LOCATION_STYLE.items():
            subset = city.loc[city["Location Resolution"].eq(resolution)]
            ax.scatter(
                subset["Evacuees"],
                subset["Estimated Female Evacuees"],
                s=43,
                marker=location_style["marker"],
                color=city_style["color"],
                edgecolor="white",
                linewidth=0.55,
                alpha=0.92,
                zorder=4,
            )
    maximum = float(pivot["Evacuees"].max()) * 1.06
    ax.plot([0, maximum], [0, 0.5 * maximum], color="#8D969E", linewidth=0.8, linestyle="--", zorder=1)
    ax.text(
        0.97,
        0.91,
        "50% reference",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=7.3,
        color="#68737C",
    )
    ax.set_xlim(-0.02 * maximum, maximum)
    ax.set_ylim(bottom=-0.02 * float(pivot["Estimated Female Evacuees"].max()))
    ax.set_xlabel("Observed evacuees (persons)", fontsize=9.0, labelpad=7)
    ax.set_ylabel("Estimated female evacuees (persons)", fontsize=9.0, labelpad=7)
    add_panel_heading(ax, "a", "Female demand screen")
    label_priority_shelters(ax, pivot, "Evacuees", "Estimated Female Evacuees")

    # Panel b: base estimate plus the full low-high overlap-scenario range.
    ax = axes[1]
    for municipality, city_style in CITY_STYLE.items():
        city = pivot.loc[pivot["Municipality"].eq(municipality)]
        ax.vlines(
            city["Estimated Female Evacuees"],
            city["low"],
            city["high"],
            color=city_style["color"],
            linewidth=0.85,
            alpha=0.38,
            zorder=2,
        )
        for resolution, location_style in LOCATION_STYLE.items():
            subset = city.loc[city["Location Resolution"].eq(resolution)]
            ax.scatter(
                subset["Estimated Female Evacuees"],
                subset["base"],
                s=43,
                marker=location_style["marker"],
                color=city_style["color"],
                edgecolor="white",
                linewidth=0.55,
                alpha=0.92,
                zorder=4,
            )
    ax.set_xlim(left=-0.02 * float(pivot["Estimated Female Evacuees"].max()))
    ax.set_ylim(bottom=-0.02 * float(pivot["high"].max()))
    ax.set_xlabel("Estimated female evacuees (persons)", fontsize=9.0, labelpad=7)
    ax.set_ylabel(
        "Estimated female functional-support evacuees (persons)",
        fontsize=9.0,
        labelpad=7,
    )
    add_panel_heading(ax, "b", "Female functional-support screen")
    label_priority_shelters(ax, pivot, "Estimated Female Evacuees", "base")

    for ax in axes:
        ax.grid(color="#D9DDE1", linewidth=0.55, zorder=0)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=6, min_n_ticks=4))
        ax.yaxis.set_major_locator(MaxNLocator(nbins=6, min_n_ticks=4))
        ax.tick_params(axis="both", labelsize=8.0, length=2.5, pad=2)

    legend_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=style["color"],
            markeredgecolor="white",
            markeredgewidth=0.55,
            markersize=7,
            label=style["label"],
        )
        for style in CITY_STYLE.values()
    ]
    legend_handles.extend(
        Line2D(
            [0],
            [0],
            marker=style["marker"],
            color="#59656E",
            markerfacecolor="white",
            markeredgecolor="#59656E",
            markeredgewidth=0.7,
            linewidth=0,
            markersize=6.5,
            label=style["label"],
        )
        for style in LOCATION_STYLE.values()
    )
    legend_handles.append(
        Line2D(
            [0],
            [0],
            color="#7D8991",
            linewidth=1.2,
            alpha=0.65,
            marker="o",
            markerfacecolor="#7D8991",
            markeredgecolor="white",
            markersize=5.5,
            label="Marker: base; line: low-high range",
        )
    )
    fig.legend(
        handles=legend_handles,
        loc="lower center",
        ncol=5,
        frameon=False,
        fontsize=8.0,
        handletextpad=0.45,
        columnspacing=1.25,
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
