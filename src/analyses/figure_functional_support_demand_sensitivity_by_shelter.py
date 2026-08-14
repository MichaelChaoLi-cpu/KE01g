#!/usr/bin/env python3
"""Functional-Support Demand Sensitivity by Shelter.

Plan: Display low, base, and high functional-support demand estimates for every
matched shelter in Kumamoto City and Yatsushiro City.
Framework: Section 5 overlap-scenario sensitivity; Section 6 shelter synthetic
demand; Section 7 complete-sample shelter comparison. Values are scenario
planning estimates, not observed functional-support evacuees.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, MaxNLocator
import numpy as np
import pandas as pd
from shapely import box, from_wkb, union_all


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
    "Figure_functional_support_demand_sensitivity_by_shelter.png"
)

SCENARIOS = ("low", "base", "high")
SCENARIO_STYLE = {
    "low": {"color": "#3B73A1", "marker": "o", "label": "Low"},
    "base": {"color": "#D2644F", "marker": "s", "label": "Base"},
    "high": {"color": "#3C8D76", "marker": "^", "label": "High"},
}
PANELS = (
    ("八代市", "Yatsushiro City", "Y"),
    ("熊本市", "Kumamoto City", "K"),
)
MAP_STYLE = {
    "exact": {"marker": "o", "color": "#2F6F9F", "label": "Exact shelter point"},
    "anchor": {"marker": "^", "color": "#D2644F", "label": "District-anchor fallback"},
    "shared": {"marker": "D", "color": "#7B5AA6", "label": "Co-located shelter codes"},
}
PLACE_LABELS = {
    "五木村": "Itsuki",
    "八代市": "Yatsushiro",
    "合志市": "Koshi",
    "嘉島町": "Kashima",
    "宇土市": "Uto",
    "宇城市": "Uki",
    "山江村": "Yamae",
    "山都町": "Yamato",
    "山鹿市": "Yamaga",
    "御船町": "Mifune",
    "水上村": "Mizukami",
    "氷川町": "Hikawa",
    "熊本市": "Kumamoto",
    "玉名市": "Tamana",
    "玉東町": "Gyokuto",
    "球磨村": "Kuma",
    "甲佐町": "Kosa",
    "益城町": "Mashiki",
    "美里町": "Misato",
    "芦北町": "Ashikita",
    "菊池市": "Kikuchi",
    "菊陽町": "Kikuyo",
}
MAP_PADDING = {
    "八代市": (0.055, 0.045),
    "熊本市": (0.045, 0.040),
}


def english_facility_type(name: str) -> str:
    """Return a concise English class while the shelter number remains the ID."""
    rules = (
        ("コミュニティセンター及び", "Community & Sports Center"),
        ("まちづくりセンター・公民館", "Community Center"),
        ("交流室・公民館", "Community Room"),
        ("アスパル", "Community Center"),
        ("コミュニティセンター", "Community Center"),
        ("老人福祉センター", "Senior Welfare Center"),
        ("保健センター", "Health Center"),
        ("支援学校", "Special Needs School"),
        ("中学校", "Junior High School"),
        ("小学校", "Elementary School"),
        ("アリーナ", "Arena"),
        ("文化センター", "Cultural Center"),
    )
    for source_text, english_text in rules:
        if source_text in name:
            return english_text
    raise ValueError(f"No English facility-class rule for shelter: {name!r}")


def add_panel_heading(ax: plt.Axes, label: str, municipality: str) -> None:
    ax.text(
        -0.035,
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
        0.030,
        1.035,
        municipality,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9.5,
        fontweight="bold",
        color="#263746",
    )


def polygon_exteriors(geometry) -> list[np.ndarray]:
    if geometry is None or geometry.is_empty:
        return []
    polygons = geometry.geoms if geometry.geom_type == "MultiPolygon" else (geometry,)
    return [np.asarray(polygon.exterior.coords) for polygon in polygons]


def load_boundaries() -> pd.DataFrame:
    boundaries = pd.read_parquet(
        BOUNDARIES,
        columns=["Municipality Name", "Ward Name", "Geometry"],
    )
    boundaries["Geometry Object"] = list(from_wkb(boundaries["Geometry"].to_numpy()))
    for municipality, _display, _prefix in PANELS:
        selected = boundaries.loc[boundaries["Municipality Name"].eq(municipality)]
        if selected.empty:
            raise KeyError(f"Missing municipality boundary: {municipality}")
    return boundaries


def grouped_map_points(points: pd.DataFrame, prefix: str) -> pd.DataFrame:
    def codes(series: pd.Series) -> str:
        return "/".join(f"{prefix}{int(value):02d}" for value in sorted(series))

    grouped = (
        points.groupby(["Longitude", "Latitude"], as_index=False)
        .agg(
            Shelter_Codes=("Shelter Number", codes),
            Shelter_Count=("Shelter Number", "size"),
            Exact_Count=(
                "Location Resolution",
                lambda values: int((values == "exact shelter master match").sum()),
            ),
        )
        .sort_values(["Latitude", "Longitude"])
        .reset_index(drop=True)
    )
    grouped["Map Class"] = np.select(
        [grouped["Shelter_Count"].gt(1), grouped["Exact_Count"].eq(1)],
        ["shared", "exact"],
        default="anchor",
    )
    return grouped


def draw_locator_map(
    ax: plt.Axes,
    points: pd.DataFrame,
    boundaries: pd.DataFrame,
    municipality: str,
    prefix: str,
) -> None:
    grouped = grouped_map_points(points, prefix)
    target_geometries = boundaries.loc[
        boundaries["Municipality Name"].eq(municipality), "Geometry Object"
    ].to_list()
    target_geometry = union_all(target_geometries)
    x_min, y_min, x_max, y_max = target_geometry.bounds
    x_pad, y_pad = MAP_PADDING[municipality]
    x_min, x_max = x_min - x_pad, x_max + x_pad
    y_min, y_max = y_min - y_pad, y_max + y_pad
    mean_latitude = (y_min + y_max) / 2
    geographic_aspect = 1 / np.cos(np.deg2rad(mean_latitude))
    x_span = x_max - x_min
    y_span = y_max - y_min
    if x_span > geographic_aspect * y_span:
        y_mid = (y_min + y_max) / 2
        y_span = x_span / geographic_aspect
        y_min, y_max = y_mid - y_span / 2, y_mid + y_span / 2
    else:
        x_mid = (x_min + x_max) / 2
        x_span = geographic_aspect * y_span
        x_min, x_max = x_mid - x_span / 2, x_mid + x_span / 2
    extent = (x_min, x_max, y_min, y_max)
    window = box(extent[0], extent[2], extent[1], extent[3])

    context = boundaries.loc[
        boundaries["Geometry Object"].map(lambda geometry: geometry.intersects(window))
    ].copy()
    context_rings = [
        ring
        for geometry in context["Geometry Object"]
        for ring in polygon_exteriors(geometry)
    ]
    target_rings = [
        ring for geometry in target_geometries for ring in polygon_exteriors(geometry)
    ]
    ax.add_collection(
        PolyCollection(
            context_rings,
            facecolors="#F1F2F1",
            edgecolors="none",
            zorder=0,
        )
    )
    ax.add_collection(
        LineCollection(
            context_rings,
            colors="#A9B0B5",
            linewidths=0.48,
            zorder=1,
        )
    )
    ax.add_collection(
        PolyCollection(
            target_rings,
            facecolors="#DCEAF2",
            edgecolors="none",
            zorder=2,
        )
    )
    ax.add_collection(
        LineCollection(
            target_rings,
            colors="#617887",
            linewidths=0.75,
            zorder=3,
        )
    )
    for map_class, style in MAP_STYLE.items():
        subset = grouped.loc[grouped["Map Class"].eq(map_class)]
        ax.scatter(
            subset["Longitude"],
            subset["Latitude"],
            s=40 if map_class == "shared" else 31,
            marker=style["marker"],
            color=style["color"],
            edgecolors="white",
            linewidths=0.5,
            zorder=4,
        )

    # Split labels into ordered left/right columns. Preserving latitude order
    # within each column prevents leader lines on the same side from crossing.
    ordered = grouped.sort_values(["Longitude", "Latitude"]).reset_index(drop=True)
    split_at = (len(ordered) + 1) // 2
    label_sides = (
        (ordered.iloc[:split_at], extent[0] + 0.018 * x_span, "left"),
        (ordered.iloc[split_at:], extent[1] - 0.018 * x_span, "right"),
    )
    for side, label_x, horizontal_alignment in label_sides:
        side = side.sort_values(["Latitude", "Longitude"]).reset_index(drop=True)
        if side.empty:
            continue
        label_y_positions = np.linspace(
            extent[2] + 0.13 * y_span,
            extent[3] - 0.045 * y_span,
            len(side),
        )
        for (_, row), label_y in zip(side.iterrows(), label_y_positions, strict=True):
            ax.annotate(
                row["Shelter_Codes"],
                xy=(row["Longitude"], row["Latitude"]),
                xytext=(label_x, label_y),
                textcoords="data",
                ha=horizontal_alignment,
                va="center",
                fontsize=6.25,
                color="#263746",
                bbox={
                    "boxstyle": "round,pad=0.11",
                    "fc": "white",
                    "ec": "#71818C",
                    "linewidth": 0.48,
                    "alpha": 0.96,
                },
                arrowprops={
                    "arrowstyle": "-",
                    "color": "#7D8991",
                    "linewidth": 0.48,
                    "shrinkA": 2.0,
                    "shrinkB": 1.5,
                },
                zorder=6,
            )

    neighbour_names: set[str] = set()
    for name, municipality_rows in boundaries.groupby("Municipality Name", observed=True):
        name = str(name)
        if name == municipality:
            neighbour_names.add(name)
            continue
        neighbour_geometry = union_all(municipality_rows["Geometry Object"].to_list())
        if target_geometry.distance(neighbour_geometry) < 0.002:
            neighbour_names.add(name)

    for name in sorted(neighbour_names):
        municipality_geometry = union_all(
            boundaries.loc[
                boundaries["Municipality Name"].eq(name), "Geometry Object"
            ].to_list()
        )
        visible_geometry = municipality_geometry.intersection(window)
        if visible_geometry.is_empty or name not in PLACE_LABELS:
            continue
        point = visible_geometry.representative_point()
        is_target = name == municipality
        ax.text(
            point.x,
            point.y,
            PLACE_LABELS[name],
            ha="center",
            va="center",
            fontsize=7.2 if is_target else 6.2,
            fontweight="bold" if is_target else "normal",
            color="#2F5267" if is_target else "#65717A",
            bbox={
                "boxstyle": "round,pad=0.12",
                "fc": "white",
                "ec": "none",
                "alpha": 0.70,
            },
            zorder=4,
        )

    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    ax.set_box_aspect(1.0)
    ax.xaxis.set_major_locator(MaxNLocator(nbins=5))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _pos: f"{value:.2f}°E"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _pos: f"{value:.2f}°N"))
    ax.tick_params(axis="both", labelsize=6.8, length=2.5, pad=2)
    ax.grid(color="#FFFFFF", linewidth=0.65, alpha=0.95, zorder=2)
    ax.set_xlabel("Longitude", fontsize=7.5, labelpad=4)
    ax.set_ylabel("Latitude", fontsize=7.5, labelpad=4)


def map_legend_handles() -> list[Line2D]:
    return [
        Line2D(
            [0],
            [0],
            marker=style["marker"],
            color="none",
            markerfacecolor=style["color"],
            markeredgecolor="white",
            markeredgewidth=0.5,
            markersize=6.5,
            label=style["label"],
        )
        for style in MAP_STYLE.values()
    ]


def main() -> None:
    frame = pd.read_parquet(SOURCE)
    required = {
        "Municipality",
        "Shelter Number",
        "Shelter Name",
        "Latitude",
        "Longitude",
        "Location Resolution",
        "Scenario",
        "Estimated Functional Support Evacuees",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")
    if len(frame) != 159 or frame["Shelter Name"].nunique() != 53:
        raise ValueError("Expected 159 records for 53 shelters and three scenarios")
    if set(frame["Scenario"].astype(str)) != set(SCENARIOS):
        raise ValueError("Expected low, base, and high scenarios")
    if frame[list(required)].isna().any().any():
        raise ValueError("Required shelter sensitivity fields contain missing values")
    if (frame["Estimated Functional Support Evacuees"] < 0).any():
        raise ValueError("Functional-support estimates cannot be negative")

    base_points = frame.loc[frame["Scenario"].astype("string").eq("base")].copy()
    if len(base_points) != 53 or base_points[["Latitude", "Longitude"]].isna().any().any():
        raise ValueError("Expected 53 base-scenario shelters with complete coordinates")
    boundaries = load_boundaries()

    municipality_counts = frame.groupby(["Municipality", "Scenario"]).size().unstack()
    expected_counts = {"八代市": 38, "熊本市": 15}
    for municipality, expected in expected_counts.items():
        if municipality not in municipality_counts.index:
            raise ValueError(f"Missing municipality: {municipality}")
        if not (municipality_counts.loc[municipality] == expected).all():
            raise ValueError(f"Unexpected shelter count for {municipality}")

    pivots: dict[str, pd.DataFrame] = {}
    for municipality, _display, _prefix in PANELS:
        pivot = frame.loc[frame["Municipality"].eq(municipality)].pivot(
            index=["Shelter Number", "Shelter Name"],
            columns="Scenario",
            values="Estimated Functional Support Evacuees",
        )
        pivot = pivot.loc[:, list(SCENARIOS)].sort_values(
            ["base", "high", "Shelter Number"],
            ascending=[False, False, True],
        )
        if not ((pivot["low"] <= pivot["base"]) & (pivot["base"] <= pivot["high"])).all():
            raise ValueError(f"Scenario sensitivity is not monotonic for {municipality}")
        pivots[municipality] = pivot

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
    fig = plt.figure(figsize=(14.2, 17.0))
    grid = fig.add_gridspec(
        2,
        2,
        height_ratios=(0.56, 1.0),
        width_ratios=(1.0, 1.0),
        hspace=0.105,
        wspace=0.30,
    )
    map_axes = [fig.add_subplot(grid[0, index]) for index in range(2)]
    axes = [fig.add_subplot(grid[1, index]) for index in range(2)]
    fig.subplots_adjust(left=0.105, right=0.985, bottom=0.045, top=0.975)

    for panel_index, (ax, (municipality, display, prefix)) in enumerate(
        zip(map_axes, PANELS, strict=True)
    ):
        points = base_points.loc[base_points["Municipality"].eq(municipality)]
        draw_locator_map(ax, points, boundaries, municipality, prefix)
        add_panel_heading(ax, chr(ord("a") + panel_index), display)
    map_axes[0].legend(
        handles=map_legend_handles(),
        loc="lower center",
        ncol=3,
        frameon=True,
        facecolor="white",
        edgecolor="#D0D3D6",
        framealpha=0.9,
        fontsize=6.7,
        borderpad=0.35,
        handletextpad=0.30,
        columnspacing=0.75,
    )

    for panel_index, (ax, (municipality, display, prefix)) in enumerate(
        zip(axes, PANELS, strict=True)
    ):
        pivot = pivots[municipality]
        y_positions = np.arange(len(pivot))
        for row in range(len(pivot)):
            if row % 2 == 0:
                ax.axhspan(row - 0.5, row + 0.5, color="#F6F7F8", zorder=0)
        ax.hlines(
            y_positions,
            pivot["low"],
            pivot["high"],
            color="#A7ADB4",
            linewidth=1.25,
            zorder=2,
        )
        for scenario in SCENARIOS:
            style = SCENARIO_STYLE[scenario]
            ax.scatter(
                pivot[scenario],
                y_positions,
                s=31 if scenario == "base" else 27,
                color=style["color"],
                marker=style["marker"],
                edgecolor="white",
                linewidth=0.5,
                zorder=4,
            )

        labels = [
            f"{prefix}{int(number):02d}  {english_facility_type(str(name))}"
            for number, name in pivot.index.to_list()
        ]
        ax.set_yticks(y_positions, labels=labels, fontsize=7.2)
        ax.tick_params(axis="y", length=0, pad=5)
        ax.tick_params(axis="x", labelsize=8.0, length=2.5, pad=2)
        ax.set_ylim(len(pivot) - 0.45, -0.55)
        ax.set_xlim(left=-0.02 * max(float(pivot["high"].max()), 1.0))
        ax.xaxis.set_major_locator(MaxNLocator(nbins=6, integer=False, min_n_ticks=4))
        ax.grid(axis="x", color="#D7DADF", linewidth=0.5, zorder=1)
        ax.set_xlabel(
            "Estimated functional-support evacuees (persons)",
            fontsize=9.0,
            labelpad=7,
        )
        add_panel_heading(ax, chr(ord("c") + panel_index), display)

    legend_handles = [
        Line2D(
            [0],
            [0],
            marker=SCENARIO_STYLE[scenario]["marker"],
            color="none",
            markerfacecolor=SCENARIO_STYLE[scenario]["color"],
            markeredgecolor="white",
            markeredgewidth=0.5,
            markersize=7,
            label=SCENARIO_STYLE[scenario]["label"],
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
        columnspacing=1.7,
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
