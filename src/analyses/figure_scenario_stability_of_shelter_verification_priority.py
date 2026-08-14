#!/usr/bin/env python3
"""Scenario Stability of Shelter Verification Priority.

Plan: Compare within-city shelter verification ranks across the low, base, and
high overlap scenarios and display each shelter's maximum rank movement.
Framework: Section 5 scenario-stability contrast; Section 6 descending
lexicographic rank pi, top-20-percent threshold h, and rank span B; Section 7
verification-priority robustness workflow. Ranks guide field verification and
do not estimate intervention benefit or optimize deployment.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/processed/shelter_equity_scenarios_preprocessed.parquet"
OUTPUT = (
    ROOT
    / "data/results/figures/"
    "Figure_scenario_stability_of_shelter_verification_priority.png"
)

SCENARIOS = ("low", "base", "high")
SCENARIO_LABELS = ("Low rank", "Base rank", "High rank")
PANELS = (
    ("八代市", "Yatsushiro City", "Y"),
    ("熊本市", "Kumamoto City", "K"),
)
RANK_CMAP = LinearSegmentedColormap.from_list(
    "priority_rank", ("#F6F1EA", "#E6B6A7", "#A94335")
)
STABILITY_COLORS = {
    "Stable": "#BFD8CC",
    "Low sensitivity": "#E8D49E",
    "Scenario-sensitive": "#B9A5CC",
}


def add_panel_heading(ax: plt.Axes, label: str, heading: str) -> None:
    ax.text(
        -0.115,
        1.070,
        label,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=12,
        fontweight="bold",
        color="#263746",
    )
    ax.text(
        -0.035,
        1.070,
        heading,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9.5,
        fontweight="bold",
        color="#263746",
    )


def assign_ranks(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply the predeclared within-city descending lexicographic rank."""
    ranked_frames: list[pd.DataFrame] = []
    for municipality, city_frame in frame.groupby("Municipality", sort=False):
        for scenario in SCENARIOS:
            scenario_frame = city_frame.loc[city_frame["Scenario"].eq(scenario)].copy()
            scenario_frame = scenario_frame.sort_values(
                [
                    "Estimated Functional Support Evacuees",
                    "Estimated Female Functional Support Evacuees",
                    "Evacuees",
                    "Shelter Number",
                ],
                ascending=[False, False, False, True],
                kind="stable",
            )
            scenario_frame["Verification Rank"] = np.arange(
                1, len(scenario_frame) + 1
            )
            ranked_frames.append(scenario_frame)

    ranked = pd.concat(ranked_frames, ignore_index=True)
    id_columns = ["Municipality", "Shelter Number", "Shelter Name"]
    wide = (
        ranked.pivot(
            index=id_columns,
            columns="Scenario",
            values="Verification Rank",
        )
        .reset_index()
        .rename_axis(columns=None)
    )
    wide["Max Rank Change"] = wide[list(SCENARIOS)].max(axis=1) - wide[
        list(SCENARIOS)
    ].min(axis=1)
    wide["Sensitivity"] = pd.cut(
        wide["Max Rank Change"],
        bins=[-np.inf, 0, 2, np.inf],
        labels=["Stable", "Low sensitivity", "Scenario-sensitive"],
    ).astype(str)
    city_sizes = wide.groupby("Municipality")["Shelter Number"].transform("size")
    thresholds = np.ceil(0.20 * city_sizes).astype(int)
    wide["Top Threshold"] = thresholds
    wide["Stable High Priority"] = wide[list(SCENARIOS)].max(axis=1).le(thresholds)
    return wide


