#!/usr/bin/env python3
"""Municipality-Level Observed and Scenario Demand Summary.

Plan: Report one row per municipality and functional-support scope scenario,
including observed demand, synthetic equity demand, standards-based toilet
requirements, evidence resolution, and interpretation boundaries.
Framework: Section 5 municipality screening and evidence separation; Section 6
municipality demand and accessible-parity sensitivity equations; Section 7
common-snapshot and scope-monotonicity workflow. Synthetic subgroup values are
not observed shelter composition or verified functional-capacity gaps.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.table import Table, TableStyleInfo


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/processed/municipality_equity_scenarios_preprocessed.parquet"
OUTPUT = (
    ROOT
    / "data/results/tables/"
    "Table_municipality_level_observed_and_scenario_demand_summary.xlsx"
)

SCENARIO_ORDER = ("Narrow", "Core", "Broad")
INTERPRETATION_BOUNDARY = (
    "Synthetic municipal screen; not observed composition, accessibility "
    "compliance, or verified capacity."
)
HEADERS = (
    "Municipality",
    "Functional Support Scenario",
    "Open Shelter Count",
    "Evacuees",
    "Municipality Estimated Female Evacuees",
    "Municipality Estimated Functional Support Evacuees",
    "Municipality Estimated Female Functional Support Evacuees",
    "Initial Total Toilet Requirement",
    "Prolonged Total Toilet Requirement",
    "Initial Accessible Unit Parity Screen",
    "Prolonged Accessible Unit Parity Screen",
    "Municipality Observation Time",
    "Municipality Evidence Tier",
)


def prepare_table(frame: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        "Estimated Female Evacuees": "Municipality Estimated Female Evacuees",
        "Estimated Functional Support Evacuees": (
            "Municipality Estimated Functional Support Evacuees"
        ),
        "Estimated Female Functional Support Evacuees": (
            "Municipality Estimated Female Functional Support Evacuees"
        ),
    }
    frame = frame.rename(columns=aliases).copy()
    required = {
        "Municipality Observation Time",
        "Municipality Code",
        "Municipality",
        "Open Shelter Count",
        "Evacuees",
        "Municipality Evidence Tier",
        "Functional Support Scenario",
        "Municipality Estimated Female Evacuees",
        "Municipality Estimated Functional Support Evacuees",
        "Municipality Estimated Female Functional Support Evacuees",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")
    if len(frame) != 33 or frame["Municipality"].nunique() != 11:
        raise ValueError("Expected 33 municipality-scenario rows for 11 municipalities")
    if set(frame["Functional Support Scenario"].astype(str)) != set(SCENARIO_ORDER):
        raise ValueError("Unexpected functional-support scenarios")
    if frame[list(required)].isna().any().any():
        raise ValueError("Municipality summary inputs must be complete")
    if frame["Municipality Observation Time"].nunique() != 1:
        raise ValueError("Municipality observations do not share one timestamp")

    for municipality, municipality_rows in frame.groupby("Municipality", observed=True):
        if len(municipality_rows) != 3:
            raise ValueError(f"Expected three scenarios for {municipality}")
        for column in ("Open Shelter Count", "Evacuees"):
            if municipality_rows[column].nunique() != 1:
                raise ValueError(f"Observed {column} varies across scenarios for {municipality}")
        ordered = municipality_rows.set_index("Functional Support Scenario").loc[
            list(SCENARIO_ORDER)
        ]
        for column in (
            "Municipality Estimated Functional Support Evacuees",
            "Municipality Estimated Female Functional Support Evacuees",
        ):
            values = ordered[column].to_numpy(dtype=float)
            if not np.all(values[:-1] <= values[1:]):
                raise ValueError(f"Scenario demand is not monotonic for {municipality}: {column}")

    core = frame.loc[frame["Functional Support Scenario"].astype(str).eq("Core")]
    if int(core["Open Shelter Count"].sum()) != 81 or int(core["Evacuees"].sum()) != 3585:
        raise ValueError("Common snapshot does not reproduce 81 shelters and 3,585 evacuees")
    if (
        frame[
            [
                "Municipality Estimated Female Evacuees",
                "Municipality Estimated Functional Support Evacuees",
                "Municipality Estimated Female Functional Support Evacuees",
            ]
        ]
        .lt(0)
        .any()
        .any()
    ):
        raise ValueError("Scenario-estimated demand cannot be negative")
    if (
        frame[
            [
                "Municipality Estimated Female Evacuees",
                "Municipality Estimated Functional Support Evacuees",
                "Municipality Estimated Female Functional Support Evacuees",
            ]
        ]
        .gt(frame["Evacuees"], axis=0)
        .any()
        .any()
    ):
        raise ValueError("Scenario-estimated subgroup demand exceeds observed evacuees")

    municipality_order = (
        core.sort_values(
            ["Municipality Estimated Functional Support Evacuees", "Municipality Code"],
            ascending=[False, True],
        )["Municipality"]
        .astype(str)
        .tolist()
    )
    frame["Municipality Order"] = pd.Categorical(
        frame["Municipality"], categories=municipality_order, ordered=True
    )
    frame["Scenario Order"] = pd.Categorical(
        frame["Functional Support Scenario"],
        categories=SCENARIO_ORDER,
        ordered=True,
    )
    frame = frame.sort_values(["Municipality Order", "Scenario Order"]).reset_index(drop=True)
    return frame


def write_workbook(table: pd.DataFrame) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Municipality Summary"
    sheet.sheet_view.showGridLines = False
    sheet.freeze_panes = "C2"
    sheet.sheet_view.zoomScale = 80

    sheet.append(list(HEADERS))
    observation_times = pd.to_datetime(table["Municipality Observation Time"])
    for row_number, (_, row) in enumerate(table.iterrows(), start=2):
        sheet.append(
            [
                str(row["Municipality"]),
                str(row["Functional Support Scenario"]),
                int(row["Open Shelter Count"]),
                int(row["Evacuees"]),
                float(row["Municipality Estimated Female Evacuees"]),
                float(row["Municipality Estimated Functional Support Evacuees"]),
                float(row["Municipality Estimated Female Functional Support Evacuees"]),
                f"=ROUNDUP(D{row_number}/50,0)",
                f"=ROUNDUP(D{row_number}/20,0)",
                f"=ROUNDUP(F{row_number}/50,0)",
                f"=ROUNDUP(F{row_number}/20,0)",
                observation_times.iloc[row_number - 2].strftime("%Y-%m-%d %H:%M JST"),
                str(row["Municipality Evidence Tier"]),
            ]
        )

    last_row = sheet.max_row
    last_column = sheet.max_column
    table_range = f"A1:M{last_row}"
    excel_table = Table(displayName="MunicipalityDemandSummary", ref=table_range)
    excel_table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    sheet.add_table(excel_table)

    header_fill = PatternFill("solid", fgColor="27445C")
    header_font = Font(name="Aptos", size=10, bold=True, color="FFFFFF")
    body_font = Font(name="Aptos", size=9, color="263746")
    thin_gray = Side(style="thin", color="D8DEE3")
    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(bottom=Side(style="medium", color="9EB1C0"))
    sheet.row_dimensions[1].height = 72

    for row in sheet.iter_rows(min_row=2, max_row=last_row, min_col=1, max_col=last_column):
        for cell in row:
            cell.font = body_font
            cell.alignment = Alignment(vertical="center", wrap_text=False)
            cell.border = Border(bottom=thin_gray)
        row[0].alignment = Alignment(horizontal="left", vertical="center")
        row[1].alignment = Alignment(horizontal="center", vertical="center")
        for cell in row[2:11]:
            cell.alignment = Alignment(horizontal="right", vertical="center")
        row[11].alignment = Alignment(horizontal="center", vertical="center")
        row[12].alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        sheet.row_dimensions[row[0].row].height = 30

    for column in ("C", "D", "H", "I", "J", "K"):
        for cell in sheet[column][1:]:
            cell.number_format = "#,##0"
    for column in ("E", "F", "G"):
        for cell in sheet[column][1:]:
            cell.number_format = "#,##0.0"

    scenario_fills = {
        "Narrow": "DCEAF4",
        "Core": "F3DED8",
        "Broad": "DCEDE5",
    }
    for scenario, color in scenario_fills.items():
        sheet.conditional_formatting.add(
            f"B2:B{last_row}",
            FormulaRule(
                formula=[f'$B2="{scenario}"'],
                fill=PatternFill("solid", fgColor=color),
            ),
        )

    column_widths = {
        "A": 19,
        "B": 15,
        "C": 12,
        "D": 12,
        "E": 16,
        "F": 18,
        "G": 20,
        "H": 14,
        "I": 15,
        "J": 17,
        "K": 18,
        "L": 19,
        "M": 20,
    }
    for column, width in column_widths.items():
        sheet.column_dimensions[column].width = width

    formula_comments = {
        "H1": "Formula: ceiling of observed evacuees divided by 50.",
        "I1": "Formula: ceiling of observed evacuees divided by 20.",
        "J1": (
            "Sensitivity screen: ceiling of estimated functional-support evacuees "
            "divided by 50; not an official accessible-toilet requirement."
        ),
        "K1": (
            "Sensitivity screen: ceiling of estimated functional-support evacuees "
            "divided by 20; not an official accessible-toilet requirement."
        ),
    }
    for cell_reference, comment_text in formula_comments.items():
        sheet[cell_reference].comment = Comment(comment_text, "Mike Li")

    sheet.auto_filter.ref = table_range
    sheet.print_area = table_range
    sheet.print_title_rows = "1:1"
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.paperSize = sheet.PAPERSIZE_A3
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 1
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_margins.left = 0.2
    sheet.page_margins.right = 0.2
    sheet.page_margins.top = 0.35
    sheet.page_margins.bottom = 0.35
    sheet.oddFooter.center.text = "Municipality-level planning screen"
    sheet.oddFooter.center.size = 8
    sheet.oddFooter.center.color = "66737D"

    notes = workbook.create_sheet("Notes")
    notes.sheet_view.showGridLines = False
    notes["A1"] = "Evidence and interpretation notes"
    notes["A1"].font = Font(name="Aptos Display", size=15, bold=True, color="27445C")
    notes["A3"] = "Item"
    notes["B3"] = "Definition or boundary"
    note_rows = (
        (
            "Interpretation boundary",
            INTERPRETATION_BOUNDARY,
        ),
        (
            "Observed fields",
            "Open Shelter Count and Evacuees are municipality-total observations at the common evacuation snapshot.",
        ),
        (
            "Synthetic fields",
            "Female and functional-support demand values are planning expectations derived from residential and certification inputs; they are not observed shelter composition.",
        ),
        (
            "Accessible-unit parity screens",
            "Initial and prolonged accessible-unit parity screens apply the ordinary 1:50 and 1:20 ratios to synthetic functional-support demand; they are not official accessible-toilet compliance thresholds.",
        ),
        (
            "Reference periods",
            "Residential population: 2020; functional-support certification: April 2026; evacuation observation: 12 August 2026 at 14:00 JST.",
        ),
    )
    for row_number, values in enumerate(note_rows, start=4):
        notes.append(values)
        notes.row_dimensions[row_number].height = 36
    for cell in notes[3]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="left", vertical="center")
    notes.row_dimensions[3].height = 24
    for row in notes.iter_rows(min_row=4, max_row=notes.max_row, min_col=1, max_col=2):
        row[0].font = Font(name="Aptos", size=9, bold=True, color="263746")
        row[1].font = body_font
        for cell in row:
            cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            cell.border = Border(bottom=thin_gray)
    notes.column_dimensions["A"].width = 30
    notes.column_dimensions["B"].width = 105
    notes.freeze_panes = "A4"
    notes.sheet_view.zoomScale = 90
    notes.print_area = f"A1:B{notes.max_row}"
    notes.page_setup.orientation = "landscape"
    notes.page_setup.paperSize = notes.PAPERSIZE_A4
    notes.page_setup.fitToWidth = 1
    notes.page_setup.fitToHeight = 1
    notes.sheet_properties.pageSetUpPr.fitToPage = True
    notes.page_margins.left = 0.35
    notes.page_margins.right = 0.35
    notes.page_margins.top = 0.45
    notes.page_margins.bottom = 0.45

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(OUTPUT)


def verify_workbook(expected: pd.DataFrame) -> None:
    workbook = load_workbook(OUTPUT, data_only=False, read_only=False)
    if workbook.sheetnames != ["Municipality Summary", "Notes"]:
        raise ValueError(f"Unexpected workbook sheets: {workbook.sheetnames}")
    sheet = workbook["Municipality Summary"]
    if sheet.max_row != 34 or sheet.max_column != 13:
        raise ValueError(f"Unexpected workbook dimensions: {sheet.max_row} x {sheet.max_column}")
    observed_headers = tuple(cell.value for cell in sheet[1])
    if observed_headers != HEADERS:
        raise ValueError("Workbook headers do not match the planned 14-column table")
    if sheet["H2"].value != "=ROUNDUP(D2/50,0)" or sheet["K34"].value != "=ROUNDUP(F34/20,0)":
        raise ValueError("Requirement or accessible-parity formulas are missing")
    values = list(sheet.values)[1:]
    if len(values) != len(expected):
        raise ValueError("Workbook data-row count does not match the validated table")
    if sum(int(row[3]) for row in values if row[1] == "Core") != 3585:
        raise ValueError("Workbook Core rows do not reproduce 3,585 evacuees")
    notes = workbook["Notes"]
    if notes["B4"].value != INTERPRETATION_BOUNDARY:
        raise ValueError("Workbook Notes sheet does not preserve the interpretation boundary")
    workbook.close()


def main() -> None:
    source = pd.read_parquet(SOURCE)
    table = prepare_table(source)
    write_workbook(table)
    verify_workbook(table)
    print(f"Saved: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
