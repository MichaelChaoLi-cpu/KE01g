#!/usr/bin/env python3
"""Water Status and Equity-Weighted Toilet Pressure.

Plan: Compare observed occupancy and base functional-support demand across
reported water-service categories, while showing temporary-toilet-only
screening pressure for each Yatsushiro shelter.
Framework: Section 5 water-status stratification; Section 6 water-severity and
temporary-toilet-only screening formulas; Section 7 grouped pressure screen.
Water is an operability proxy and the shortfall is not a functional-capacity gap.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd
import seaborn as sns


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/processed/shelter_equity_scenarios_preprocessed.parquet"
OUTPUT = (
    ROOT
    / "data/results/figures/"
    "Figure_water_status_and_equity_weighted_toilet_pressure.png"
)

WATER_ORDER = ("Available", "Partial", "Unavailable")
WATER_LABELS = {
    "Available": "Available",
    "Partial": "Partially available",
    "Unavailable": "Unavailable",
}
WATER_COLORS = {
    "Available": "#C9DDD5",
    "Partial": "#EED9AD",
    "Unavailable": "#E5BCB5",
}
POINT_ZERO = "#587B91"
POINT_POSITIVE = "#C65345"


def add_panel_heading(ax: plt.Axes, label: str, heading: str) -> None:
    ax.text(
        -0.09,
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
        -0.02,
        1.035,
        heading,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9.5,
        fontweight="bold",
        color="#263746",
    )


def point_size(shortfall: pd.Series | np.ndarray | float) -> pd.Series | np.ndarray | float:
    return 30 + 7 * np.asarray(shortfall)


def add_points_and_labels(
    ax: plt.Axes,
    frame: pd.DataFrame,
    y_column: str,
) -> None:
    plotted_rows: list[pd.DataFrame] = []
    for category_index, category in enumerate(WATER_ORDER):
        group = (
            frame.loc[frame["Water Group"].eq(category)]
            .sort_values("Shelter Number")
            .copy()
        )
        jitter = (
            np.linspace(-0.16, 0.16, len(group))
            if len(group) > 1
            else np.array([0.0])
        )
        group["Plot X"] = category_index + jitter
        colors = np.where(
            group["Temporary-Toilet-Only Shortfall"].gt(0),
            POINT_POSITIVE,
            POINT_ZERO,
        )
        ax.scatter(
            group["Plot X"],
            group[y_column],
            s=point_size(group["Temporary-Toilet-Only Shortfall"]),
            color=colors,
            edgecolor="white",
            linewidth=0.55,
            alpha=0.90,
            zorder=4,
        )
        plotted_rows.append(group)

    plotted = pd.concat(plotted_rows, ignore_index=True)
    label_rows = (
        plotted.sort_values(["Water Group", y_column], ascending=[True, False])
        .groupby("Water Group", observed=True, sort=False)
        .head(1)
    )
    offsets = {
        "Available": (-8, 8),
        "Partial": (8, 8),
        "Unavailable": (8, 8),
    }
    for _, row in label_rows.iterrows():
        dx, dy = offsets[str(row["Water Group"])]
        ax.annotate(
            f"Y{int(row['Shelter Number']):02d}",
            xy=(row["Plot X"], row[y_column]),
            xytext=(dx, dy),
            textcoords="offset points",
            ha="right" if dx < 0 else "left",
            va="bottom",
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
        "Evacuees",
        "Water Status",
        "Temporary Toilets Installed",
        "Scenario",
        "Estimated Functional Support Evacuees",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")
    base = frame.loc[
        frame["Scenario"].astype("string").eq("base")
        & frame["Municipality"].eq("八代市")
    ].copy()
    if len(base) != 38:
        raise ValueError("Expected 38 Yatsushiro shelters in the base scenario")
    if base[list(required.difference({"Municipality", "Scenario"}))].isna().any().any():
        raise ValueError("Yatsushiro water-pressure fields must be complete")
    if (base[["Evacuees", "Temporary Toilets Installed", "Estimated Functional Support Evacuees"]] < 0).any().any():
        raise ValueError("Demand and deployment fields cannot be negative")

    base["Water Group"] = base["Water Status"].astype(str).map(
        {
            "〇": "Available",
            "○": "Available",
            "△": "Partial",
            "×": "Unavailable",
        }
    )
    if base["Water Group"].isna().any():
        unknown = sorted(base.loc[base["Water Group"].isna(), "Water Status"].astype(str).unique())
        raise ValueError(f"Unrecognized water-status values: {unknown}")
    observed_counts = base["Water Group"].value_counts().to_dict()
    if observed_counts != {"Available": 19, "Unavailable": 13, "Partial": 6}:
        raise ValueError(f"Unexpected water-status counts: {observed_counts}")

    base["Prolonged Requirement"] = np.ceil(base["Evacuees"] / 20).astype(int)
    base["Temporary-Toilet-Only Shortfall"] = (
        base["Prolonged Requirement"] - base["Temporary Toilets Installed"]
    ).clip(lower=0)
    if float(base["Temporary-Toilet-Only Shortfall"].sum()) != 31.0:
        raise ValueError("Unexpected Yatsushiro temporary-toilet-only shortfall total")

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
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 6.2))
    fig.subplots_adjust(left=0.08, right=0.985, bottom=0.20, top=0.92, wspace=0.20)

    panels = (
        ("Evacuees", "Observed shelter occupancy", "Observed evacuees (persons)"),
        (
            "Estimated Functional Support Evacuees",
            "Base functional-support demand",
            "Estimated functional-support evacuees (persons)",
        ),
    )
    counts = base["Water Group"].value_counts()
    x_labels = [
        f"{WATER_LABELS[category]}\nn={int(counts[category])}"
        for category in WATER_ORDER
    ]

    for panel_index, (ax, (y_column, heading, y_label)) in enumerate(
        zip(axes, panels, strict=True)
    ):
        sns.boxplot(
            data=base,
            x="Water Group",
            y=y_column,
            order=WATER_ORDER,
            palette=WATER_COLORS,
            width=0.56,
            linewidth=0.85,
            showfliers=False,
            saturation=0.9,
            ax=ax,
            zorder=2,
        )
        add_points_and_labels(ax, base, y_column)
        ax.set_xlabel("")
        ax.set_ylabel(y_label, fontsize=9.0, labelpad=7)
        ax.set_xticks(np.arange(len(WATER_ORDER)), x_labels)
        ax.tick_params(axis="x", labelsize=8.0, length=0, pad=7)
        ax.tick_params(axis="y", labelsize=8.0, length=2.5, pad=2)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=6, min_n_ticks=4))
        ax.grid(axis="y", color="#D9DDE1", linewidth=0.55, zorder=0)
        ax.set_ylim(bottom=-0.02 * max(float(base[y_column].max()), 1.0))
        add_panel_heading(ax, chr(ord("a") + panel_index), f"Yatsushiro: {heading}")

    shortfall_levels = (0, 1, 5, 10)
    legend_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=POINT_ZERO if level == 0 else POINT_POSITIVE,
            markeredgecolor="white",
            markeredgewidth=0.55,
            markersize=np.sqrt(float(point_size(level))),
            label=str(level),
        )
        for level in shortfall_levels
    ]
    fig.legend(
        handles=legend_handles,
        title="Temporary-toilet-only screening shortfall S (units)",
        loc="lower center",
        ncol=4,
        frameon=False,
        fontsize=8.0,
        title_fontsize=8.2,
        handletextpad=0.35,
        columnspacing=1.25,
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
