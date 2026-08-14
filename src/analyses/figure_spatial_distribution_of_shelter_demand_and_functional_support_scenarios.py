#!/usr/bin/env python3
"""Spatial Distribution of Shelter Demand and Functional-Support Scenarios.

Plan: Map observed shelter occupancy and base-scenario functional-support
demand across the complete municipal jurisdictions of Kumamoto City and
Yatsushiro City.
Framework: Section 5 spatial and synthetic-demand contrast; Section 6 synthetic
shelter demand; Section 7 matched-city spatial mapping. Both panels use the
same extent and scale. Scenario demand is not observed disability composition.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.colors import PowerNorm
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter, MultipleLocator
import numpy as np
import pandas as pd
from shapely import from_wkb


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/processed/shelter_equity_scenarios_preprocessed.parquet"
BOUNDARIES = (
    ROOT
    / "data/exp/scenario-planning/"
    "kumamoto_prefecture_administrative_areas_2025_preprocessed.parquet"
)
OUTPUT = (
    ROOT
    / "data/results/figures/"
    "Figure_spatial_distribution_of_shelter_demand_and_functional_support_scenarios.png"
)

STUDY_MUNICIPALITIES = {"熊本市", "八代市"}
PANELS = (
    (
        "Evacuees",
        "viridis",
        "Observed evacuees (marker area and color)",
        [0, 50, 100, 200, 300],
    ),
    (
        "Estimated Functional Support Evacuees",
        "magma",
        "Base-scenario estimated functional-support evacuees (marker area and color)",
        [0, 5, 10, 20, 30],
    ),
)
RESOLUTION_STYLE = {
    "exact shelter master match": ("o", "Exact shelter point"),
    "district anchor fallback": ("^", "District-anchor fallback"),
}
BOUNDARY_FILL = "#f2f2ef"
BOUNDARY_LINE = "#707070"


def polygon_exteriors(geometries: np.ndarray) -> list[np.ndarray]:
    exteriors: list[np.ndarray] = []
    for geometry in geometries:
        if geometry is None or geometry.is_empty:
            continue
        parts = geometry.geoms if geometry.geom_type == "MultiPolygon" else (geometry,)
        for part in parts:
            exteriors.append(np.asarray(part.exterior.coords))
    return exteriors


def load_boundaries() -> tuple[list[np.ndarray], list[np.ndarray]]:
    frame = pd.read_parquet(BOUNDARIES, columns=["Municipality Name", "Geometry"])
    geometries = from_wkb(frame["Geometry"].to_numpy())
    target = frame["Municipality Name"].astype("string").isin(STUDY_MUNICIPALITIES).to_numpy()
    absent = STUDY_MUNICIPALITIES.difference(
        frame.loc[target, "Municipality Name"].astype(str).unique()
    )
    if absent:
        raise KeyError(f"Missing study-municipality boundaries: {sorted(absent)}")
    return polygon_exteriors(geometries), polygon_exteriors(geometries[target])


def shared_extent(boundaries: list[np.ndarray]) -> tuple[float, float, float, float]:
    coordinates = np.vstack(boundaries)
    x_min, y_min = coordinates.min(axis=0)
    x_max, y_max = coordinates.max(axis=0)
    x_padding = 0.018 * (x_max - x_min)
    y_padding = 0.018 * (y_max - y_min)
    return x_min - x_padding, x_max + x_padding, y_min - y_padding, y_max + y_padding


def degree_formatter(value: float, _position: int) -> str:
    return f"{value:.2f}°"


def marker_area(values: pd.Series, maximum: float) -> np.ndarray:
    scaled = np.clip(values.to_numpy(dtype=float) / max(maximum, 1e-9), 0, 1)
    return 16.0 + 170.0 * np.sqrt(scaled)


def add_north_arrow(ax: plt.Axes) -> None:
    ax.annotate(
        "N",
        xy=(0.95, 0.96),
        xytext=(0.95, 0.87),
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
    x_start = x_min + 0.06 * (x_max - x_min)
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


def main() -> None:
    df = pd.read_parquet(SOURCE)
    base = df.loc[df["Scenario"].astype("string").eq("base")].copy()
    required = {
        "Municipality",
        "Latitude",
        "Longitude",
        "Evacuees",
        "Estimated Functional Support Evacuees",
        "Location Resolution",
    }
    missing = required.difference(base.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")
    if len(base) != 53 or base[["Latitude", "Longitude"]].isna().any().any():
        raise ValueError("Expected 53 base-scenario shelters with complete coordinates")

    prefecture_rings, study_rings = load_boundaries()
    extent = shared_extent(prefecture_rings)
    mean_latitude = (extent[2] + extent[3]) / 2

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.edgecolor": "#374151",
            "axes.linewidth": 0.85,
            "xtick.color": "#4a4a4a",
            "ytick.color": "#4a4a4a",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    fig = plt.figure(figsize=(12.0, 6.8), constrained_layout=True)
    grid = fig.add_gridspec(
        3,
        2,
        height_ratios=(1.0, 0.045, 0.050),
        hspace=0.045,
        wspace=0.075,
    )
    axes = [fig.add_subplot(grid[0, index]) for index in range(2)]
    colorbar_axes = [fig.add_subplot(grid[1, index]) for index in range(2)]
    legend_axis = fig.add_subplot(grid[2, :])
    legend_axis.set_axis_off()

    for index, (ax, color_axis, (column, cmap, colorbar_label, ticks)) in enumerate(
        zip(axes, colorbar_axes, PANELS, strict=True)
    ):
        values = base[column].astype(float)
        maximum = float(values.max())
        norm = PowerNorm(gamma=0.62, vmin=0.0, vmax=maximum)
        ax.add_collection(
            PolyCollection(
                prefecture_rings,
                facecolors=BOUNDARY_FILL,
                edgecolors="none",
                zorder=0,
            )
        )
        ax.add_collection(
            LineCollection(
                prefecture_rings,
                colors="#a0a0a0",
                linewidths=0.32,
                alpha=0.82,
                zorder=3,
            )
        )
        ax.add_collection(
            PolyCollection(
                study_rings,
                facecolors="#dce6ec",
                edgecolors="none",
                alpha=0.88,
                zorder=2,
            )
        )
        ax.add_collection(
            LineCollection(
                study_rings,
                colors=BOUNDARY_LINE,
                linewidths=0.72,
                alpha=0.95,
                zorder=4,
            )
        )

        plotted = None
        for resolution, (marker, _) in RESOLUTION_STYLE.items():
            part = base.loc[
                base["Location Resolution"].astype("string").eq(resolution)
            ]
            plotted = ax.scatter(
                part["Longitude"],
                part["Latitude"],
                s=marker_area(part[column].astype(float), maximum),
                c=part[column].astype(float),
                cmap=cmap,
                norm=norm,
                marker=marker,
                edgecolors="white",
                linewidths=0.5,
                alpha=0.92,
                zorder=7,
            )
        if plotted is None:
            raise ValueError("No shelter points were plotted")

        ax.set_xlim(extent[0], extent[1])
        ax.set_ylim(extent[2], extent[3])
        ax.set_aspect(1 / np.cos(np.deg2rad(mean_latitude)))
        ax.xaxis.set_major_locator(MultipleLocator(0.25))
        ax.yaxis.set_major_locator(MultipleLocator(0.20))
        ax.xaxis.set_major_formatter(FuncFormatter(degree_formatter))
        ax.yaxis.set_major_formatter(FuncFormatter(degree_formatter))
        ax.tick_params(labelsize=7.4, length=2.5, pad=2)
        ax.grid(color="#d6d6d6", linewidth=0.35, linestyle=(0, (2, 3)), zorder=1)

        add_panel_label(ax, chr(ord("a") + index))
        if index == 0:
            add_north_arrow(ax)
            add_scale_bar(ax, mean_latitude)

        colorbar = fig.colorbar(plotted, cax=color_axis, orientation="horizontal")
        colorbar.set_ticks(ticks)
        colorbar.set_label(colorbar_label, fontsize=8.0, labelpad=2)
        colorbar.ax.tick_params(labelsize=7.0, length=2, pad=1)
        colorbar.outline.set_linewidth(0.45)

    legend_handles = [
        Line2D(
            [0],
            [0],
            marker=marker,
            linestyle="none",
            markerfacecolor="#64748b",
            markeredgecolor="white",
            markeredgewidth=0.5,
            markersize=6.5,
            label=display,
        )
        for marker, display in RESOLUTION_STYLE.values()
    ]
    legend_handles.append(
        Patch(
            facecolor="#dce6ec",
            edgecolor=BOUNDARY_LINE,
            linewidth=0.7,
            label="Study municipalities: Kumamoto City and Yatsushiro City (53 open shelters)",
        )
    )
    legend_axis.legend(
        handles=legend_handles,
        loc="center",
        ncol=3,
        frameon=False,
        fontsize=8.0,
        handletextpad=0.5,
        columnspacing=1.5,
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
