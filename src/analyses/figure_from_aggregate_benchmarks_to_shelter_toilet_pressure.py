#!/usr/bin/env python3
"""From Aggregate Benchmarks to Shelter Toilet Pressure.

Plan: Connect pooled versus sitewise requirements to Yatsushiro priority-site
temporary-toilet pressure and water-stratified total and functional-support
demand.
Framework: Section 5 fragmentation, deployment-screen, and water-status
contrasts; Section 6 benchmark, shortfall, and grouped-summary formulas;
Section 7 descriptive pressure workflow. Temporary-toilet shortfall is a field-
verification signal, not a verified functional-capacity deficit.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd
import seaborn as sns

from figure_shelter_toilet_pressure_and_reported_deployment import english_facility_type


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/processed/shelter_equity_scenarios_preprocessed.parquet"
OUTPUT = (
    ROOT
    / "data/results/figures/"
    "Figure_from_aggregate_benchmarks_to_shelter_toilet_pressure.png"
)

CITY_ORDER = ("八代市", "熊本市")
CITY_LABELS = {"八代市": "Yatsushiro", "熊本市": "Kumamoto"}
BENCHMARKS = (("Initial", 50), ("Prolonged", 20))
POOLED_COLOR = "#A6ADB4"
SITEWISE_COLOR = "#2F6F9F"
REQUIREMENT_COLOR = "#C65345"
TEMPORARY_COLOR = "#3B73A1"
TOILET_CAR_COLOR = "#D3A24D"
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
        -0.085,
        1.04,
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
        1.04,
        heading,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9.2,
        fontweight="bold",
        color="#263746",
    )


def point_size(shortfall) -> np.ndarray:
    return 28 + 7 * np.asarray(shortfall)


def build_comparison(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    for benchmark, people_per_toilet in BENCHMARKS:
        for municipality in CITY_ORDER:
            city = frame.loc[frame["Municipality"].eq(municipality)]
            evacuees = int(city["Evacuees"].sum())
            pooled = int(np.ceil(evacuees / people_per_toilet))
            sitewise = int(np.ceil(city["Evacuees"] / people_per_toilet).sum())
            rows.append(
                {
                    "Benchmark": benchmark,
                    "Municipality": municipality,
                    "Pooled": pooled,
                    "Sitewise": sitewise,
                    "Increment": sitewise - pooled,
                    "Increment Percent": 100 * (sitewise - pooled) / pooled,
                }
            )
    comparison = pd.DataFrame(rows)
    if len(comparison) != 4 or (comparison["Sitewise"] < comparison["Pooled"]).any():
        raise ValueError("Invalid pooled-versus-sitewise comparison")
    return comparison


def draw_requirement_panel(ax: plt.Axes, comparison: pd.DataFrame) -> None:
    x = np.arange(len(comparison), dtype=float)
    width = 0.32
    pooled = ax.bar(
        x - width / 2,
        comparison["Pooled"],
        width=width,
        color=POOLED_COLOR,
        edgecolor="white",
        linewidth=0.7,
        zorder=3,
    )
    sitewise = ax.bar(
        x + width / 2,
        comparison["Sitewise"],
        width=width,
        color=SITEWISE_COLOR,
        edgecolor="white",
        linewidth=0.7,
        zorder=3,
    )
    for bars in (pooled, sitewise):
        ax.bar_label(
            bars,
            labels=[f"{int(value)}" for value in bars.datavalues],
            padding=2.5,
            fontsize=7.4,
            fontweight="bold",
            color="#263746",
        )
    maximum = float(comparison["Sitewise"].max())
    for row_index, row in comparison.iterrows():
        ax.text(
            row_index,
            float(row["Sitewise"]) + maximum * 0.10,
            f"+{int(row['Increment'])}\n(+{row['Increment Percent']:.0f}%)",
            ha="center",
            va="bottom",
            fontsize=7.1,
            color="#44515B",
        )
    labels = [
        f"{row.Benchmark}\n{CITY_LABELS[row.Municipality]}"
        for row in comparison.itertuples(index=False)
    ]
    ax.set_xticks(x, labels)
    ax.tick_params(axis="x", labelsize=7.5, length=0, pad=6)
    ax.tick_params(axis="y", labelsize=7.8, length=2.5)
    ax.set_ylabel("Required toilet units", fontsize=8.7, labelpad=6)
    ax.set_ylim(0, maximum * 1.30)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6, integer=True))
    ax.grid(axis="y", color="#D9DDE1", linewidth=0.55, zorder=0)
    ax.legend(
        handles=[
            Patch(facecolor=POOLED_COLOR, edgecolor="white", label="Pooled city"),
            Patch(facecolor=SITEWISE_COLOR, edgecolor="white", label="Sum of shelter-specific"),
        ],
        loc="upper left",
        frameon=False,
        fontsize=7.1,
        handlelength=1.4,
        handletextpad=0.4,
    )
    add_panel_heading(ax, "a", "Aggregate versus sitewise benchmark requirements")


def draw_priority_panel(
    demand_ax: plt.Axes,
    car_ax: plt.Axes,
    priority: pd.DataFrame,
) -> None:
    priority = priority.sort_values(
        ["Temporary-Toilet-Only Shortfall", "Evacuees", "Shelter Number"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    y = np.arange(len(priority))
    for row in range(len(priority)):
        if row % 2 == 0:
            demand_ax.axhspan(row - 0.5, row + 0.5, color="#F5F6F7", zorder=0)
            car_ax.axhspan(row - 0.5, row + 0.5, color="#F5F6F7", zorder=0)
    demand_ax.hlines(
        y,
        priority["Temporary Toilets Installed"],
        priority["Prolonged Requirement"],
        color="#D58B80",
        linewidth=2.0,
        zorder=2,
    )
    demand_ax.scatter(
        priority["Temporary Toilets Installed"],
        y,
        marker="s",
        s=35,
        color=TEMPORARY_COLOR,
        edgecolor="white",
        linewidth=0.55,
        zorder=4,
        label="Reported temporary toilets",
    )
    demand_ax.scatter(
        priority["Prolonged Requirement"],
        y,
        marker="o",
        s=36,
        color=REQUIREMENT_COLOR,
        edgecolor="white",
        linewidth=0.55,
        zorder=4,
        label="Prolonged requirement",
    )
    for row_index, row in priority.iterrows():
        demand_ax.text(
            float(row["Prolonged Requirement"]) + 0.35,
            row_index,
            f"+{int(row['Temporary-Toilet-Only Shortfall'])}",
            ha="left",
            va="center",
            fontsize=6.8,
            color=REQUIREMENT_COLOR,
            fontweight="bold",
        )
    labels = [
        f"Y{int(number):02d}  {english_facility_type(str(name))}"
        for number, name in zip(
            priority["Shelter Number"], priority["Shelter Name"], strict=True
        )
    ]
    demand_ax.set_yticks(y, labels, fontsize=6.7)
    demand_ax.tick_params(axis="y", length=0, pad=4)
    demand_ax.tick_params(axis="x", labelsize=7.5, length=2.5)
    demand_ax.set_ylim(len(priority) - 0.45, -0.55)
    demand_ax.set_xlim(0, float(priority["Prolonged Requirement"].max()) + 3.0)
    demand_ax.xaxis.set_major_locator(MaxNLocator(nbins=6, integer=True))
    demand_ax.grid(axis="x", color="#D9DDE1", linewidth=0.5, zorder=0)
    demand_ax.set_xlabel("Toilet units", fontsize=8.2, labelpad=6)
    demand_ax.legend(
        loc="lower right",
        frameon=False,
        fontsize=6.6,
        handletextpad=0.35,
        borderaxespad=0.5,
    )

    car_ax.scatter(
        priority["Toilet Cars"],
        y,
        marker="^",
        s=38,
        color=TOILET_CAR_COLOR,
        edgecolor="white",
        linewidth=0.55,
        zorder=4,
    )
    car_ax.set_ylim(len(priority) - 0.45, -0.55)
    car_ax.set_xlim(-0.15, max(1.25, float(priority["Toilet Cars"].max()) + 0.4))
    car_ax.xaxis.set_major_locator(MaxNLocator(nbins=3, integer=True))
    car_ax.tick_params(axis="x", labelsize=7.3, length=2.5)
    car_ax.tick_params(axis="y", left=False, labelleft=False)
    car_ax.grid(axis="x", color="#D9DDE1", linewidth=0.5, zorder=0)
    car_ax.set_xlabel("Toilet-car\nvehicles", fontsize=7.6, labelpad=4)
    add_panel_heading(demand_ax, "b", "Yatsushiro priority-site temporary-toilet screen")


def add_water_points(ax: plt.Axes, frame: pd.DataFrame, y_column: str) -> None:
    plotted_groups: list[pd.DataFrame] = []
    for category_index, category in enumerate(WATER_ORDER):
        group = frame.loc[frame["Water Group"].eq(category)].sort_values("Shelter Number").copy()
        jitter = np.linspace(-0.16, 0.16, len(group)) if len(group) > 1 else np.array([0.0])
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
        plotted_groups.append(group)
    plotted = pd.concat(plotted_groups, ignore_index=True)
    label_rows = (
        plotted.sort_values(["Water Group", y_column], ascending=[True, False])
        .groupby("Water Group", observed=True, sort=False)
        .head(1)
    )
    for _, row in label_rows.iterrows():
        ax.annotate(
            f"Y{int(row['Shelter Number']):02d}",
            xy=(row["Plot X"], row[y_column]),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=6.8,
            color="#263746",
            bbox={
                "boxstyle": "round,pad=0.12",
                "fc": "white",
                "ec": "#71818C",
                "linewidth": 0.45,
                "alpha": 0.96,
            },
            zorder=7,
        )


def draw_water_panel(
    ax: plt.Axes,
    frame: pd.DataFrame,
    y_column: str,
    y_label: str,
    panel_label: str,
    heading: str,
) -> None:
    sns.boxplot(
        data=frame,
        x="Water Group",
        y=y_column,
        order=WATER_ORDER,
        palette=WATER_COLORS,
        hue="Water Group",
        legend=False,
        width=0.56,
        linewidth=0.85,
        showfliers=False,
        saturation=0.9,
        ax=ax,
        zorder=2,
    )
    add_water_points(ax, frame, y_column)
    counts = frame["Water Group"].value_counts()
    ax.set_xticks(
        np.arange(len(WATER_ORDER)),
        [f"{WATER_LABELS[category]}\nn={int(counts[category])}" for category in WATER_ORDER],
    )
    ax.set_xlabel("")
    ax.set_ylabel(y_label, fontsize=8.7, labelpad=6)
    ax.tick_params(axis="x", labelsize=7.5, length=0, pad=6)
    ax.tick_params(axis="y", labelsize=7.8, length=2.5)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6, min_n_ticks=4))
    ax.grid(axis="y", color="#D9DDE1", linewidth=0.55, zorder=0)
    ax.set_ylim(bottom=-0.02 * max(float(frame[y_column].max()), 1.0))
    add_panel_heading(ax, panel_label, heading)


def main() -> None:
    frame = pd.read_parquet(SOURCE)
    required = {
        "Municipality",
        "Shelter Number",
        "Shelter Name",
        "Evacuees",
        "Water Status",
        "Temporary Toilets Installed",
        "Toilet Cars",
        "Scenario",
        "Estimated Functional Support Evacuees",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")
    base = frame.loc[frame["Scenario"].astype("string").eq("base")].copy()
    if len(base) != 53 or base.duplicated(["Municipality", "Shelter Number"]).any():
        raise ValueError("Expected 53 unique shelters in the matched base scenario")
    expected = {"八代市": (38, 1852), "熊本市": (15, 280)}
    for municipality, (shelters, evacuees) in expected.items():
        city = base.loc[base["Municipality"].eq(municipality)]
        if len(city) != shelters or int(city["Evacuees"].sum()) != evacuees:
            raise ValueError(f"Matched sample does not reproduce {municipality} totals")
    comparison = build_comparison(base)

    yatsushiro = base.loc[base["Municipality"].eq("八代市")].copy()
    if yatsushiro[list(required.difference({"Municipality", "Scenario"}))].isna().any().any():
        raise ValueError("Yatsushiro pressure fields must be complete")
    yatsushiro["Water Group"] = yatsushiro["Water Status"].astype(str).map(
        {"〇": "Available", "○": "Available", "△": "Partial", "×": "Unavailable"}
    )
    if yatsushiro["Water Group"].isna().any():
        raise ValueError("Unrecognized Yatsushiro water status")
    observed_counts = yatsushiro["Water Group"].value_counts().to_dict()
    if observed_counts != {"Available": 19, "Unavailable": 13, "Partial": 6}:
        raise ValueError(f"Unexpected water-status counts: {observed_counts}")
    yatsushiro["Prolonged Requirement"] = np.ceil(yatsushiro["Evacuees"] / 20).astype(int)
    yatsushiro["Temporary-Toilet-Only Shortfall"] = (
        yatsushiro["Prolonged Requirement"] - yatsushiro["Temporary Toilets Installed"]
    ).clip(lower=0).astype(int)
    if int(yatsushiro["Temporary-Toilet-Only Shortfall"].sum()) != 31:
        raise ValueError("Unexpected Yatsushiro temporary-toilet-only shortfall total")
    priority = yatsushiro.loc[yatsushiro["Temporary-Toilet-Only Shortfall"].gt(0)].copy()
    if len(priority) != 11:
        raise ValueError("Expected 11 positive-screening-shortfall shelters")

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
    fig = plt.figure(figsize=(13.3, 9.2))
    outer = fig.add_gridspec(
        3,
        1,
        height_ratios=(0.92, 1.0, 0.045),
        hspace=0.25,
    )
    top_grid = outer[0, 0].subgridspec(1, 2, wspace=0.34)
    bottom_grid = outer[1, 0].subgridspec(1, 2, wspace=0.20)
    requirement_ax = fig.add_subplot(top_grid[0, 0])
    priority_grid = top_grid[0, 1].subgridspec(
        1, 2, width_ratios=(0.76, 0.24), wspace=0.045
    )
    priority_ax = fig.add_subplot(priority_grid[0, 0])
    car_ax = fig.add_subplot(priority_grid[0, 1], sharey=priority_ax)
    water_ax = fig.add_subplot(bottom_grid[0, 0])
    support_ax = fig.add_subplot(bottom_grid[0, 1])
    legend_axis = fig.add_subplot(outer[2, 0])
    legend_axis.set_axis_off()

    draw_requirement_panel(requirement_ax, comparison)
    draw_priority_panel(priority_ax, car_ax, priority)
    draw_water_panel(
        water_ax,
        yatsushiro,
        "Evacuees",
        "Observed evacuees (persons)",
        "c",
        "Yatsushiro demand by water status",
    )
    draw_water_panel(
        support_ax,
        yatsushiro,
        "Estimated Functional Support Evacuees",
        "Estimated functional-support evacuees",
        "d",
        "Yatsushiro functional-support demand by water status",
    )
    shortfall_levels = (0, 1, 5, 10)
    legend_axis.legend(
        handles=[
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
        ],
        title="Temporary-toilet-only screening shortfall (units)",
        loc="center",
        ncol=4,
        frameon=False,
        fontsize=7.8,
        title_fontsize=8.0,
        handletextpad=0.35,
        columnspacing=1.2,
    )
    fig.subplots_adjust(left=0.105, right=0.985, bottom=0.045, top=0.97)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
