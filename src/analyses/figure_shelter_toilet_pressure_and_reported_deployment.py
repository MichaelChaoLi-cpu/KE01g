#!/usr/bin/env python3
"""Shelter Toilet Pressure and Reported Deployment.

Plan: Rank matched shelters by observed evacuees and align each row with
reported temporary-toilet units and toilet-car vehicles.
Framework: Section 5 missing-preserving deployment screen; Section 6 reported
deployment inputs and no-deployable-unit indicator; Section 7 field-verification
screen. Toilet cars remain vehicle counts and missing reports are not zeros.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/processed/shelter_equity_scenarios_preprocessed.parquet"
OUTPUT = (
    ROOT
    / "data/results/figures/"
    "Figure_shelter_toilet_pressure_and_reported_deployment.png"
)

PANELS = (
    ("八代市", "Yatsushiro City", "Y"),
    ("熊本市", "Kumamoto City", "K"),
)
EVACUEE_COLOR = "#9AA6AF"
TEMPORARY_COLOR = "#2F6F9F"
TOILET_CAR_COLOR = "#D2644F"
MISSING_X = -2.0


def english_facility_type(name: str) -> str:
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


def add_panel_heading(ax: plt.Axes, label: str, heading: str) -> None:
    ax.text(
        -0.06,
        1.025,
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
        1.025,
        heading,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9.5,
        fontweight="bold",
        color="#263746",
    )


def main() -> None:
    frame = pd.read_parquet(SOURCE)
    required = {
        "Municipality",
        "Shelter Number",
        "Shelter Name",
        "Evacuees",
        "Temporary Toilets Installed",
        "Toilet Cars",
        "Scenario",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")
    base = frame.loc[frame["Scenario"].astype("string").eq("base")].copy()
    if len(base) != 53:
        raise ValueError("Expected 53 shelters in the matched base-scenario sample")
    if base.duplicated(["Municipality", "Shelter Number"]).any():
        raise ValueError("Shelter identifiers are not unique within municipality")
    if base["Evacuees"].isna().any() or (base["Evacuees"] < 0).any():
        raise ValueError("Evacuees must be complete and nonnegative")
    for column in ("Temporary Toilets Installed", "Toilet Cars"):
        if (base[column].dropna() < 0).any():
            raise ValueError(f"{column} cannot be negative where reported")

    expected_coverage = {
        "八代市": {"shelters": 38, "temporary": 38, "cars": 38},
        "熊本市": {"shelters": 15, "temporary": 1, "cars": 0},
    }
    for municipality, expected in expected_coverage.items():
        city = base.loc[base["Municipality"].eq(municipality)]
        observed = {
            "shelters": len(city),
            "temporary": int(city["Temporary Toilets Installed"].notna().sum()),
            "cars": int(city["Toilet Cars"].notna().sum()),
        }
        if observed != expected:
            raise ValueError(
                f"Unexpected deployment coverage for {municipality}: {observed}"
            )

    maximum_reported = float(
        pd.concat(
            [base["Temporary Toilets Installed"], base["Toilet Cars"]],
            ignore_index=True,
        ).max(skipna=True)
    )
    deployment_right = max(12.8, maximum_reported * 1.08)

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
    fig = plt.figure(figsize=(14.5, 14.5))
    outer = fig.add_gridspec(1, 2, width_ratios=(1, 1), wspace=0.24)
    panel_axes: list[tuple[plt.Axes, plt.Axes]] = []
    for panel_index in range(2):
        inner = outer[panel_index].subgridspec(
            1,
            2,
            width_ratios=(0.66, 0.34),
            wspace=0.045,
        )
        demand_ax = fig.add_subplot(inner[0, 0])
        deployment_ax = fig.add_subplot(inner[0, 1], sharey=demand_ax)
        panel_axes.append((demand_ax, deployment_ax))
    fig.subplots_adjust(left=0.11, right=0.985, bottom=0.085, top=0.975)

    for panel_index, ((demand_ax, deployment_ax), (municipality, display, prefix)) in enumerate(
        zip(panel_axes, PANELS, strict=True)
    ):
        city = (
            base.loc[base["Municipality"].eq(municipality)]
            .sort_values(["Evacuees", "Shelter Number"], ascending=[False, True])
            .reset_index(drop=True)
        )
        y_positions = np.arange(len(city))
        for row in range(len(city)):
            if row % 2 == 0:
                demand_ax.axhspan(row - 0.5, row + 0.5, color="#F5F6F7", zorder=0)
                deployment_ax.axhspan(row - 0.5, row + 0.5, color="#F5F6F7", zorder=0)

        bars = demand_ax.barh(
            y_positions,
            city["Evacuees"],
            height=0.56,
            color=EVACUEE_COLOR,
            edgecolor="white",
            linewidth=0.45,
            zorder=3,
        )
        demand_ax.bar_label(
            bars,
            labels=[f"{int(value)}" for value in city["Evacuees"]],
            padding=2.5,
            fontsize=6.8,
            color="#3B4852",
        )
        shelter_labels = [
            f"{prefix}{int(number):02d}  {english_facility_type(str(name))}"
            for number, name in zip(
                city["Shelter Number"], city["Shelter Name"], strict=True
            )
        ]
        demand_ax.set_yticks(y_positions, shelter_labels, fontsize=7.0)
        demand_ax.tick_params(axis="y", length=0, pad=5)
        demand_ax.tick_params(axis="x", labelsize=7.8, length=2.5, pad=2)
        demand_ax.set_ylim(len(city) - 0.45, -0.55)
        demand_ax.set_xlim(
            left=0,
            right=max(1.0, float(city["Evacuees"].max()) * 1.15),
        )
        demand_ax.xaxis.set_major_locator(MaxNLocator(nbins=5, integer=True, min_n_ticks=4))
        demand_ax.grid(axis="x", color="#D9DDE1", linewidth=0.5, zorder=0)
        demand_ax.set_xlabel("Observed evacuees (persons)", fontsize=8.6, labelpad=7)

        temporary_x = city["Temporary Toilets Installed"].fillna(MISSING_X)
        cars_x = city["Toilet Cars"].fillna(MISSING_X)
        temporary_reported = city["Temporary Toilets Installed"].notna()
        cars_reported = city["Toilet Cars"].notna()
        deployment_ax.scatter(
            temporary_x[temporary_reported],
            y_positions[temporary_reported] - 0.13,
            marker="s",
            s=30,
            color=TEMPORARY_COLOR,
            edgecolor="white",
            linewidth=0.5,
            zorder=4,
        )
        deployment_ax.scatter(
            temporary_x[~temporary_reported],
            y_positions[~temporary_reported] - 0.13,
            marker="s",
            s=29,
            facecolor="white",
            edgecolor=TEMPORARY_COLOR,
            linewidth=0.8,
            zorder=4,
        )
        deployment_ax.scatter(
            cars_x[cars_reported],
            y_positions[cars_reported] + 0.13,
            marker="^",
            s=34,
            color=TOILET_CAR_COLOR,
            edgecolor="white",
            linewidth=0.5,
            zorder=4,
        )
        deployment_ax.scatter(
            cars_x[~cars_reported],
            y_positions[~cars_reported] + 0.13,
            marker="^",
            s=33,
            facecolor="white",
            edgecolor=TOILET_CAR_COLOR,
            linewidth=0.8,
            zorder=4,
        )
        has_missing = bool((~temporary_reported).any() or (~cars_reported).any())
        if has_missing:
            deployment_ax.set_xlim(MISSING_X - 0.8, deployment_right)
            deployment_ax.set_xticks(
                [MISSING_X, 0, 5, 10],
                labels=["NR", "0", "5", "10"],
            )
            deployment_ax.axvline(-1.0, color="#B9C0C5", linewidth=0.6, zorder=1)
        else:
            deployment_ax.set_xlim(-0.6, deployment_right)
            deployment_ax.set_xticks([0, 5, 10], labels=["0", "5", "10"])
        deployment_ax.tick_params(axis="x", labelsize=7.8, length=2.5, pad=2)
        deployment_ax.tick_params(axis="y", left=False, labelleft=False)
        deployment_ax.grid(axis="x", color="#D9DDE1", linewidth=0.5, zorder=0)
        deployment_ax.set_xlabel("Reported count", fontsize=8.6, labelpad=7)

        temporary_coverage = int(city["Temporary Toilets Installed"].notna().sum())
        car_coverage = int(city["Toilet Cars"].notna().sum())
        heading = (
            f"{display}  |  temporary {temporary_coverage}/{len(city)}; "
            f"toilet cars {car_coverage}/{len(city)} reported"
        )
        add_panel_heading(demand_ax, chr(ord("a") + panel_index), heading)

    legend_handles = [
        Patch(facecolor=EVACUEE_COLOR, edgecolor="white", label="Observed evacuees"),
        Line2D(
            [0],
            [0],
            marker="s",
            color="none",
            markerfacecolor=TEMPORARY_COLOR,
            markeredgecolor="white",
            markersize=7,
            label="Temporary-toilet units",
        ),
        Line2D(
            [0],
            [0],
            marker="^",
            color="none",
            markerfacecolor=TOILET_CAR_COLOR,
            markeredgecolor="white",
            markersize=7,
            label="Toilet-car vehicles",
        ),
        Line2D(
            [0],
            [0],
            marker="s",
            color="none",
            markerfacecolor="white",
            markeredgecolor="#65727B",
            markeredgewidth=0.8,
            markersize=6.5,
            label="Open marker at NR: not reported",
        ),
    ]
    fig.legend(
        handles=legend_handles,
        loc="lower center",
        ncol=4,
        frameon=False,
        fontsize=8.2,
        handletextpad=0.45,
        columnspacing=1.35,
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
