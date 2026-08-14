#!/usr/bin/env python3
"""Aggregate versus Shelter-Specific Toilet Requirements.

Plan: Contrast pooled-city requirements with the sum of shelter-specific,
upward-rounded requirements under initial and prolonged-stay benchmarks.
Framework: Section 5 spatial-fragmentation contrast; Section 6 benchmark,
pooled, sitewise, and fragmentation-increment equations; Section 7 matched-city
comparison. These are standards-based requirements, not functional deficits.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/processed/shelter_equity_scenarios_preprocessed.parquet"
OUTPUT = (
    ROOT
    / "data/results/figures/"
    "Figure_aggregate_versus_shelter_specific_toilet_requirements.png"
)

CITY_ORDER = ("八代市", "熊本市")
CITY_LABELS = {"八代市": "Yatsushiro City", "熊本市": "Kumamoto City"}
BENCHMARKS = (
    ("initial", 50, "Initial response: 1 toilet per 50 evacuees"),
    ("prolonged", 20, "Prolonged stay: 1 toilet per 20 evacuees"),
)
BAR_STYLE = {
    "Pooled city": "#A6ADB4",
    "Sum of shelter-specific": "#2F6F9F",
}


def add_panel_heading(ax: plt.Axes, label: str, heading: str) -> None:
    ax.text(
        -0.095,
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
        -0.025,
        1.035,
        heading,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9.5,
        fontweight="bold",
        color="#263746",
    )


def build_comparison(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    for municipality in CITY_ORDER:
        city = frame.loc[frame["Municipality"].eq(municipality)]
        if city.empty:
            raise ValueError(f"Missing municipality: {municipality}")
        evacuees = int(city["Evacuees"].sum())
        for benchmark, people_per_toilet, _heading in BENCHMARKS:
            pooled = int(np.ceil(evacuees / people_per_toilet))
            sitewise = int(np.ceil(city["Evacuees"] / people_per_toilet).sum())
            increment = sitewise - pooled
            increment_percent = 100 * increment / pooled if pooled > 0 else np.nan
            rows.append(
                {
                    "Municipality": municipality,
                    "Benchmark": benchmark,
                    "People per Toilet": people_per_toilet,
                    "Shelters": len(city),
                    "Evacuees": evacuees,
                    "Pooled city": pooled,
                    "Sum of shelter-specific": sitewise,
                    "Increment": increment,
                    "Increment Percent": increment_percent,
                }
            )
    comparison = pd.DataFrame(rows)
    if len(comparison) != 4:
        raise ValueError("Expected two municipalities by two toilet benchmarks")
    if (comparison["Sum of shelter-specific"] < comparison["Pooled city"]).any():
        raise ValueError("Sitewise requirement cannot be lower than pooled requirement")
    return comparison


def main() -> None:
    frame = pd.read_parquet(SOURCE)
    required = {"Municipality", "Shelter Number", "Evacuees", "Scenario"}
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
    expected = {"八代市": (38, 1852), "熊本市": (15, 280)}
    for municipality, (shelters, evacuees) in expected.items():
        city = base.loc[base["Municipality"].eq(municipality)]
        if len(city) != shelters or int(city["Evacuees"].sum()) != evacuees:
            raise ValueError(f"Matched sample does not reproduce {municipality} totals")

    comparison = build_comparison(base)

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
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 5.7))
    fig.subplots_adjust(left=0.08, right=0.985, bottom=0.22, top=0.91, wspace=0.19)
    x_positions = np.arange(len(CITY_ORDER), dtype=float)
    bar_width = 0.32

    for panel_index, (ax, (benchmark, _people_per_toilet, heading)) in enumerate(
        zip(axes, BENCHMARKS, strict=True)
    ):
        panel = (
            comparison.loc[comparison["Benchmark"].eq(benchmark)]
            .set_index("Municipality")
            .loc[list(CITY_ORDER)]
        )
        pooled_bars = ax.bar(
            x_positions - bar_width / 2,
            panel["Pooled city"],
            width=bar_width,
            color=BAR_STYLE["Pooled city"],
            edgecolor="white",
            linewidth=0.7,
            zorder=3,
        )
        sitewise_bars = ax.bar(
            x_positions + bar_width / 2,
            panel["Sum of shelter-specific"],
            width=bar_width,
            color=BAR_STYLE["Sum of shelter-specific"],
            edgecolor="white",
            linewidth=0.7,
            zorder=3,
        )
        for bars in (pooled_bars, sitewise_bars):
            ax.bar_label(
                bars,
                labels=[f"{int(value)}" for value in bars.datavalues],
                padding=3,
                fontsize=8.3,
                fontweight="bold",
                color="#263746",
            )

        maximum = float(panel["Sum of shelter-specific"].max())
        for city_index, municipality in enumerate(CITY_ORDER):
            row = panel.loc[municipality]
            bracket_y = float(row["Sum of shelter-specific"]) + 0.11 * maximum
            x_left = city_index - bar_width / 2
            x_right = city_index + bar_width / 2
            ax.plot(
                [x_left, x_left, x_right, x_right],
                [bracket_y - 0.018 * maximum, bracket_y, bracket_y, bracket_y - 0.018 * maximum],
                color="#6F7A82",
                linewidth=0.7,
                zorder=4,
            )
            ax.text(
                city_index,
                bracket_y + 0.015 * maximum,
                f"+{int(row['Increment'])}  (+{row['Increment Percent']:.0f}%)",
                ha="center",
                va="bottom",
                fontsize=8.0,
                color="#44515B",
            )

        tick_labels = [
            f"{CITY_LABELS[municipality]}\n{int(panel.loc[municipality, 'Evacuees']):,} evacuees; "
            f"{int(panel.loc[municipality, 'Shelters'])} shelters"
            for municipality in CITY_ORDER
        ]
        ax.set_xticks(x_positions, tick_labels)
        ax.tick_params(axis="x", labelsize=8.2, length=0, pad=7)
        ax.tick_params(axis="y", labelsize=8.0, length=2.5, pad=2)
        ax.set_ylim(0, maximum * 1.30)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=6, integer=True, min_n_ticks=4))
        ax.grid(axis="y", color="#D9DDE1", linewidth=0.55, zorder=0)
        ax.set_ylabel("Required toilet units", fontsize=9.0, labelpad=7)
        add_panel_heading(ax, chr(ord("a") + panel_index), heading)

    legend_handles = [
        Line2D(
            [0],
            [0],
            marker="s",
            color="none",
            markerfacecolor=color,
            markeredgecolor="white",
            markeredgewidth=0.7,
            markersize=9,
            label=label,
        )
        for label, color in BAR_STYLE.items()
    ]
    fig.legend(
        handles=legend_handles,
        loc="lower center",
        ncol=2,
        frameon=False,
        fontsize=8.5,
        handletextpad=0.5,
        columnspacing=1.8,
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
