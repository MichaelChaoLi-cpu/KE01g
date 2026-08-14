#!/usr/bin/env python3
"""Prefecture-Wide Evacuation and Equity-Demand Screen.

Plan: Combine observed and Core municipality maps with Narrow, Core, and Broad
total and female functional-support demand sensitivity.
Framework: Section 5 two-tier municipality screening; Section 6 municipality
demand, scope-scenario, and ranking equations; Section 7 common-snapshot map
and certification-scope sensitivity workflow. Scenario values are synthetic
planning expectations rather than observed subgroup composition.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.colors import PowerNorm
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator, FuncFormatter, MaxNLocator, NullFormatter
import numpy as np
import pandas as pd
from shapely import from_wkb


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/processed/municipality_equity_scenarios_preprocessed.parquet"
BOUNDARIES = (
    ROOT
    / "data/exp/scenario-planning/"
    "kumamoto_prefecture_administrative_areas_2025_preprocessed.parquet"
)
OUTPUT = (
    ROOT
    / "data/results/figures/"
    "Figure_prefecture_wide_evacuation_and_equity_demand_screen.png"
)

SCENARIOS = ("Narrow", "Core", "Broad")
SCENARIO_STYLE = {
    "Narrow": {"color": "#3B73A1", "marker": "o"},
    "Core": {"color": "#D2644F", "marker": "s"},
    "Broad": {"color": "#3C8D76", "marker": "^"},
}
TICKS = (0.1, 0.3, 1, 3, 10, 30, 100, 200)
BACKGROUND_FILL = "#F2F2EF"
BACKGROUND_LINE = "#A2A2A2"
MUNICIPALITY_LINE = "#767676"
DETAIL_LINE = "#005B96"


def polygon_exteriors(geometry) -> list[np.ndarray]:
    if geometry is None or geometry.is_empty:
        return []
    polygons = geometry.geoms if geometry.geom_type == "MultiPolygon" else (geometry,)
    return [np.asarray(polygon.exterior.coords) for polygon in polygons]


def shared_extent(rings: list[np.ndarray]) -> tuple[float, float, float, float]:
    coordinates = np.vstack(rings)
    x_min, y_min = coordinates.min(axis=0)
    x_max, y_max = coordinates.max(axis=0)
    x_pad = 0.025 * (x_max - x_min)
    y_pad = 0.018 * (y_max - y_min)
    return x_min - x_pad, x_max + x_pad, y_min - y_pad, y_max + y_pad


def add_panel_heading(ax: plt.Axes, label: str, heading: str) -> None:
    ax.text(
        -0.075,
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
        -0.005,
        1.035,
        heading,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9.2,
        fontweight="bold",
        color="#263746",
    )


def add_north_arrow(ax: plt.Axes) -> None:
    ax.annotate(
        "N",
        xy=(0.95, 0.965),
        xytext=(0.95, 0.875),
        xycoords="axes fraction",
        ha="center",
        va="center",
        fontsize=8.5,
        fontweight="bold",
        arrowprops={"arrowstyle": "-|>", "color": "#303030", "lw": 1.0},
        zorder=12,
    )


def add_scale_bar(ax: plt.Axes, latitude: float, length_km: float = 25.0) -> None:
    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()
    length_degrees = length_km / (111.32 * np.cos(np.deg2rad(latitude)))
    x_start = x_min + 0.07 * (x_max - x_min)
    y_start = y_min + 0.045 * (y_max - y_min)
    ax.plot(
        [x_start, x_start + length_degrees],
        [y_start, y_start],
        color="#252525",
        linewidth=2.2,
        solid_capstyle="butt",
        zorder=12,
    )
    ax.text(
        x_start + length_degrees / 2,
        y_start + 0.011,
        f"{length_km:g} km",
        ha="center",
        va="bottom",
        fontsize=7.0,
        color="#252525",
        zorder=12,
    )


def tick_label(value: float, _position: int) -> str:
    return f"{value:g}" if value < 1 else f"{value:,.0f}"


def draw_map(
    ax: plt.Axes,
    color_axis: plt.Axes,
    core_by_code: pd.DataFrame,
    rings_by_code: dict[str, list[np.ndarray]],
    all_rings: list[np.ndarray],
    extent: tuple[float, float, float, float],
    shelter_detail_codes: set[str],
    column: str,
    cmap_name: str,
    colorbar_label: str,
    panel_label: str,
    heading: str,
) -> None:
    values = core_by_code[column].astype(float)
    norm = PowerNorm(gamma=0.58, vmin=0.0, vmax=float(values.max()))
    cmap = plt.get_cmap(cmap_name)
    ax.add_collection(
        PolyCollection(all_rings, facecolors=BACKGROUND_FILL, edgecolors="none", zorder=0)
    )
    ax.add_collection(
        LineCollection(
            all_rings,
            colors=BACKGROUND_LINE,
            linewidths=0.30,
            alpha=0.88,
            zorder=3,
        )
    )
    for code in core_by_code.index:
        edge_color = DETAIL_LINE if code in shelter_detail_codes else MUNICIPALITY_LINE
        edge_width = 1.1 if code in shelter_detail_codes else 0.65
        ax.add_collection(
            PolyCollection(
                rings_by_code[code],
                facecolors=[cmap(norm(float(core_by_code.loc[code, column])))],
                edgecolors=edge_color,
                linewidths=edge_width,
                zorder=5,
            )
        )
    mean_latitude = (extent[2] + extent[3]) / 2
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    # Preserve geographic proportions while allowing the map axes to occupy
    # the same full-width grid cells as the sensitivity panels below.
    ax.set_aspect(1 / np.cos(np.deg2rad(mean_latitude)), adjustable="datalim")
    ax.set_xticks([])
    ax.set_yticks([])
    add_panel_heading(ax, panel_label, heading)
    if panel_label == "a":
        add_north_arrow(ax)
        add_scale_bar(ax, mean_latitude)

    mapper = ScalarMappable(norm=norm, cmap=cmap)
    mapper.set_array([])
    colorbar = plt.colorbar(mapper, cax=color_axis, orientation="horizontal")
    colorbar.locator = MaxNLocator(nbins=5, integer=True)
    colorbar.formatter = FuncFormatter(lambda value, _position: f"{value:,.0f}")
    colorbar.update_ticks()
    colorbar.set_label(colorbar_label, fontsize=8.0, labelpad=1.5)
    colorbar.ax.tick_params(labelsize=7.0, length=2, pad=1)
    colorbar.outline.set_linewidth(0.45)


def draw_sensitivity(
    ax: plt.Axes,
    pivot: pd.DataFrame,
    order: list[str],
    panel_label: str,
    heading: str,
    x_label: str,
    show_y_labels: bool,
) -> None:
    pivot = pivot.loc[order]
    y_positions = np.arange(len(order))
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
    ax.set_xlabel(x_label, fontsize=8.5, labelpad=6)
    ax.set_ylim(len(order) - 0.45, -0.55)
    if show_y_labels:
        ax.set_yticks(y_positions, labels=order, fontsize=8.2)
    else:
        ax.set_yticks(y_positions)
        ax.tick_params(axis="y", labelleft=False)
    add_panel_heading(ax, panel_label, heading)


def main() -> None:
    frame = pd.read_parquet(SOURCE).rename(
        columns={
            "Estimated Female Evacuees": "Municipality Estimated Female Evacuees",
            "Estimated Functional Support Evacuees": (
                "Municipality Estimated Functional Support Evacuees"
            ),
            "Estimated Female Functional Support Evacuees": (
                "Municipality Estimated Female Functional Support Evacuees"
            ),
        }
    )
    required = {
        "Municipality Observation Time",
        "Municipality Code",
        "Municipality",
        "Open Shelter Count",
        "Evacuees",
        "Municipality Evidence Tier",
        "Functional Support Scenario",
        "Municipality Estimated Female Evacuees",
        "Municipality Estimated Functional Support Evacuees",
        "Municipality Estimated Female Functional Support Evacuees",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")
    if len(frame) != 33 or frame["Municipality"].nunique() != 11:
        raise ValueError("Expected 33 municipality-scenario records for 11 municipalities")
    if set(frame["Functional Support Scenario"].astype(str)) != set(SCENARIOS):
        raise ValueError("Unexpected municipality functional-support scenarios")
    core = frame.loc[frame["Functional Support Scenario"].astype(str).eq("Core")].copy()
    if core["Open Shelter Count"].sum() != 81 or core["Evacuees"].sum() != 3585:
        raise ValueError("Common snapshot does not reproduce 81 shelters and 3,585 evacuees")
    if core["Municipality Observation Time"].nunique() != 1:
        raise ValueError("Municipalities do not share one observation time")

    pivot_columns = (
        "Municipality Estimated Functional Support Evacuees",
        "Municipality Estimated Female Functional Support Evacuees",
    )
    pivots = {
        column: frame.pivot(
            index="Municipality",
            columns="Functional Support Scenario",
            values=column,
        ).loc[:, list(SCENARIOS)]
        for column in pivot_columns
    }
    for column, pivot in pivots.items():
        if not ((pivot["Narrow"] <= pivot["Core"]) & (pivot["Core"] <= pivot["Broad"])).all():
            raise ValueError(f"Scenario scope is not monotonic for {column}")
        if (pivot <= 0).any().any():
            raise ValueError(f"Log-scale values must be positive for {column}")
    order = pivots[pivot_columns[0]]["Core"].sort_values(ascending=False).index.tolist()

    boundaries = pd.read_parquet(
        BOUNDARIES, columns=["Municipality Code", "Municipality Name", "Geometry"]
    )
    boundaries["Geometry Object"] = list(from_wkb(boundaries["Geometry"].to_numpy()))
    all_rings: list[np.ndarray] = []
    rings_by_code: dict[str, list[np.ndarray]] = {}
    for _, row in boundaries.iterrows():
        rings = polygon_exteriors(row["Geometry Object"])
        all_rings.extend(rings)
        code = "43100" if str(row["Municipality Name"]) == "熊本市" else str(row["Municipality Code"])
        rings_by_code.setdefault(code, []).extend(rings)
    core["Municipality Code"] = core["Municipality Code"].astype(str)
    core_by_code = core.set_index("Municipality Code")
    missing_codes = set(core_by_code.index).difference(rings_by_code)
    if missing_codes:
        raise KeyError(f"Missing municipal boundaries: {sorted(missing_codes)}")
    shelter_detail_codes = set(
        core.loc[
            core["Municipality"].isin(["Kumamoto City", "Yatsushiro City"]),
            "Municipality Code",
        ]
    )
    extent = shared_extent(all_rings)

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.edgecolor": "#4B5563",
            "axes.linewidth": 0.8,
            "xtick.color": "#3F4854",
            "ytick.color": "#263746",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    fig = plt.figure(figsize=(12.8, 9.3))
    outer = fig.add_gridspec(
        3,
        2,
        height_ratios=(1.0, 0.92, 0.045),
        hspace=0.25,
        wspace=0.18,
    )
    top_left = outer[0, 0].subgridspec(2, 1, height_ratios=(1.0, 0.065), hspace=0.08)
    top_right = outer[0, 1].subgridspec(2, 1, height_ratios=(1.0, 0.065), hspace=0.08)
    map_a = fig.add_subplot(top_left[0])
    color_a = fig.add_subplot(top_left[1])
    map_b = fig.add_subplot(top_right[0])
    color_b = fig.add_subplot(top_right[1])
    forest_c = fig.add_subplot(outer[1, 0])
    forest_d = fig.add_subplot(outer[1, 1])
    legend_axis = fig.add_subplot(outer[2, :])
    legend_axis.set_axis_off()

    draw_map(
        map_a,
        color_a,
        core_by_code,
        rings_by_code,
        all_rings,
        extent,
        shelter_detail_codes,
        "Evacuees",
        "viridis",
        "Observed evacuees",
        "a",
        "Observed municipality demand",
    )
    draw_map(
        map_b,
        color_b,
        core_by_code,
        rings_by_code,
        all_rings,
        extent,
        shelter_detail_codes,
        "Municipality Estimated Functional Support Evacuees",
        "magma",
        "Core estimated functional-support evacuees",
        "b",
        "Core functional-support scenario",
    )
    map_b.legend(
        handles=[
            Line2D([0], [0], color=DETAIL_LINE, lw=2.0, label="Shelter-detail evidence available"),
            Line2D([0], [0], color=MUNICIPALITY_LINE, lw=1.4, label="Municipality totals only"),
        ],
        loc="upper left",
        bbox_to_anchor=(0.01, 0.99),
        frameon=True,
        framealpha=0.9,
        facecolor="white",
        edgecolor="#D0D4D8",
        fontsize=6.7,
        handlelength=1.7,
    )
    draw_sensitivity(
        forest_c,
        pivots[pivot_columns[0]],
        order,
        "c",
        "Functional-support scope sensitivity",
        "Estimated functional-support evacuees (persons, log scale)",
        True,
    )
    draw_sensitivity(
        forest_d,
        pivots[pivot_columns[1]],
        order,
        "d",
        "Female functional-support scope sensitivity",
        "Estimated female functional-support evacuees (persons, log scale)",
        False,
    )
    scenario_handles = [
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
    legend_axis.legend(
        handles=scenario_handles,
        loc="center",
        ncol=3,
        frameon=False,
        fontsize=8.2,
        handletextpad=0.45,
        columnspacing=1.6,
    )
    fig.subplots_adjust(left=0.105, right=0.985, bottom=0.045, top=0.975)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
