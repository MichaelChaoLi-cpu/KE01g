#!/usr/bin/env python3
"""Gender and Functional-Support Toilet Service Packages.

Plan: Display the quantitative and operational service-package recommendations
for Yatsushiro shelters with a positive temporary-toilet-only screening shortfall.
Framework: Section 5 equity-sensitive conditional mitigation; Section 6 full-
mobility general-unit addition, women-to-men planning designation, and separate
Accessible Unit Parity Screen; Section 7 service-package verification workflow.
Actions are recommendations to verify or provide, not observed facility features.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from matplotlib.patches import Patch, Rectangle
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/processed/shelter_equity_scenarios_preprocessed.parquet"
OUTPUT = (
    ROOT
    / "data/results/figures/"
    "Figure_gender_and_functional_support_toilet_service_packages.png"
)

TARGET_MUNICIPALITY = "八代市"
QUANTITY_COLUMNS = (
    "Evacuees",
    "Estimated Female Evacuees",
    "Estimated Functional Support Evacuees",
    "Estimated Female Functional Support Evacuees",
    "Temporary Toilets Installed",
    "Toilet Cars",
    "General Unit Addition",
    "Women Designation",
    "Men Designation",
    "Prolonged Accessible Unit Parity Screen",
)
QUANTITY_LABELS = (
    "Observed\nevacuees",
    "Estimated\nwomen",
    "Estimated\nfunctional support",
    "Estimated women +\nfunctional support",
    "Reported\ntemporary toilets",
    "Reported\ntoilet cars",
    "Add general\nunits",
    "Designate\nfor women",
    "Designate\nfor men",
    "Accessible parity\n(separate screen)",
)
QUANTITY_COLORS = (
    "#607D91",
    "#9A6F91",
    "#7A6A9E",
    "#A45D7B",
    "#637D8C",
    "#637D8C",
    "#C65345",
    "#C65345",
    "#3B73A1",
    "#3C8D76",
)
ACTION_COLUMNS = (
    "Water and wastewater",
    "Containment and collection",
    "Lighting and locks",
    "Handwashing",
    "Menstrual hygiene",
    "Accessible route",
)
ACTION_LABELS = (
    "Water +\nwastewater",
    "Containment +\ncollection",
    "Lighting +\nlocks",
    "Handwashing",
    "Menstrual\nhygiene",
    "Accessible\nroute",
)
ACTION_COLORS = {
    "Immediate response": "#E3A29A",
    "Verify and prepare": "#EAD8A7",
    "Include in package": "#BFD8CC",
    "Women-specific": "#D9BED0",
}


def english_facility_type(name: str) -> str:
    rules = (
        ("総合体育館", "Arena"),
        ("コミュニティセンター", "Community Center"),
        ("保健センター", "Health Center"),
        ("中学校", "Junior High School"),
        ("小学校", "Elementary School"),
    )
    for source_text, english_text in rules:
        if source_text in name:
            return english_text
    raise ValueError(f"No English facility-class rule for shelter: {name!r}")


def add_panel_heading(ax: plt.Axes, label: str, heading: str) -> None:
    ax.text(
        -0.025,
        1.205,
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
        1.205,
        heading,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9.3,
        fontweight="bold",
        color="#263746",
    )


def blend_with_white(color: str, strength: float) -> tuple[float, float, float]:
    rgb = np.asarray(to_rgb(color))
    strength = float(np.clip(strength, 0.16, 1.0))
    return tuple(1.0 - strength * (1.0 - rgb))


def construct_priority_frame(frame: pd.DataFrame) -> pd.DataFrame:
    priority = frame.copy()
    priority["Prolonged Requirement"] = np.ceil(priority["Evacuees"] / 20).astype(int)
    priority["General Unit Addition"] = (
        priority["Prolonged Requirement"] - priority["Temporary Toilets Installed"]
    ).clip(lower=0).astype(int)
    priority = priority.loc[priority["General Unit Addition"].gt(0)].copy()
    priority["Women Designation"] = np.ceil(
        0.75 * priority["General Unit Addition"]
    ).astype(int)
    priority["Men Designation"] = (
        priority["General Unit Addition"] - priority["Women Designation"]
    ).astype(int)
    priority = priority.sort_values(
        [
            "General Unit Addition",
            "Estimated Functional Support Evacuees",
            "Estimated Female Functional Support Evacuees",
            "Evacuees",
            "Shelter Number",
        ],
        ascending=[False, False, False, False, True],
        kind="stable",
    ).reset_index(drop=True)
    priority["Shelter Label"] = [
        f"Y{int(number):02d}  {english_facility_type(str(name))}"
        for number, name in zip(
            priority["Shelter Number"], priority["Shelter Name"], strict=True
        )
    ]
    return priority


def draw_quantity_panel(ax: plt.Axes, priority: pd.DataFrame) -> None:
    values = priority[list(QUANTITY_COLUMNS)].to_numpy(dtype=float)
    n_rows, n_columns = values.shape
    rgba = np.ones((n_rows, n_columns, 4), dtype=float)
    for column_index, color in enumerate(QUANTITY_COLORS):
        column = values[:, column_index]
        maximum = max(float(column.max()), 1.0)
        strengths = 0.20 + 0.80 * np.sqrt(column / maximum)
        for row_index, strength in enumerate(strengths):
            rgba[row_index, column_index, :3] = blend_with_white(color, float(strength))
    ax.imshow(rgba, aspect="auto", interpolation="nearest")

    decimals = {1, 2, 3}
    for row_index in range(n_rows):
        for column_index in range(n_columns):
            value = values[row_index, column_index]
            label = f"{value:.1f}" if column_index in decimals else f"{int(round(value))}"
            maximum = max(float(values[:, column_index].max()), 1.0)
            strength = 0.20 + 0.80 * np.sqrt(value / maximum)
            text_color = "white" if strength > 0.73 else "#263746"
            ax.text(
                column_index,
                row_index,
                label,
                ha="center",
                va="center",
                fontsize=7.0,
                fontweight="bold" if column_index >= 6 else "normal",
                color=text_color,
                zorder=3,
            )

    ax.set_xticks(np.arange(n_columns), QUANTITY_LABELS)
    ax.set_yticks(np.arange(n_rows), priority["Shelter Label"])
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", labelsize=7.0, length=0, pad=6)
    ax.tick_params(axis="y", labelsize=7.2, length=0, pad=5)
    ax.set_xticks(np.arange(-0.5, n_columns, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, n_rows, 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=0.65)
    ax.tick_params(which="minor", bottom=False, left=False, top=False)
    ax.axvline(3.5, color="#51616E", linewidth=1.15)
    ax.axvline(5.5, color="#51616E", linewidth=1.15)
    ax.axvline(8.5, color="#3C8D76", linewidth=1.15)
    for spine in ax.spines.values():
        spine.set_visible(False)
    add_panel_heading(
        ax,
        "a",
        "Demand, reported context, and recommended quantities · accessible parity is separate",
    )


def action_package(priority: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    n_rows = len(priority)
    classes = np.empty((n_rows, len(ACTION_COLUMNS)), dtype=object)
    labels = np.empty((n_rows, len(ACTION_COLUMNS)), dtype=object)
    for row_index, (_, row) in enumerate(priority.iterrows()):
        water_unavailable = str(row["Water Status"]) == "×"
        if water_unavailable:
            classes[row_index, 0] = "Immediate response"
            labels[row_index, 0] = "Use non-flush\n+ verify sewer"
            classes[row_index, 1] = "Immediate response"
            labels[row_index, 1] = "Set storage\n+ collection"
        else:
            classes[row_index, 0] = "Verify and prepare"
            labels[row_index, 0] = "Verify\nwastewater"
            classes[row_index, 1] = "Verify and prepare"
            labels[row_index, 1] = "Confirm backup\ncollection"
        classes[row_index, 2] = "Include in package"
        labels[row_index, 2] = "Verify /\nprovide"
        classes[row_index, 3] = "Include in package"
        labels[row_index, 3] = "Provide"
        classes[row_index, 4] = "Women-specific"
        labels[row_index, 4] = "Provide bin\n+ supplies"
        classes[row_index, 5] = "Include in package"
        labels[row_index, 5] = "Verify /\nclear"
    return classes, labels


def draw_action_panel(ax: plt.Axes, priority: pd.DataFrame) -> None:
    classes, labels = action_package(priority)
    n_rows, n_columns = classes.shape
    for row_index in range(n_rows):
        for column_index in range(n_columns):
            action_class = str(classes[row_index, column_index])
            ax.add_patch(
                Rectangle(
                    (column_index - 0.5, row_index - 0.5),
                    1,
                    1,
                    facecolor=ACTION_COLORS[action_class],
                    edgecolor="white",
                    linewidth=0.65,
                )
            )
            ax.text(
                column_index,
                row_index,
                str(labels[row_index, column_index]),
                ha="center",
                va="center",
                fontsize=6.7,
                color="#263746",
                linespacing=1.05,
            )
    ax.set_xlim(-0.5, n_columns - 0.5)
    ax.set_ylim(n_rows - 0.5, -0.5)
    ax.set_xticks(np.arange(n_columns), ACTION_LABELS)
    ax.set_yticks(np.arange(n_rows), priority["Shelter Label"])
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", labelsize=7.2, length=0, pad=6)
    ax.tick_params(axis="y", labelsize=7.2, length=0, pad=5)
    for spine in ax.spines.values():
        spine.set_visible(False)
    add_panel_heading(
        ax,
        "b",
        "Actions to verify or provide · cells are recommendations, not observed conditions",
    )


def validate(frame: pd.DataFrame, priority: pd.DataFrame) -> None:
    required = {
        "Municipality",
        "Shelter Number",
        "Shelter Name",
        "Evacuees",
        "Estimated Female Evacuees",
        "Estimated Functional Support Evacuees",
        "Estimated Female Functional Support Evacuees",
        "Prolonged Accessible Unit Parity Screen",
        "Water Status",
        "Temporary Toilets Installed",
        "Toilet Cars",
        "Scenario",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")
    if frame[list(required)].isna().any().any():
        raise ValueError("Required service-package fields must be complete")
    if len(priority) != 11:
        raise ValueError("Expected 11 Yatsushiro shelters with a positive screening shortfall")
    if int(priority["General Unit Addition"].sum()) != 31:
        raise ValueError("Expected 31 recommended general-unit additions")
    if int(priority["Women Designation"].sum()) != 26:
        raise ValueError("Expected 26 incremental units designated for women")
    if int(priority["Men Designation"].sum()) != 5:
        raise ValueError("Expected 5 incremental units designated for men")
    if int(priority["Prolonged Accessible Unit Parity Screen"].sum()) != 12:
        raise ValueError("Expected an accessible-parity screen total of 12")
    if not (
        priority["Women Designation"] + priority["Men Designation"]
    ).eq(priority["General Unit Addition"]).all():
        raise ValueError("Women and men designations must reproduce general additions")
    if set(priority["Water Status"].astype(str)) != {"〇", "×"}:
        raise ValueError("Expected available and unavailable water states in priority shelters")


def main() -> None:
    frame = pd.read_parquet(SOURCE)
    base = frame.loc[
        frame["Municipality"].eq(TARGET_MUNICIPALITY)
        & frame["Scenario"].astype("string").eq("base")
    ].copy()
    priority = construct_priority_frame(base)
    validate(base, priority)

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    fig, axes = plt.subplots(2, 1, figsize=(14.4, 10.8))
    fig.subplots_adjust(left=0.18, right=0.985, bottom=0.075, top=0.895, hspace=0.52)
    draw_quantity_panel(axes[0], priority)
    draw_action_panel(axes[1], priority)

    action_handles = [
        Patch(facecolor=color, edgecolor="none", label=label)
        for label, color in ACTION_COLORS.items()
    ]
    fig.legend(
        handles=action_handles,
        loc="lower center",
        ncol=4,
        frameon=False,
        fontsize=7.8,
        handlelength=1.5,
        handletextpad=0.45,
        columnspacing=1.4,
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
