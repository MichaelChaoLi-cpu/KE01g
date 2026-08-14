#!/usr/bin/env python3
"""Provisional Emergency Toilet Rebalancing Plan.

Plan: Map the current Yatsushiro temporary-toilet-only screening imbalance and
the priority-constrained nearest-donor movements under full reported-surplus
mobility.
Framework: Section 5 conditional mitigation contrast; Section 6 donor capacity
D, integer transfer x, post-transfer inventory, and residual shortfall U;
Section 7 conditional Yatsushiro rebalancing workflow. Transfer lines are a
best-case planning sensitivity, not a verified dispatch order.
"""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch
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
    "Figure_provisional_emergency_toilet_rebalancing_plan.png"
)

TARGET_MUNICIPALITY = "八代市"
PLACE_LABELS = {
    "五木村": "Itsuki",
    "八代市": "Yatsushiro",
    "宇土市": "Uto",
    "宇城市": "Uki",
    "山江村": "Yamae",
    "山都町": "Yamato",
    "氷川町": "Hikawa",
    "球磨村": "Kuma",
    "美里町": "Misato",
    "芦北町": "Ashikita",
}

SHORTFALL_COLOR = "#C65345"
SURPLUS_COLOR = "#3C8D76"
BALANCED_COLOR = "#A7AFB5"
RESOLVED_COLOR = SHORTFALL_COLOR
TRANSFER_COLOR = "#4F7891"
INCREASE_LABEL_FACE = "#F4D0CA"
DECREASE_LABEL_FACE = "#CDE2D7"


def add_panel_heading(ax: plt.Axes, label: str, heading: str) -> None:
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
        0.015,
        1.035,
        heading,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9.4,
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
    if not boundaries["Municipality Name"].eq(TARGET_MUNICIPALITY).any():
        raise KeyError("Yatsushiro municipal boundary is missing")
    return boundaries


def map_geometry(boundaries: pd.DataFrame) -> tuple[object, tuple[float, float, float, float]]:
    target_geometries = boundaries.loc[
        boundaries["Municipality Name"].eq(TARGET_MUNICIPALITY), "Geometry Object"
    ].to_list()
    target_geometry = union_all(target_geometries)
    x_min, y_min, x_max, y_max = target_geometry.bounds
    x_min, x_max = x_min - 0.055, x_max + 0.045
    y_min, y_max = y_min - 0.045, y_max + 0.045
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
    return target_geometry, (x_min, x_max, y_min, y_max)


