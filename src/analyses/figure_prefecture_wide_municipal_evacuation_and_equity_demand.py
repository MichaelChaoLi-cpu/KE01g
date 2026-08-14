#!/usr/bin/env python3
"""Prefecture-Wide Municipal Evacuation and Equity Demand.

Plan: Map observed evacuees, scenario-estimated female evacuees, and Core
functional-support demand across all municipalities reporting open shelters.
Framework: Section 5 municipality screening and evidence separation; Section 6
municipality demand equations; Section 7 common-snapshot boundary mapping.
Scenario panels are planning proxies, not observed subgroup composition.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.colors import PowerNorm
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, MaxNLocator
import numpy as np
import pandas as pd
from shapely import from_wkb
from shapely.ops import unary_union


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
    "Figure_prefecture_wide_municipal_evacuation_and_equity_demand.png"
)

PANELS = (
    (
        "Evacuees",
        "viridis",
        "Observed evacuees",
    ),
    (
        "Municipality Estimated Female Evacuees",
        "magma",
        "Estimated female evacuees",
    ),
    (
        "Municipality Estimated Functional Support Evacuees",
        "cividis",
        "Core estimated functional-support evacuees",
    ),
)
BACKGROUND_FILL = "#f2f2ef"
BACKGROUND_LINE = "#a2a2a2"
MUNICIPALITY_LINE = "#767676"
DETAIL_LINE = "#005b96"


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


def add_panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.045,
        1.02,
        label,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=12,
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
    ax.plot(
        [x_start, x_start, x_start + length_degrees, x_start + length_degrees],
        [y_start - 0.006, y_start + 0.006, y_start - 0.006, y_start + 0.006],
        color="#252525",
        linewidth=0.8,
        zorder=12,
    )
    ax.text(
        x_start + length_degrees / 2,
        y_start + 0.011,
        f"{length_km:g} km",
        ha="center",
        va="bottom",
        fontsize=7.2,
        color="#252525",
        zorder=12,
    )


def main() -> None:
    scenarios = pd.read_parquet(SOURCE).copy()
    # The municipality dataset stores the article-facing municipality concepts
    # under shorter source columns; alias them explicitly to the Section 4 names.
    scenarios = scenarios.rename(
        columns={
            "Estimated Female Evacuees": "Municipality Estimated Female Evacuees",
            "Estimated Functional Support Evacuees": (
                "Municipality Estimated Functional Support Evacuees"
            ),
        }
    )
    required = {
        "Municipality Observation Time",
        "Municipality Code",
        "Municipality (Japanese)",
        "Municipality",
        "Open Shelter Count",
        "Evacuees",
        "Municipality Evidence Tier",
        "Functional Support Scenario",
        "Municipality Estimated Female Evacuees",
        "Municipality Estimated Functional Support Evacuees",
    }
    missing = required.difference(scenarios.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")

    core = scenarios.loc[
        scenarios["Functional Support Scenario"].astype("string").eq("Core")
    ].copy()
    if len(core) != 11 or core["Municipality Code"].nunique() != 11:
        raise ValueError("Expected one Core record for each of 11 municipalities")
    if core["Open Shelter Count"].sum() != 81 or core["Evacuees"].sum() != 3585:
        raise ValueError("Common snapshot does not reproduce 81 shelters and 3,585 evacuees")
    if core["Municipality Observation Time"].nunique() != 1:
        raise ValueError("Municipalities do not share one observation time")

    boundaries = pd.read_parquet(
        BOUNDARIES,
        columns=["Municipality Code", "Municipality Name", "Geometry"],
    )
    boundaries["Geometry Object"] = list(from_wkb(boundaries["Geometry"].to_numpy()))
    all_rings: list[np.ndarray] = []
    rings_by_code: dict[str, list[np.ndarray]] = {}
    for row in boundaries.itertuples(index=False):
        code = str(row[0])
        municipality_name = str(row[1])
        geometry = row[3]
        rings = polygon_exteriors(geometry)
        all_rings.extend(rings)
        # The analysis dataset uses the designated-city code 43100, whereas
        # the boundary source stores Kumamoto City's five wards separately.
        # Retain the ward outlines while assigning every ward the city value.
        analysis_code = "43100" if municipality_name == "熊本市" else code
        rings_by_code.setdefault(analysis_code, []).extend(rings)

    boundary_codes = set(rings_by_code)
    missing_codes = set(core["Municipality Code"].astype(str)).difference(boundary_codes)
    if missing_codes:
        raise KeyError(f"Missing municipal boundaries: {sorted(missing_codes)}")

    core_by_code = core.assign(
        **{"Municipality Code": core["Municipality Code"].astype(str)}
    ).set_index("Municipality Code")
    affected_codes = set(core_by_code.index)
    # Every colored value comes from the common municipality-total snapshot.
    # Blue outlines only flag the two cities with separate Tier 2 shelter-detail
    # records; they do not change the evidence level of the mapped values.
    shelter_detail_codes = set(
        core.loc[
            core["Municipality"].isin(["Kumamoto City", "Yatsushiro City"]),
            "Municipality Code",
        ].astype(str)
    )

    extent = shared_extent(all_rings)
    mean_latitude = (extent[2] + extent[3]) / 2

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.edgecolor": "#374151",
            "axes.linewidth": 0.8,
            "xtick.color": "#4a4a4a",
            "ytick.color": "#4a4a4a",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    fig = plt.figure(figsize=(13.8, 6.25), constrained_layout=True)
    grid = fig.add_gridspec(
        3,
        3,
        height_ratios=(1.0, 0.048, 0.047),
        hspace=0.035,
        wspace=0.065,
    )
    axes = [fig.add_subplot(grid[0, i]) for i in range(3)]
    color_axes = [fig.add_subplot(grid[1, i]) for i in range(3)]
    legend_axis = fig.add_subplot(grid[2, :])
    legend_axis.set_axis_off()

    for panel_index, (ax, color_axis, (column, cmap_name, colorbar_label)) in enumerate(
        zip(axes, color_axes, PANELS, strict=True)
    ):
        values = core_by_code[column].astype(float)
        maximum = float(values.max())
        norm = PowerNorm(gamma=0.58, vmin=0.0, vmax=maximum)
        cmap = plt.get_cmap(cmap_name)

        ax.add_collection(
            PolyCollection(
                all_rings,
                facecolors=BACKGROUND_FILL,
                edgecolors="none",
                zorder=0,
            )
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
        for code in affected_codes:
            value = float(core_by_code.loc[code, column])
            edge_color = DETAIL_LINE if code in shelter_detail_codes else MUNICIPALITY_LINE
            edge_width = 1.1 if code in shelter_detail_codes else 0.65
            ax.add_collection(
                PolyCollection(
                    rings_by_code[code],
                    facecolors=[cmap(norm(value))],
                    edgecolors=edge_color,
                    linewidths=edge_width,
                    zorder=5,
                )
            )

        ax.set_xlim(extent[0], extent[1])
        ax.set_ylim(extent[2], extent[3])
        ax.set_aspect(1 / np.cos(np.deg2rad(mean_latitude)))
        ax.set_xticks([])
        ax.set_yticks([])
        add_panel_label(ax, chr(ord("a") + panel_index))
        if panel_index == 0:
            add_north_arrow(ax)
            add_scale_bar(ax, mean_latitude)

        mapper = ScalarMappable(norm=norm, cmap=cmap)
        mapper.set_array([])
        colorbar = fig.colorbar(mapper, cax=color_axis, orientation="horizontal")
        colorbar.locator = MaxNLocator(nbins=5, integer=True)
        colorbar.formatter = FuncFormatter(lambda value, _position: f"{value:,.0f}")
        colorbar.update_ticks()
        colorbar.set_label(colorbar_label, fontsize=8.0, labelpad=1.5)
        colorbar.ax.tick_params(labelsize=7.0, length=2, pad=1)
        colorbar.outline.set_linewidth(0.45)

    legend_axis.legend(
        handles=[
            Line2D(
                [0],
                [0],
                color=DETAIL_LINE,
                linewidth=2.0,
                label="Separate shelter-detail records available (mapped values remain municipal totals)",
            ),
            Line2D(
                [0],
                [0],
                color=MUNICIPALITY_LINE,
                linewidth=1.4,
                label="Municipality-total evidence only",
            ),
        ],
        loc="center",
        ncol=2,
        frameon=False,
        fontsize=8.0,
        handlelength=2.5,
        columnspacing=2.4,
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
