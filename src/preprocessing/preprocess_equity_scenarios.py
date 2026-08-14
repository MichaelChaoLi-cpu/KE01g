#!/usr/bin/env python3
"""Construct calibrated mesh and shelter equity-demand scenarios.

The script distinguishes observed counts, synthetic small-area estimates, and
scenario assumptions. It never treats residential composition as observed
shelter composition.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.path import Path as MplPath


ROOT = Path(__file__).resolve().parents[2]
MESH_SOURCE = ROOT / "data/raw/population/estat_2020_T001231_kumamoto/tblT001231E43.txt"
BOUNDARY_SOURCE = ROOT / "data/exp/scenario-planning/municipal_boundaries_2025.geojson"
SHELTER_MASTER = ROOT / "data/processed/kumamoto_prefecture_shelter_master_preprocessed.parquet"
KUMAMOTO_SHELTERS = ROOT / "data/raw/official_event/kumamoto_city/2026-08-12_1200_open_shelters.csv"
KUMAMOTO_DEPLOYMENT = ROOT / "data/raw/official_event/kumamoto_city/2026-08-12_temporary_toilet_deployment_actions.csv"
YATSUSHIRO_SHELTERS = ROOT / "data/raw/official_event/yatsushiro/2026-08-12_1200_open_shelters.csv"

MESH_OUTPUT = ROOT / "data/processed/mesh_equity_scenarios_preprocessed.parquet"
SHELTER_OUTPUT = ROOT / "data/processed/shelter_equity_scenarios_preprocessed.parquet"
SUMMARY_OUTPUT = ROOT / "data/exp/scenario-planning/shelter_equity_scenario_summary.csv"
QA_OUTPUT = ROOT / "data/exp/scenario-planning/qa_summary.json"


# City totals are administrative inputs, not event-period shelter counts.
CITY_INPUTS = {
    "熊本市": {
        "physical_disability_total": 26726.0,
        "long_term_care_total": 41944.0,
        "physical_disability_reference": "FY2024",
        "long_term_care_reference": "2025-03",
    },
    "八代市": {
        "physical_disability_total": 5296.0,
        "long_term_care_total": 8698.0,
        "physical_disability_reference": "FY2024",
        "long_term_care_reference": "FY2026 projection",
    },
}

# Relative allocation weights only. Calibration forces the allocated city
# totals to equal the administrative inputs above.
AGE_BINS = ["Age 0-14", "Age 15-64", "Age 65-74", "Age 75-84", "Age 85+"]
DISABILITY_WEIGHTS = np.array([0.6, 1.0, 1.8, 3.0, 4.5], dtype=float)
CARE_WEIGHTS = np.array([0.0, 0.0, 1.0, 4.0, 10.0], dtype=float)
OVERLAP_SCENARIOS = {
    "low": 1.0,   # complete overlap of the smaller group
    "base": 0.5,  # half of the smaller group overlaps
    "high": 0.0,  # no overlap
}


def normalize_name(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value))
    text = re.sub(r"[\s・･()（）「」\-ー]", "", text)
    text = re.sub(r"^(熊本市立|八代市立|市立)", "", text)
    return text


def mesh_center(mesh_code: str) -> tuple[float, float]:
    code = str(mesh_code)
    if len(code) < 8 or not code.isdigit():
        raise ValueError(f"Unsupported mesh code: {mesh_code}")
    lat = int(code[0:2]) * (2.0 / 3.0)
    lon = 100.0 + int(code[2:4])
    dlat = 2.0 / 3.0
    dlon = 1.0

    dlat /= 8.0
    dlon /= 8.0
    lat += int(code[4]) * dlat
    lon += int(code[5]) * dlon

    dlat /= 10.0
    dlon /= 10.0
    lat += int(code[6]) * dlat
    lon += int(code[7]) * dlon

    for digit in code[8:]:
        quadrant = int(digit)
        if quadrant not in (1, 2, 3, 4):
            raise ValueError(f"Unsupported subdivision digit in mesh code: {mesh_code}")
        dlat /= 2.0
        dlon /= 2.0
        if quadrant in (3, 4):
            lat += dlat
        if quadrant in (2, 4):
            lon += dlon
    return lat + dlat / 2.0, lon + dlon / 2.0


def points_in_polygon_geometry(points: np.ndarray, geometry: dict) -> np.ndarray:
    result = np.zeros(len(points), dtype=bool)
    polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    for polygon in polygons:
        exterior = np.asarray(polygon[0], dtype=float)
        xmin, ymin = exterior.min(axis=0)
        xmax, ymax = exterior.max(axis=0)
        candidates = np.flatnonzero(
            (points[:, 0] >= xmin)
            & (points[:, 0] <= xmax)
            & (points[:, 1] >= ymin)
            & (points[:, 1] <= ymax)
        )
        if len(candidates) == 0:
            continue
        inside = MplPath(exterior).contains_points(points[candidates], radius=1e-12)
        if len(polygon) > 1 and inside.any():
            inside_candidates = candidates[inside]
            for hole in polygon[1:]:
                hole_path = MplPath(np.asarray(hole, dtype=float))
                inside[inside] &= ~hole_path.contains_points(points[inside_candidates], radius=1e-12)
        result[candidates[inside]] = True
    return result


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.replace({"*": np.nan, "-": np.nan, "X": np.nan}), errors="coerce")


def reconstruct_age_sex(mesh: pd.DataFrame) -> pd.DataFrame:
    """Allocate disclosure-group age-sex totals back to constituent meshes."""
    code_map = {
        "Male Age 0-14": "T001231005",
        "Female Age 0-14": "T001231006",
        "Male Age 15-64": "T001231011",
        "Female Age 15-64": "T001231012",
        "Male Age 65+": "T001231020",
        "Female Age 65+": "T001231021",
        "Male Age 75+": "T001231023",
        "Female Age 75+": "T001231024",
        "Male Age 85+": "T001231026",
        "Female Age 85+": "T001231027",
    }
    mesh = mesh.copy()
    mesh["Disclosure Group Code"] = np.where(
        mesh["HTKSYORI"].eq("2"), mesh["HTKSAKI"], mesh["KEY_CODE"]
    )
    leaders = mesh.drop_duplicates("KEY_CODE").set_index("KEY_CODE")
    total_population = numeric(mesh["T001231001"]).fillna(0.0)
    for name, source_column in code_map.items():
        group_values = mesh["Disclosure Group Code"].map(numeric(leaders[source_column]))
        if group_values.isna().any():
            missing_group = mesh.loc[group_values.isna(), "Disclosure Group Code"].iloc[0]
            raise ValueError(f"Missing group value for {missing_group}, {source_column}")
        sex_column = "T001231002" if name.startswith("Male") else "T001231003"
        weights = numeric(mesh[sex_column]).fillna(0.0)
        weight_sums = weights.groupby(mesh["Disclosure Group Code"]).transform("sum")
        fallback_sums = total_population.groupby(mesh["Disclosure Group Code"]).transform("sum")
        use_fallback = weight_sums <= 0
        effective_weights = weights.where(~use_fallback, total_population)
        effective_sums = weight_sums.where(~use_fallback, fallback_sums)
        mesh[name] = np.where(
            effective_sums > 0,
            group_values * effective_weights / effective_sums,
            0.0,
        )
    for sex in ("Male", "Female"):
        mesh[f"{sex} Age 65-74"] = (mesh[f"{sex} Age 65+"] - mesh[f"{sex} Age 75+"]).clip(lower=0)
        mesh[f"{sex} Age 75-84"] = (mesh[f"{sex} Age 75+"] - mesh[f"{sex} Age 85+"]).clip(lower=0)
    return mesh


def bounded_allocate(total: float, weights: np.ndarray, capacity: np.ndarray) -> np.ndarray:
    allocation = np.zeros_like(weights, dtype=float)
    remaining = float(total)
    active = (weights > 0) & (capacity > 0)
    for _ in range(20):
        if remaining <= 1e-9 or not active.any():
            break
        share = remaining * weights[active] / weights[active].sum()
        room = capacity[active] - allocation[active]
        add = np.minimum(share, room)
        allocation[active] += add
        remaining = total - allocation.sum()
        active = active & (allocation < capacity - 1e-9)
    if remaining > 1e-5:
        raise ValueError(f"Unable to allocate calibrated total; unallocated={remaining}")
    return allocation


def city_mask(mesh: pd.DataFrame) -> pd.Series:
    with BOUNDARY_SOURCE.open(encoding="utf-8") as handle:
        boundary_data = json.load(handle)
    points = mesh[["Longitude", "Latitude"]].to_numpy(dtype=float)
    assigned = pd.Series(pd.NA, index=mesh.index, dtype="string")
    for feature in boundary_data["features"]:
        municipality = feature["properties"]["municipality"]
        mask = points_in_polygon_geometry(points, feature["geometry"])
        assigned.loc[mask] = municipality
    return assigned


def build_mesh_scenarios() -> pd.DataFrame:
    raw = pd.read_csv(MESH_SOURCE, encoding="cp932", dtype=str, skiprows=[1])
    raw = reconstruct_age_sex(raw)
    coords = [mesh_center(code) for code in raw["KEY_CODE"]]
    raw["Latitude"] = [x[0] for x in coords]
    raw["Longitude"] = [x[1] for x in coords]
    raw["Municipality"] = city_mask(raw)
    raw = raw[raw["Municipality"].notna()].copy()
    raw["Total Population"] = numeric(raw["T001231001"]).fillna(0.0)
    raw["Male Population"] = numeric(raw["T001231002"]).fillna(0.0)
    raw["Female Population"] = numeric(raw["T001231003"]).fillna(0.0)
    raw["Female Share"] = np.where(
        raw["Total Population"] > 0,
        raw["Female Population"] / raw["Total Population"],
        np.nan,
    )
    raw["Disclosure Group Aggregated"] = raw["HTKSYORI"].isin(["1", "2"])

    for sex in ("Male", "Female"):
        raw[f"{sex} Age 0-14"] = raw[f"{sex} Age 0-14"].astype(float)
        raw[f"{sex} Age 15-64"] = raw[f"{sex} Age 15-64"].astype(float)
        raw[f"{sex} Age 65-74"] = raw[f"{sex} Age 65-74"].astype(float)
        raw[f"{sex} Age 75-84"] = raw[f"{sex} Age 75-84"].astype(float)
        raw[f"{sex} Age 85+"] = raw[f"{sex} Age 85+"].astype(float)

    scenario_frames: list[pd.DataFrame] = []
    for municipality, city_frame in raw.groupby("Municipality", sort=True):
        city_frame = city_frame.copy()
        city_input = CITY_INPUTS[municipality]
        male_age = city_frame[[f"Male {x}" for x in AGE_BINS]].to_numpy(dtype=float)
        female_age = city_frame[[f"Female {x}" for x in AGE_BINS]].to_numpy(dtype=float)
        male_capacity = city_frame["Male Population"].to_numpy(dtype=float)
        female_capacity = city_frame["Female Population"].to_numpy(dtype=float)

        disability_slot_weights = np.concatenate(
            [(male_age * DISABILITY_WEIGHTS).sum(axis=1), (female_age * DISABILITY_WEIGHTS).sum(axis=1)]
        )
        care_slot_weights = np.concatenate(
            [(male_age * CARE_WEIGHTS).sum(axis=1), (female_age * CARE_WEIGHTS).sum(axis=1)]
        )
        slot_capacity = np.concatenate([male_capacity, female_capacity])
        disability = bounded_allocate(
            city_input["physical_disability_total"], disability_slot_weights, slot_capacity
        )
        care = bounded_allocate(city_input["long_term_care_total"], care_slot_weights, slot_capacity)
        n = len(city_frame)
        d_male, d_female = disability[:n], disability[n:]
        c_male, c_female = care[:n], care[n:]

        for scenario, overlap_fraction in OVERLAP_SCENARIOS.items():
            frame = city_frame.copy()
            support_male = np.minimum(
                male_capacity,
                d_male + c_male - overlap_fraction * np.minimum(d_male, c_male),
            )
            support_female = np.minimum(
                female_capacity,
                d_female + c_female - overlap_fraction * np.minimum(d_female, c_female),
            )
            frame["Scenario"] = scenario
            frame["Estimated Physical Disability Population"] = d_male + d_female
            frame["Estimated Female Physical Disability Population"] = d_female
            frame["Estimated Long-Term Care Population"] = c_male + c_female
            frame["Estimated Female Long-Term Care Population"] = c_female
            frame["Estimated Functional Support Population"] = support_male + support_female
            frame["Estimated Female Functional Support Population"] = support_female
            frame["Functional Support Share"] = np.where(
                frame["Total Population"] > 0,
                frame["Estimated Functional Support Population"] / frame["Total Population"],
                np.nan,
            )
            frame["Physical Disability Reference"] = city_input["physical_disability_reference"]
            frame["Long-Term Care Reference"] = city_input["long_term_care_reference"]
            scenario_frames.append(frame)

    result = pd.concat(scenario_frames, ignore_index=True)
    keep = [
        "KEY_CODE",
        "Municipality",
        "Latitude",
        "Longitude",
        "Total Population",
        "Male Population",
        "Female Population",
        "Female Share",
        "Male Age 0-14",
        "Female Age 0-14",
        "Male Age 15-64",
        "Female Age 15-64",
        "Male Age 65-74",
        "Female Age 65-74",
        "Male Age 75-84",
        "Female Age 75-84",
        "Male Age 85+",
        "Female Age 85+",
        "Disclosure Group Code",
        "Disclosure Group Aggregated",
        "Scenario",
        "Estimated Physical Disability Population",
        "Estimated Female Physical Disability Population",
        "Estimated Long-Term Care Population",
        "Estimated Female Long-Term Care Population",
        "Estimated Functional Support Population",
        "Estimated Female Functional Support Population",
        "Functional Support Share",
        "Physical Disability Reference",
        "Long-Term Care Reference",
    ]
    result = result[keep].rename(columns={"KEY_CODE": "Mesh Code"})
    return result


def resolve_shelter_locations() -> pd.DataFrame:
    master = pd.read_parquet(SHELTER_MASTER)
    master["Normalized Name"] = master["Shelter Name"].map(normalize_name)
    rows: list[pd.DataFrame] = []

    kumamoto = pd.read_csv(KUMAMOTO_SHELTERS)
    kumamoto["Municipality"] = "熊本市"
    kumamoto["District or Ward"] = kumamoto["ward"]
    kumamoto["District"] = pd.NA
    kumamoto["Ward"] = kumamoto["ward"]
    kumamoto["Shelter Number"] = kumamoto["shelter_number"]
    kumamoto["Shelter Name"] = kumamoto["shelter_name"]
    kumamoto["Evacuees"] = kumamoto["evacuee_people"]
    kumamoto["Evacuee Households"] = kumamoto["evacuee_households"]
    kumamoto["Observation Time"] = kumamoto["observation_time"]
    kumamoto["Water Status"] = pd.NA
    kumamoto["Toilet Cars"] = pd.NA
    deployment = pd.read_csv(KUMAMOTO_DEPLOYMENT)
    installed = deployment[deployment["deployment_status"].eq("installed")].copy()
    installed["Normalized Name"] = installed["shelter_name"].map(normalize_name)
    deployment_map = installed.set_index("Normalized Name")["reported_units"].to_dict()
    kumamoto["Temporary Toilets Installed"] = kumamoto["Shelter Name"].map(
        lambda x: deployment_map.get(normalize_name(x), np.nan)
    )

    k_master = master[master["Municipality"].eq("熊本市")].drop_duplicates("Normalized Name")
    k_lookup = k_master.set_index("Normalized Name")
    k_coords = []
    for name in kumamoto["Shelter Name"]:
        key = normalize_name(name)
        if key not in k_lookup.index:
            raise ValueError(f"Kumamoto shelter location not matched: {name}")
        match = k_lookup.loc[key]
        k_coords.append((float(match["Latitude"]), float(match["Longitude"])))
    kumamoto["Latitude"] = [x[0] for x in k_coords]
    kumamoto["Longitude"] = [x[1] for x in k_coords]
    kumamoto["Location Resolution"] = "exact shelter master match"
    kumamoto["Catchment Method"] = "nearest open shelter"
    rows.append(kumamoto)

    yatsushiro = pd.read_csv(YATSUSHIRO_SHELTERS)
    yatsushiro["Municipality"] = "八代市"
    yatsushiro["District or Ward"] = yatsushiro["district"]
    yatsushiro["District"] = yatsushiro["district"]
    yatsushiro["Ward"] = pd.NA
    yatsushiro["Shelter Number"] = yatsushiro["shelter_number"]
    yatsushiro["Shelter Name"] = yatsushiro["shelter_name"]
    yatsushiro["Evacuees"] = yatsushiro["evacuee_people"]
    yatsushiro["Evacuee Households"] = yatsushiro["evacuee_households"]
    yatsushiro["Observation Time"] = yatsushiro["observation_time"]
    yatsushiro["Water Status"] = yatsushiro["water_status_symbol"]
    yatsushiro["Temporary Toilets Installed"] = yatsushiro["temporary_toilets_installed"]
    yatsushiro["Toilet Cars"] = yatsushiro["toilet_cars"]

    y_master = master[master["Municipality"].eq("八代市")].copy()
    y_lookup = y_master.drop_duplicates("Normalized Name").set_index("Normalized Name")
    exact_by_district: dict[str, list[tuple[float, float]]] = {}
    exact_locations: dict[str, tuple[float, float]] = {}
    for _, row in yatsushiro.iterrows():
        key = normalize_name(row["Shelter Name"])
        if key in y_lookup.index:
            match = y_lookup.loc[key]
            coords = (float(match["Latitude"]), float(match["Longitude"]))
            exact_locations[key] = coords
            exact_by_district.setdefault(row["District or Ward"], []).append(coords)

    district_anchors: dict[str, tuple[float, float]] = {}
    for district in yatsushiro["District or Ward"].unique():
        candidates = exact_by_district.get(district, [])
        if not candidates:
            fallback = y_master[y_master["Normalized Name"].str.contains(normalize_name(district), regex=False)]
            candidates = list(zip(fallback["Latitude"].astype(float), fallback["Longitude"].astype(float)))
        if not candidates:
            raise ValueError(f"No district anchor available for {district}")
        district_anchors[district] = (
            float(np.mean([x[0] for x in candidates])),
            float(np.mean([x[1] for x in candidates])),
        )

    y_coords = []
    y_resolution = []
    for _, row in yatsushiro.iterrows():
        key = normalize_name(row["Shelter Name"])
        if key in exact_locations:
            y_coords.append(exact_locations[key])
            y_resolution.append("exact shelter master match")
        else:
            y_coords.append(district_anchors[row["District or Ward"]])
            y_resolution.append("district anchor fallback")
    yatsushiro["Latitude"] = [x[0] for x in y_coords]
    yatsushiro["Longitude"] = [x[1] for x in y_coords]
    yatsushiro["Location Resolution"] = y_resolution
    yatsushiro["Catchment Method"] = "nearest district anchor"
    rows.append(yatsushiro)

    keep = [
        "Municipality",
        "Shelter Number",
        "Shelter Name",
        "District or Ward",
        "District",
        "Ward",
        "Latitude",
        "Longitude",
        "Location Resolution",
        "Catchment Method",
        "Evacuee Households",
        "Evacuees",
        "Water Status",
        "Temporary Toilets Installed",
        "Toilet Cars",
        "Observation Time",
    ]
    return pd.concat([x[keep] for x in rows], ignore_index=True)


def nearest_labels(points: np.ndarray, anchors: np.ndarray, labels: list[str]) -> np.ndarray:
    lat0 = np.radians(points[:, 1].mean())
    dx = (points[:, None, 0] - anchors[None, :, 0]) * math.cos(lat0)
    dy = points[:, None, 1] - anchors[None, :, 1]
    nearest = np.argmin(dx * dx + dy * dy, axis=1)
    return np.asarray(labels, dtype=object)[nearest]


def build_shelter_scenarios(mesh: pd.DataFrame) -> pd.DataFrame:
    shelters = resolve_shelter_locations()
    output_frames: list[pd.DataFrame] = []
    for municipality, city_shelters in shelters.groupby("Municipality", sort=True):
        city_shelters = city_shelters.copy()
        if municipality == "熊本市":
            anchor_table = city_shelters[["Shelter Number", "Longitude", "Latitude"]].drop_duplicates()
            anchor_labels = anchor_table["Shelter Number"].astype(str).tolist()
            shelter_label_column = "Shelter Number"
        else:
            anchor_table = (
                city_shelters.groupby("District or Ward", as_index=False)[["Longitude", "Latitude"]]
                .mean()
            )
            anchor_labels = anchor_table["District or Ward"].astype(str).tolist()
            shelter_label_column = "District or Ward"
        anchors = anchor_table[["Longitude", "Latitude"]].to_numpy(dtype=float)

        for scenario, city_mesh in mesh[mesh["Municipality"].eq(municipality)].groupby("Scenario"):
            city_mesh = city_mesh.copy()
            points = city_mesh[["Longitude", "Latitude"]].to_numpy(dtype=float)
            city_mesh["Catchment Label"] = nearest_labels(points, anchors, anchor_labels)
            grouped = city_mesh.groupby("Catchment Label", as_index=True).agg(
                **{
                    "Catchment Residential Population": ("Total Population", "sum"),
                    "Catchment Female Population": ("Female Population", "sum"),
                    "Catchment Estimated Physical Disability Population": (
                        "Estimated Physical Disability Population",
                        "sum",
                    ),
                    "Catchment Estimated Long-Term Care Population": (
                        "Estimated Long-Term Care Population",
                        "sum",
                    ),
                    "Catchment Estimated Functional Support Population": (
                        "Estimated Functional Support Population",
                        "sum",
                    ),
                    "Catchment Estimated Female Functional Support Population": (
                        "Estimated Female Functional Support Population",
                        "sum",
                    ),
                }
            )
            frame = city_shelters.copy()
            frame["Scenario"] = scenario
            lookup_labels = frame[shelter_label_column].astype(str)
            for column in grouped.columns:
                frame[column] = lookup_labels.map(grouped[column])
            denom = frame["Catchment Residential Population"]
            frame["Catchment Female Share"] = frame["Catchment Female Population"] / denom
            frame["Catchment Functional Support Share"] = (
                frame["Catchment Estimated Functional Support Population"] / denom
            )
            frame["Estimated Female Evacuees"] = frame["Evacuees"] * frame["Catchment Female Share"]
            frame["Estimated Functional Support Evacuees"] = (
                frame["Evacuees"] * frame["Catchment Functional Support Share"]
            )
            frame["Estimated Female Functional Support Evacuees"] = (
                frame["Evacuees"]
                * frame["Catchment Estimated Female Functional Support Population"]
                / denom
            )
            for label, people_per_unit in (("Initial", 50), ("Prolonged", 20)):
                total_requirement = np.ceil(frame["Evacuees"] / people_per_unit).astype(int)
                total_requirement = np.where(frame["Evacuees"] > 0, total_requirement, 0)
                frame[f"{label} Total Toilet Requirement"] = total_requirement
                women_requirement = np.ceil(0.75 * total_requirement).astype(int)
                frame[f"{label} Women Toilet Allocation"] = women_requirement
                frame[f"{label} Men Toilet Allocation"] = total_requirement - women_requirement
                accessible_requirement = np.ceil(
                    frame["Estimated Functional Support Evacuees"] / people_per_unit
                ).astype(int)
                accessible_requirement = np.where(
                    frame["Estimated Functional Support Evacuees"] > 0,
                    accessible_requirement,
                    0,
                )
                frame[f"{label} Accessible Unit Parity Screen"] = accessible_requirement
            frame["Evidence Status"] = "scenario estimate, not observed shelter composition"
            output_frames.append(frame)
    result = pd.concat(output_frames, ignore_index=True)
    for column in ("District", "Ward", "Location Resolution"):
        result[column] = result[column].astype("string").str.strip().astype("category")
    scenario_order = pd.Categorical(result["Scenario"], ["low", "base", "high"], ordered=True)
    result = result.assign(_scenario_order=scenario_order).sort_values(
        ["Municipality", "Shelter Number", "_scenario_order"]
    ).drop(columns="_scenario_order")
    return result.reset_index(drop=True)


def write_summary(mesh: pd.DataFrame, shelters: pd.DataFrame) -> None:
    summary = (
        shelters.groupby(["Municipality", "Scenario"], as_index=False)
        .agg(
            Shelters=("Shelter Name", "count"),
            Evacuees=("Evacuees", "sum"),
            Estimated_Female_Evacuees=("Estimated Female Evacuees", "sum"),
            Estimated_Functional_Support_Evacuees=("Estimated Functional Support Evacuees", "sum"),
            Estimated_Female_Functional_Support_Evacuees=(
                "Estimated Female Functional Support Evacuees",
                "sum",
            ),
            Prolonged_Total_Toilet_Requirement=("Prolonged Total Toilet Requirement", "sum"),
            Prolonged_Accessible_Unit_Parity_Screen=("Prolonged Accessible Unit Parity Screen", "sum"),
        )
    )
    summary.to_csv(SUMMARY_OUTPUT, index=False)

    qa = {
        "mesh_rows": int(len(mesh)),
        "unique_meshes": int(mesh["Mesh Code"].nunique()),
        "shelter_scenario_rows": int(len(shelters)),
        "shelters": int(shelters[["Municipality", "Shelter Number"]].drop_duplicates().shape[0]),
        "mesh_population_by_city": {
            k: float(v)
            for k, v in mesh[mesh["Scenario"].eq("base")]
            .groupby("Municipality")["Total Population"]
            .sum()
            .items()
        },
        "published_2020_census_population": {"熊本市": 738865.0, "八代市": 123067.0},
        "mesh_boundary_population_difference": {
            municipality: float(
                mesh[mesh["Scenario"].eq("base") & mesh["Municipality"].eq(municipality)][
                    "Total Population"
                ].sum()
                - published
            )
            for municipality, published in {"熊本市": 738865.0, "八代市": 123067.0}.items()
        },
        "physical_disability_calibration": {
            k: float(v)
            for k, v in mesh[mesh["Scenario"].eq("base")]
            .groupby("Municipality")["Estimated Physical Disability Population"]
            .sum()
            .items()
        },
        "long_term_care_calibration": {
            k: float(v)
            for k, v in mesh[mesh["Scenario"].eq("base")]
            .groupby("Municipality")["Estimated Long-Term Care Population"]
            .sum()
            .items()
        },
        "location_resolution_counts": {
            str(k): int(v)
            for k, v in shelters.drop_duplicates(["Municipality", "Shelter Number"])[
                "Location Resolution"
            ].value_counts().items()
        },
        "scenario_monotonic_by_shelter": bool(
            shelters.pivot_table(
                index=["Municipality", "Shelter Number"],
                columns="Scenario",
                values="Estimated Functional Support Evacuees",
            )
            .eval("low <= base <= high")
            .all()
        ),
    }
    QA_OUTPUT.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    for source in (MESH_SOURCE, BOUNDARY_SOURCE, SHELTER_MASTER, KUMAMOTO_SHELTERS, YATSUSHIRO_SHELTERS):
        if not source.exists():
            raise FileNotFoundError(source)
    MESH_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    mesh = build_mesh_scenarios()
    shelters = build_shelter_scenarios(mesh)
    mesh.to_parquet(MESH_OUTPUT, index=False)
    shelters.to_parquet(SHELTER_OUTPUT, index=False)
    write_summary(mesh, shelters)
    print(f"wrote {MESH_OUTPUT.relative_to(ROOT)}: {mesh.shape[0]} rows x {mesh.shape[1]} columns")
    print(f"wrote {SHELTER_OUTPUT.relative_to(ROOT)}: {shelters.shape[0]} rows x {shelters.shape[1]} columns")
    print(f"wrote {SUMMARY_OUTPUT.relative_to(ROOT)}")
    print(f"wrote {QA_OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
