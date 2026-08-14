#!/usr/bin/env python3
"""Shelter Spatial Distribution and Functional-Support Sensitivity.

Plan: Combine Kumamoto City and Yatsushiro City locator maps with city-specific
low, base, and high shelter functional-support estimates.
Framework: Section 5 shelter spatial and synthetic-demand contrasts; Section 6
calibrated mesh catchments and overlap scenarios; Section 7 joint spatial and
scenario-sensitivity workflow. District-anchor locations remain district-level
screens rather than precise shelter catchments.
"""

from pathlib import Path

import figure_functional_support_demand_sensitivity_by_shelter as source_figure


ROOT = Path(__file__).resolve().parents[2]
source_figure.OUTPUT = (
    ROOT
    / "data/results/figures/"
    "Figure_shelter_spatial_distribution_and_functional_support_sensitivity.png"
)


if __name__ == "__main__":
    source_figure.main()
