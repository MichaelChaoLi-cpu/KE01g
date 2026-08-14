#!/usr/bin/env python3
"""Build municipality-level sex and functional-support planning scenarios.

Residential composition is used only as a scenario input. The resulting
estimated evacuee counts are not observed sex- or need-disaggregated shelter
counts.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from shapely import from_wkb, intersects_xy


ROOT = Path(__file__).resolve().parents[2]
MESH_SOURCE = ROOT / "data/raw/population/estat_2020_T001231_kumamoto/tblT001231E43.txt"
BOUNDARY_SOURCE = ROOT / "data/exp/scenario-planning/kumamoto_prefecture_administrative_areas_2025_preprocessed.parquet"
DEMAND_SOURCE = ROOT / "data/processed/kumamoto_prefecture_municipality_shelter_totals_2026-08-12_1400_preprocessed.parquet"
LTC_TOTAL_SOURCE = ROOT / "data/processed/mhlw_ltc_2026_04_total_preprocessed.parquet"
LTC_FEMALE_SOURCE = ROOT / "data/processed/mhlw_ltc_2026_04_female_preprocessed.parquet"
OUTPUT = ROOT / "data/processed/municipality_equity_scenarios_preprocessed.parquet"


def mesh_center(mesh_code: str) -> tuple[float, float]:
    code = str(mesh_code)
    if len(code) < 8 or not code.isdigit():
        raise ValueError(f"Unsupported mesh code: {mesh_code}")
    latitude = int(code[0:2]) * (2.0 / 3.0)
    longitude = 100.0 + int(code[2:4])
    dlat, dlon = 2.0 / 3.0, 1.0
    dlat, dlon = dlat / 8.0, dlon / 8.0
    latitude += int(code[4]) * dlat
    longitude += int(code[5]) * dlon
    dlat, dlon = dlat / 10.0, dlon / 10.0
    latitude += int(code[6]) * dlat
    longitude += int(code[7]) * dlon
    for digit in code[8:]:
        quadrant = int(digit)
        if quadrant not in (1, 2, 3, 4):
            raise ValueError(f"Unsupported subdivision digit: {mesh_code}")
        dlat, dlon = dlat / 2.0, dlon / 2.0
        if quadrant in (3, 4):
            latitude += dlat
        if quadrant in (2, 4):
            longitude += dlon
    return latitude + dlat / 2.0, longitude + dlon / 2.0


def aggregate_residential_population(target_names: set[str]) -> pd.DataFrame:
    mesh = pd.read_csv(
        MESH_SOURCE,
        encoding="cp932",
        dtype=str,
        skiprows=[1],
        usecols=["KEY_CODE", "T001231001", "T001231002", "T001231003"],
    )
    centers = [mesh_center(code) for code in mesh["KEY_CODE"]]
    latitude = np.asarray([point[0] for point in centers])
    longitude = np.asarray([point[1] for point in centers])
    assigned = np.full(len(mesh), None, dtype=object)

    boundaries = pd.read_parquet(BOUNDARY_SOURCE)
    boundaries = boundaries.loc[boundaries["Municipality Name"].isin(target_names)].copy()
    for municipality, rows in boundaries.groupby("Municipality Name", sort=False):
        municipality_mask = np.zeros(len(mesh), dtype=bool)
        for geometry_wkb in rows["Geometry"]:
            municipality_mask |= intersects_xy(from_wkb(geometry_wkb), longitude, latitude)
        conflicting = municipality_mask & pd.notna(assigned) & (assigned != municipality)
        if conflicting.any():
            raise ValueError(f"Overlapping municipality assignment for {municipality}")
        assigned[municipality_mask] = municipality

    mesh["Municipality (Japanese)"] = assigned
    mesh = mesh.loc[mesh["Municipality (Japanese)"].notna()].copy()
    numeric_map = {
        "T001231001": "Residential Population",
        "T001231002": "Residential Male Population",
        "T001231003": "Residential Female Population",
    }
    for source, readable in numeric_map.items():
        mesh[readable] = pd.to_numeric(mesh[source], errors="coerce")
    if mesh[list(numeric_map.values())].isna().any().any():
        raise ValueError("Unexpected missing values in census sex totals")
    result = (
        mesh.groupby("Municipality (Japanese)", as_index=False)[list(numeric_map.values())]
        .sum()
    )
    missing = target_names.difference(result["Municipality (Japanese)"])
    if missing:
        raise ValueError(f"Municipalities not assigned from mesh: {sorted(missing)}")
    result["Municipality Female Share"] = (
        result["Residential Female Population"] / result["Residential Population"]
    )
    return result


def ltc_fields(path: Path, prefix: str) -> pd.DataFrame:
    fields = [
        "Municipality",
        "Higher Assistance Certified Population",
        "Care Certified Population",
        "Support or Care Certified Population",
    ]
    frame = pd.read_parquet(path, columns=fields)
    frame["Municipality"] = frame["Municipality"].astype("string")
    return frame.rename(
        columns={
            "Municipality": "Municipality (Japanese)",
            **{field: f"{prefix} {field}" for field in fields[1:]},
        }
    )


def main() -> None:
    demand = pd.read_parquet(DEMAND_SOURCE)
    demand["Municipality (Japanese)"] = demand["Municipality (Japanese)"].astype("string")
    target_names = set(demand["Municipality (Japanese)"])
    context = demand.merge(
        aggregate_residential_population(target_names),
        on="Municipality (Japanese)",
        how="left",
        validate="one_to_one",
    )
    context = context.merge(
        ltc_fields(LTC_TOTAL_SOURCE, "Total"),
        on="Municipality (Japanese)",
        how="left",
        validate="one_to_one",
    ).merge(
        ltc_fields(LTC_FEMALE_SOURCE, "Female"),
        on="Municipality (Japanese)",
        how="left",
        validate="one_to_one",
    )
    if len(context) != 11 or context.isna().any().any():
        raise ValueError("The municipality equity context did not match all 11 records")

    scenario_fields = {
        "Narrow": "Higher Assistance Certified Population",
        "Core": "Care Certified Population",
        "Broad": "Support or Care Certified Population",
    }
    frames = []
    for scenario, field in scenario_fields.items():
        frame = context.copy()
        frame["Functional Support Scenario"] = scenario
        frame["Municipality Functional Support Population"] = frame[f"Total {field}"]
        frame["Municipality Female Functional Support Population"] = frame[f"Female {field}"]
        frame["Municipality Functional Support Share"] = (
            frame["Municipality Functional Support Population"]
            / frame["Residential Population"]
        )
        frame["Municipality Female Functional Support Share"] = (
            frame["Municipality Female Functional Support Population"]
            / frame["Residential Population"]
        )
        frame["Estimated Female Evacuees"] = (
            frame["Evacuees"] * frame["Municipality Female Share"]
        )
        frame["Estimated Functional Support Evacuees"] = (
            frame["Evacuees"] * frame["Municipality Functional Support Share"]
        )
        frame["Estimated Female Functional Support Evacuees"] = (
            frame["Evacuees"]
            * frame["Municipality Female Functional Support Share"]
        )
        frames.append(frame)

    output = pd.concat(frames, ignore_index=True)
    output["Functional Support Scenario"] = pd.Categorical(
        output["Functional Support Scenario"],
        categories=["Narrow", "Core", "Broad"],
        ordered=True,
    )
    keep = [
        "Municipality Observation Time",
        "Municipality Code",
        "Municipality (Japanese)",
        "Municipality",
        "Open Shelter Count",
        "Evacuees",
        "Municipality Evidence Tier",
        "Residential Population",
        "Residential Male Population",
        "Residential Female Population",
        "Municipality Female Share",
        "Functional Support Scenario",
        "Municipality Functional Support Population",
        "Municipality Female Functional Support Population",
        "Municipality Functional Support Share",
        "Municipality Female Functional Support Share",
        "Estimated Female Evacuees",
        "Estimated Functional Support Evacuees",
        "Estimated Female Functional Support Evacuees",
    ]
    output = output[keep].sort_values(
        ["Functional Support Scenario", "Evacuees", "Municipality"],
        ascending=[True, False, True],
        ignore_index=True,
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(OUTPUT, index=False, engine="pyarrow")
    print(f"Saved {len(output):,} rows x {len(output.columns)} cols -> {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
