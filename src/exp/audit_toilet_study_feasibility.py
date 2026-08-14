#!/usr/bin/env python3
"""Create a conservative toilet-capacity screening from the current Yatsushiro table.

This is an evidence audit, not a final adequacy estimate. It intentionally excludes
fixed toilets and toilet-car stalls because the official source does not report them.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/raw/official_event/yatsushiro/2026-08-13_0600_open_shelters.csv"
LEGACY_SOURCE = ROOT / "data/raw/reused_local/KE01d/yatsushiro_shelters_2026-08-06_1800.csv"
OUTPUT_DIR = ROOT / "data/exp/data-source-audit"
OUTPUT_TABLE = OUTPUT_DIR / "yatsushiro_temporary_toilet_screen.csv"
OUTPUT_SUMMARY = OUTPUT_DIR / "yatsushiro_temporary_toilet_screen_summary.json"
OUTPUT_SNAPSHOTS = OUTPUT_DIR / "yatsushiro_snapshot_comparison.csv"


def integer(row: dict[str, str], key: str) -> int:
    return int(row[key])


def main() -> None:
    with SOURCE.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))

    output_rows: list[dict[str, object]] = []
    for row in rows:
        evacuees = integer(row, "evacuee_people")
        temporary = integer(row, "temporary_toilets_installed")
        initial_requirement = math.ceil(evacuees / 50)
        long_requirement = math.ceil(evacuees / 20)
        output_rows.append(
            {
                "Shelter Number": integer(row, "shelter_number"),
                "Shelter Name": row["shelter_name"],
                "District": row["district"],
                "Evacuees": evacuees,
                "Water Status": {
                    "〇": "available",
                    "△": "partially available",
                    "×": "unavailable",
                }[row["water_status_symbol"]],
                "Temporary Toilets Installed": temporary,
                "Toilet Cars": integer(row, "toilet_cars"),
                "Initial Total Toilet Requirement": initial_requirement,
                "Long-Duration Total Toilet Requirement": long_requirement,
                "Temporary-Toilet-Only Long-Duration Shortfall": max(
                    0, long_requirement - temporary
                ),
                "Temporary Toilet Screen Status": (
                    "no_evacuated_users"
                    if evacuees == 0
                    else "temporary_count_below_long_duration_requirement"
                    if temporary < long_requirement
                    else "temporary_count_meets_long_duration_quantity_only"
                ),
                "Interpretation": (
                    "Screen only: fixed stalls, toilet-car stalls, sex allocation, "
                    "accessibility, sewer operability, hygiene, safety, and waste "
                    "handling are not observed."
                ),
            }
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_TABLE.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)

    occupied = [row for row in output_rows if row["Evacuees"] > 0]
    summary = {
        "observation_time": "2026-08-13T06:00:00+09:00",
        "shelters_reported": len(output_rows),
        "occupied_shelters": len(occupied),
        "evacuees": sum(int(row["Evacuees"]) for row in output_rows),
        "temporary_toilets_installed": sum(
            int(row["Temporary Toilets Installed"]) for row in output_rows
        ),
        "toilet_cars": sum(int(row["Toilet Cars"]) for row in output_rows),
        "aggregate_initial_requirement": math.ceil(
            sum(int(row["Evacuees"]) for row in output_rows) / 50
        ),
        "aggregate_long_duration_requirement": math.ceil(
            sum(int(row["Evacuees"]) for row in output_rows) / 20
        ),
        "sitewise_initial_requirement": sum(
            int(row["Initial Total Toilet Requirement"]) for row in output_rows
        ),
        "sitewise_long_duration_requirement": sum(
            int(row["Long-Duration Total Toilet Requirement"]) for row in output_rows
        ),
        "occupied_shelters_below_long_duration_requirement_using_temporary_toilets_only": sum(
            row["Temporary Toilet Screen Status"]
            == "temporary_count_below_long_duration_requirement"
            for row in occupied
        ),
        "evacuees_at_those_shelters": sum(
            int(row["Evacuees"])
            for row in occupied
            if row["Temporary Toilet Screen Status"]
            == "temporary_count_below_long_duration_requirement"
        ),
        "occupied_shelters_with_no_temporary_toilet_or_toilet_car": sum(
            int(row["Temporary Toilets Installed"]) == 0
            and int(row["Toilet Cars"]) == 0
            for row in occupied
        ),
        "evacuees_at_shelters_with_no_temporary_toilet_or_toilet_car": sum(
            int(row["Evacuees"])
            for row in occupied
            if int(row["Temporary Toilets Installed"]) == 0
            and int(row["Toilet Cars"]) == 0
        ),
        "evacuees_at_shelters_with_unavailable_water": sum(
            int(row["Evacuees"])
            for row in output_rows
            if row["Water Status"] == "unavailable"
        ),
        "evacuees_at_shelters_with_partially_available_water": sum(
            int(row["Evacuees"])
            for row in output_rows
            if row["Water Status"] == "partially available"
        ),
        "interpretation": (
            "Temporary-toilet-only screening cannot establish total or gender-specific "
            "functional capacity. Toilet-car stall counts and all fixed-toilet fields are absent."
        ),
    }
    OUTPUT_SUMMARY.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    with LEGACY_SOURCE.open(encoding="utf-8-sig", newline="") as stream:
        legacy_rows = list(csv.DictReader(stream))

    snapshot_rows = [
        {
            "observation_time": "2026-08-06T18:00:00+09:00",
            "shelters": len(legacy_rows),
            "evacuee_people": sum(int(row["evacuee_people"] or 0) for row in legacy_rows),
            "temporary_toilets_installed": sum(int(row["toilet_count"] or 0) for row in legacy_rows),
            "toilet_cars": sum(int(row["portable_toilet_count"] or 0) for row in legacy_rows),
            "water_available": sum(row["water_status_symbol"] == "○" for row in legacy_rows),
            "water_partial": sum(row["water_status_symbol"] == "△" for row in legacy_rows),
            "water_unavailable": sum(row["water_status_symbol"] == "×" for row in legacy_rows),
            "source_scope_note": "Legacy official Yatsushiro snapshot copied from KE01d; Toilet Count means temporary toilets installed and Portable Toilet Count means toilet cars.",
        },
        {
            "observation_time": "2026-08-13T06:00:00+09:00",
            "shelters": len(rows),
            "evacuee_people": sum(integer(row, "evacuee_people") for row in rows),
            "temporary_toilets_installed": sum(integer(row, "temporary_toilets_installed") for row in rows),
            "toilet_cars": sum(integer(row, "toilet_cars") for row in rows),
            "water_available": sum(row["water_status_symbol"] == "〇" for row in rows),
            "water_partial": sum(row["water_status_symbol"] == "△" for row in rows),
            "water_unavailable": sum(row["water_status_symbol"] == "×" for row in rows),
            "source_scope_note": "Current official Yatsushiro snapshot transcribed and total-checked against the source PDF.",
        },
    ]
    with OUTPUT_SNAPSHOTS.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(snapshot_rows[0]))
        writer.writeheader()
        writer.writerows(snapshot_rows)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