def validate(frame: pd.DataFrame, wide: pd.DataFrame) -> None:
    required = {
        "Municipality",
        "Shelter Number",
        "Shelter Name",
        "Scenario",
        "Evacuees",
        "Estimated Functional Support Evacuees",
        "Estimated Female Functional Support Evacuees",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")
    if set(frame["Scenario"].dropna().unique()) != set(SCENARIOS):
        raise ValueError("Expected exactly low, base, and high overlap scenarios")
    expected_counts = {"八代市": 38, "熊本市": 15}
    observed_counts = wide.groupby("Municipality").size().to_dict()
    if observed_counts != expected_counts:
        raise ValueError(f"Unexpected shelter counts: {observed_counts}")
    if frame[list(required)].isna().any().any():
        raise ValueError("Scenario-ranking inputs must be complete")
    if frame.duplicated(["Municipality", "Shelter Number", "Scenario"]).any():
        raise ValueError("Shelter-scenario keys must be unique")
    for municipality, count in expected_counts.items():
        city = wide.loc[wide["Municipality"].eq(municipality)]
        for scenario in SCENARIOS:
            if sorted(city[scenario].astype(int).tolist()) != list(range(1, count + 1)):
                raise ValueError(f"Invalid {scenario} rank permutation for {municipality}")


def draw_city_panel(
    ax: plt.Axes,
    city: pd.DataFrame,
    municipality_label: str,
    prefix: str,
    panel_label: str,
) -> None:
    city = city.sort_values(["base", "Shelter Number"], kind="stable").reset_index(
        drop=True
    )
    n_shelters = len(city)
    threshold = int(city["Top Threshold"].iloc[0])
    rank_values = city[list(SCENARIOS)].to_numpy(dtype=float)
    normalized_priority = 1 - ((rank_values - 1) / max(n_shelters - 1, 1))

    ax.imshow(
        normalized_priority,
        cmap=RANK_CMAP,
        vmin=0,
        vmax=1,
        interpolation="nearest",
        aspect="auto",
        extent=(-0.5, 2.5, n_shelters - 0.5, -0.5),
        zorder=1,
    )

    # The fourth column displays B_jc using the predeclared stability classes.
    for row_index, row in city.iterrows():
        sensitivity = str(row["Sensitivity"])
        ax.add_patch(
            Rectangle(
                (2.62, row_index - 0.5),
                0.76,
                1.0,
                facecolor=STABILITY_COLORS[sensitivity],
                edgecolor="white",
                linewidth=0.45,
                zorder=2,
            )
        )
        for column_index, scenario in enumerate(SCENARIOS):
            value = int(row[scenario])
            text_color = "white" if value <= max(2, round(n_shelters * 0.12)) else "#263746"
            ax.text(
                column_index,
                row_index,
                str(value),
                ha="center",
                va="center",
                fontsize=6.5 if n_shelters > 20 else 7.4,
                fontweight="bold" if bool(row["Stable High Priority"]) else "normal",
                color=text_color,
                zorder=3,
            )
        ax.text(
            3.0,
            row_index,
            str(int(row["Max Rank Change"])),
            ha="center",
            va="center",
            fontsize=6.5 if n_shelters > 20 else 7.4,
            fontweight="bold" if sensitivity == "Scenario-sensitive" else "normal",
            color="#263746",
            zorder=3,
        )

    # White cell borders preserve readability without making the panel heavy.
    ax.set_xticks(np.arange(-0.5, 3.51, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, n_shelters, 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=0.45)
    ax.tick_params(which="minor", bottom=False, left=False)

    shelter_codes = [f"{prefix}{int(number):02d}" for number in city["Shelter Number"]]
    ax.set_yticks(np.arange(n_shelters), shelter_codes)
    ax.set_xticks([0, 1, 2, 3], [*SCENARIO_LABELS, "Max Δ"])
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", labelsize=7.8, length=0, pad=6)
    ax.tick_params(axis="y", labelsize=6.2 if n_shelters > 20 else 7.2, length=0, pad=4)
    ax.set_xlim(-0.5, 3.42)
    ax.set_ylim(n_shelters - 0.5, -0.5)
    for spine in ax.spines.values():
        spine.set_visible(False)

    # In base-rank order this line marks the prespecified top-20-percent set.
    ax.axhline(threshold - 0.5, color="#354B5E", linewidth=1.15, zorder=5)
    for index, label in enumerate(ax.get_yticklabels()):
        row = city.iloc[index]
        if bool(row["Stable High Priority"]):
            label.set_fontweight("bold")
            label.set_color("#A94335")
        elif str(row["Sensitivity"]) == "Scenario-sensitive":
            label.set_fontweight("bold")
            label.set_color("#72558A")

    stable_high = int(city["Stable High Priority"].sum())
    sensitive = int(city["Sensitivity"].eq("Scenario-sensitive").sum())
    add_panel_heading(
        ax,
        panel_label,
        f"{municipality_label}: {stable_high} stable top-{threshold}; "
        f"{sensitive} scenario-sensitive",
    )


def main() -> None:
    frame = pd.read_parquet(SOURCE)
    required_for_filter = {"Municipality", "Scenario"}
    missing_filter = required_for_filter.difference(frame.columns)
    if missing_filter:
        raise KeyError(f"Missing required columns: {sorted(missing_filter)}")
    frame = frame.loc[
        frame["Municipality"].isin([panel[0] for panel in PANELS])
        & frame["Scenario"].isin(SCENARIOS)
    ].copy()
    wide = assign_ranks(frame)
    validate(frame, wide)

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 9.4), gridspec_kw={"width_ratios": [1, 1]})
    fig.subplots_adjust(left=0.075, right=0.985, bottom=0.105, top=0.900, wspace=0.22)

    for panel_index, (ax, (municipality, display_name, prefix)) in enumerate(
        zip(axes, PANELS, strict=True)
    ):
        city = wide.loc[wide["Municipality"].eq(municipality)].copy()
        draw_city_panel(
            ax,
            city,
            display_name,
            prefix,
            chr(ord("a") + panel_index),
        )

    legend_handles = [
        Line2D(
            [0],
            [0],
            marker="s",
            color="none",
            markerfacecolor="#A94335",
            markeredgecolor="none",
            markersize=7,
            label="Earlier rank (darker)",
        ),
        *[
            Patch(facecolor=color, edgecolor="none", label=label)
            for label, color in STABILITY_COLORS.items()
        ],
        Line2D(
            [0],
            [0],
            color="#354B5E",
            linewidth=1.15,
            label="Top 20% threshold",
        ),
    ]
    fig.legend(
        handles=legend_handles,
        loc="lower center",
        ncol=5,
        frameon=False,
        fontsize=7.6,
        handlelength=1.4,
        handletextpad=0.45,
        columnspacing=1.25,
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