def draw_base_map(
    ax: plt.Axes,
    boundaries: pd.DataFrame,
    target_geometry,
    extent: tuple[float, float, float, float],
) -> None:
    window = box(extent[0], extent[2], extent[1], extent[3])
    context = boundaries.loc[
        boundaries["Geometry Object"].map(lambda geometry: geometry.intersects(window))
    ].copy()
    context_rings = [
        ring
        for geometry in context["Geometry Object"]
        for ring in polygon_exteriors(geometry)
    ]
    target_geometries = boundaries.loc[
        boundaries["Municipality Name"].eq(TARGET_MUNICIPALITY), "Geometry Object"
    ].to_list()
    target_rings = [
        ring for geometry in target_geometries for ring in polygon_exteriors(geometry)
    ]
    ax.add_collection(
        PolyCollection(context_rings, facecolors="#F1F2F1", edgecolors="none", zorder=0)
    )
    ax.add_collection(
        LineCollection(context_rings, colors="#A9B0B5", linewidths=0.48, zorder=1)
    )
    ax.add_collection(
        PolyCollection(target_rings, facecolors="#DCEAF2", edgecolors="none", zorder=2)
    )
    ax.add_collection(
        LineCollection(target_rings, colors="#617887", linewidths=0.78, zorder=3)
    )

    neighbour_names: set[str] = set()
    for name, municipality_rows in boundaries.groupby("Municipality Name", observed=True):
        name = str(name)
        municipality_geometry = union_all(municipality_rows["Geometry Object"].to_list())
        if name == TARGET_MUNICIPALITY or target_geometry.distance(municipality_geometry) < 0.002:
            neighbour_names.add(name)
    for name in sorted(neighbour_names):
        if name not in PLACE_LABELS:
            continue
        municipality_geometry = union_all(
            boundaries.loc[
                boundaries["Municipality Name"].eq(name), "Geometry Object"
            ].to_list()
        )
        visible_geometry = municipality_geometry.intersection(window)
        if visible_geometry.is_empty:
            continue
        point = visible_geometry.representative_point()
        is_target = name == TARGET_MUNICIPALITY
        ax.text(
            point.x,
            point.y,
            PLACE_LABELS[name],
            ha="center",
            va="center",
            fontsize=7.2 if is_target else 6.2,
            fontweight="bold" if is_target else "normal",
            color="#2F5267" if is_target else "#65717A",
            bbox={"boxstyle": "round,pad=0.12", "fc": "white", "ec": "none", "alpha": 0.72},
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


def haversine_km(row_a: pd.Series, row_b: pd.Series) -> float:
    lat1, lon1, lat2, lon2 = map(
        radians,
        [row_a["Latitude"], row_a["Longitude"], row_b["Latitude"], row_b["Longitude"]],
    )
    value = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * asin(sqrt(value))


def construct_screen(frame: pd.DataFrame) -> pd.DataFrame:
    screen = frame.copy()
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
        raise ValueError("Unrecognized Yatsushiro water-status value")
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


def full_mobility_flows(screen: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    capacities = screen["Reported Surplus"].astype(int).to_dict()
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
    records: list[dict[str, float | int]] = []
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
            records.append(
                {
                    "Donor Index": int(donor_index),
                    "Recipient Index": int(recipient_index),
                    "Units": int(quantity),
                    "Distance km": float(distance),
                }
            )
    flows = pd.DataFrame.from_records(records)
    if flows.empty:
        flows = pd.DataFrame(columns=["Donor Index", "Recipient Index", "Units", "Distance km"])
    outflow = flows.groupby("Donor Index")["Units"].sum() if not flows.empty else pd.Series(dtype=float)
    inflow = flows.groupby("Recipient Index")["Units"].sum() if not flows.empty else pd.Series(dtype=float)
    post = screen.copy()
    post["Transfer Out"] = post.index.to_series().map(outflow).fillna(0).astype(int)
    post["Transfer In"] = post.index.to_series().map(inflow).fillna(0).astype(int)
    post["Post-Transfer Inventory"] = (
        post["Temporary Toilets Installed"] + post["Transfer In"] - post["Transfer Out"]
    ).astype(int)
    post["Residual Shortfall"] = (
        post["Prolonged Requirement"] - post["Post-Transfer Inventory"]
    ).clip(lower=0).astype(int)
    return flows, post


def label_column_points(
    ax: plt.Axes,
    rows: pd.DataFrame,
    extent: tuple[float, float, float, float],
    label_column: str,
) -> None:
    if rows.empty:
        return
    x_span = extent[1] - extent[0]
    y_span = extent[3] - extent[2]
    ordered = rows.sort_values(["Longitude", "Latitude", "Shelter Number"]).copy()
    split_at = (len(ordered) + 1) // 2
    label_sides = (
        (ordered.iloc[:split_at], extent[0] + 0.018 * x_span, "left"),
        (ordered.iloc[split_at:], extent[1] - 0.018 * x_span, "right"),
    )
    for side, label_x, horizontal_alignment in label_sides:
        side = side.sort_values(["Latitude", "Longitude", "Shelter Number"]).reset_index(drop=True)
        if side.empty:
            continue
        label_y_positions = np.linspace(
            extent[2] + 0.12 * y_span,
            extent[3] - 0.045 * y_span,
            len(side),
        )
        for (_, row), label_y in zip(side.iterrows(), label_y_positions, strict=True):
            is_increase = str(row["Label Direction"]) == "increase"
            label_face = INCREASE_LABEL_FACE if is_increase else DECREASE_LABEL_FACE
            label_edge = SHORTFALL_COLOR if is_increase else SURPLUS_COLOR
            ax.annotate(
                str(row[label_column]),
                xy=(row["Longitude"], row["Latitude"]),
                xytext=(label_x, label_y),
                textcoords="data",
                ha=horizontal_alignment,
                va="center",
                fontsize=6.15,
                color="#263746",
                bbox={
                    "boxstyle": "round,pad=0.12",
                    "fc": label_face,
                    "ec": label_edge,
                    "linewidth": 0.58,
                    "alpha": 0.97,
                },
                arrowprops={
                    "arrowstyle": "-",
                    "color": label_edge,
                    "linewidth": 0.48,
                    "shrinkA": 2.0,
                    "shrinkB": 1.5,
                },
                zorder=9,
            )


def draw_current_panel(
    ax: plt.Axes,
    screen: pd.DataFrame,
    boundaries: pd.DataFrame,
    target_geometry,
    extent: tuple[float, float, float, float],
) -> None:
    draw_base_map(ax, boundaries, target_geometry, extent)
    balanced = screen.loc[
        screen["Screening Shortfall"].eq(0) & screen["Reported Surplus"].eq(0)
    ]
    donors = screen.loc[screen["Reported Surplus"].gt(0)]
    recipients = screen.loc[screen["Screening Shortfall"].gt(0)]
    ax.scatter(
        balanced["Longitude"], balanced["Latitude"],
        s=19, marker="o", color=BALANCED_COLOR, edgecolor="white", linewidth=0.45, zorder=5,
    )
    ax.scatter(
        donors["Longitude"], donors["Latitude"],
        s=24 + 9 * donors["Reported Surplus"], marker="D", color=SURPLUS_COLOR,
        edgecolor="white", linewidth=0.55, alpha=0.92, zorder=6,
    )
    ax.scatter(
        recipients["Longitude"], recipients["Latitude"],
        s=30 + 10 * recipients["Screening Shortfall"], marker="o", color=SHORTFALL_COLOR,
        edgecolor="white", linewidth=0.65, alpha=0.94, zorder=7,
    )
    active = screen.loc[
        screen["Screening Shortfall"].gt(0) | screen["Reported Surplus"].gt(0)
    ].copy()
    active["Map Label"] = np.where(
        active["Screening Shortfall"].gt(0),
        active["Shelter Number"].map(lambda value: f"Y{int(value):02d}")
        + "  +"
        + active["Screening Shortfall"].astype(str),
        active["Shelter Number"].map(lambda value: f"Y{int(value):02d}")
        + "  −"
        + active["Reported Surplus"].astype(str),
    )
    active["Label Direction"] = np.where(
        active["Screening Shortfall"].gt(0), "increase", "decrease"
    )
    label_column_points(ax, active, extent, "Map Label")
    legend = ax.legend(
        handles=[
            Line2D([0], [0], marker="o", color="none", markerfacecolor=SHORTFALL_COLOR,
                   markeredgecolor="white", markersize=7, label="Required increase (+)"),
            Line2D([0], [0], marker="D", color="none", markerfacecolor=SURPLUS_COLOR,
                   markeredgecolor="white", markersize=6.5, label="Potential decrease (−)"),
            Line2D([0], [0], marker="o", color="none", markerfacecolor=BALANCED_COLOR,
                   markeredgecolor="white", markersize=5.5, label="At screen benchmark"),
        ],
        loc="lower center", ncol=3, frameon=True, facecolor="white", edgecolor="#D0D3D6",
        framealpha=0.94, fontsize=6.4, borderpad=0.35, handletextpad=0.3, columnspacing=0.7,
    )
    legend.set_zorder(12)


def draw_transfer_panel(
    ax: plt.Axes,
    screen: pd.DataFrame,
    flows: pd.DataFrame,
    post: pd.DataFrame,
    boundaries: pd.DataFrame,
    target_geometry,
    extent: tuple[float, float, float, float],
) -> None:
    draw_base_map(ax, boundaries, target_geometry, extent)
    ax.scatter(
        screen["Longitude"], screen["Latitude"], s=13, color="#C7CDD1",
        edgecolor="white", linewidth=0.35, zorder=4,
    )
    for flow_index, flow in flows.iterrows():
        donor = screen.loc[int(flow["Donor Index"])]
        recipient = screen.loc[int(flow["Recipient Index"])]
        quantity = int(flow["Units"])
        curvature = 0.05 * (-1 if flow_index % 2 else 1)
        arrow = FancyArrowPatch(
            (donor["Longitude"], donor["Latitude"]),
            (recipient["Longitude"], recipient["Latitude"]),
            arrowstyle="-|>",
            mutation_scale=7.0 + 0.35 * quantity,
            connectionstyle=f"arc3,rad={curvature}",
            linewidth=0.65 + 0.42 * quantity,
            color=TRANSFER_COLOR,
            alpha=0.68,
            shrinkA=3.2,
            shrinkB=4.2,
            zorder=5,
        )
        ax.add_patch(arrow)
        midpoint_x = (donor["Longitude"] + recipient["Longitude"]) / 2
        midpoint_y = (donor["Latitude"] + recipient["Latitude"]) / 2
        ax.text(
            midpoint_x, midpoint_y, str(quantity), ha="center", va="center", fontsize=5.8,
            fontweight="bold", color="#36596D",
            bbox={"boxstyle": "circle,pad=0.12", "fc": "white", "ec": TRANSFER_COLOR,
                  "linewidth": 0.45, "alpha": 0.92},
            zorder=7,
        )

    used_donors = post.loc[post["Transfer Out"].gt(0)]
    recipients = post.loc[post["Transfer In"].gt(0)]
    ax.scatter(
        used_donors["Longitude"], used_donors["Latitude"],
        s=30 + 7 * used_donors["Transfer Out"], marker="s", color=SURPLUS_COLOR,
        edgecolor="white", linewidth=0.6, zorder=8,
    )
    ax.scatter(
        recipients["Longitude"], recipients["Latitude"],
        s=34 + 8 * recipients["Transfer In"], marker="o", color=RESOLVED_COLOR,
        edgecolor="white", linewidth=0.7, zorder=8,
    )
    active = pd.concat([used_donors, recipients]).drop_duplicates().copy()
    active["Map Label"] = np.where(
        active["Transfer In"].gt(0),
        active["Shelter Number"].map(lambda value: f"Y{int(value):02d}")
        + "  +"
        + active["Transfer In"].astype(str),
        active["Shelter Number"].map(lambda value: f"Y{int(value):02d}")
        + "  −"
        + active["Transfer Out"].astype(str),
    )
    active["Label Direction"] = np.where(
        active["Transfer In"].gt(0), "increase", "decrease"
    )
    label_column_points(ax, active, extent, "Map Label")
    legend = ax.legend(
        handles=[
            Line2D([0], [0], marker="s", color="none", markerfacecolor=SURPLUS_COLOR,
                   markeredgecolor="white", markersize=6.5, label="Conditional donor (−)"),
            Line2D([0], [0], marker="o", color="none", markerfacecolor=RESOLVED_COLOR,
                   markeredgecolor="white", markersize=7, label="Transfer target (+)"),
            Line2D([0, 1], [0, 0], color=TRANSFER_COLOR, linewidth=2.0,
                   label="Conditional transfer; label = units"),
        ],
        loc="lower center", ncol=3, frameon=True, facecolor="white", edgecolor="#D0D3D6",
        framealpha=0.94, fontsize=6.4, borderpad=0.35, handletextpad=0.35, columnspacing=0.8,
    )
    legend.set_zorder(12)


def main() -> None:
    frame = pd.read_parquet(SOURCE)
    required = {
        "Municipality", "Shelter Number", "Shelter Name", "Latitude", "Longitude",
        "Location Resolution", "Evacuees", "Water Status", "Temporary Toilets Installed",
        "Toilet Cars", "Scenario", "Estimated Functional Support Evacuees",
        "Estimated Female Functional Support Evacuees",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")
    base = frame.loc[
        frame["Municipality"].eq(TARGET_MUNICIPALITY)
        & frame["Scenario"].astype("string").eq("base")
    ].copy().reset_index(drop=True)
    if len(base) != 38:
        raise ValueError("Expected 38 Yatsushiro shelters in the base scenario")
    if base[list(required.difference({"Municipality", "Scenario"}))].isna().any().any():
        raise ValueError("Required Yatsushiro rebalancing fields must be complete")
    if (base[["Evacuees", "Temporary Toilets Installed", "Toilet Cars"]] < 0).any().any():
        raise ValueError("Demand and deployment values cannot be negative")

    screen = construct_screen(base)
    if int(screen["Screening Shortfall"].sum()) != 31:
        raise ValueError("Expected a 31-unit current screening shortfall")
    if int(screen["Reported Surplus"].sum()) != 72:
        raise ValueError("Expected 72 reported units above sitewise requirements")
    if int(screen["Screening Shortfall"].gt(0).sum()) != 11:
        raise ValueError("Expected 11 current shortfall shelters")
    flows, post = full_mobility_flows(screen)
    if int(flows["Units"].sum()) != 31 or int(post["Residual Shortfall"].sum()) != 0:
        raise ValueError("Full-mobility scenario must move 31 units and resolve the screen")
    if int(post["Transfer In"].sum()) != int(post["Transfer Out"].sum()):
        raise ValueError("Transfer inflow and outflow must be conserved")
    donor_rows = post.loc[post["Transfer Out"].gt(0)]
    if (donor_rows["Post-Transfer Inventory"] < donor_rows["Prolonged Requirement"]).any():
        raise ValueError("A donor falls below its protected prolonged requirement")

    boundaries = load_boundaries()
    target_geometry, extent = map_geometry(boundaries)
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
    fig, axes = plt.subplots(1, 2, figsize=(14.2, 7.4), gridspec_kw={"width_ratios": [1, 1]})
    fig.subplots_adjust(left=0.07, right=0.985, bottom=0.08, top=0.93, wspace=0.18)
    draw_current_panel(axes[0], screen, boundaries, target_geometry, extent)
    draw_transfer_panel(axes[1], screen, flows, post, boundaries, target_geometry, extent)
    add_panel_heading(axes[0], "a", "Current screen · 31 shortfall units, 72 reported surplus units")
    add_panel_heading(axes[1], "b", "Full-mobility sensitivity · 31 moved, residual screen = 0")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
