"""Legacy compatibility steps remaining for cleanup."""
from __future__ import annotations

from behave import given
import project_centric_steps


# REMOVED: @given('the project contains a file "{filename}" with content:')
# This step created circular validation - hand-crafted KiCad files that mirror jBOM expectations
# rather than testing real KiCad compatibility.
#
# ARCHITECTURAL ISSUE: Fragile, implementation-dependent test data
# PROPER SOLUTION: Use fixture-based approach with real KiCad-generated files
#   1. Use actual KiCad to generate real project files
#   2. Save them as fixtures in fixtures/ directory
#   3. Copy fixture files for test scenarios
#   4. Tests real-world compatibility, not circular validation


@given('an inventory file "{filename}" with contents:')
def given_inventory_file_with_contents(context, filename):
    """Legacy: create inventory CSV file with table data."""
    from pathlib import Path
    import csv

    file_path = Path(context.project_root) / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", newline="", encoding="utf-8") as csvfile:
        if context.table and context.table.headings:
            writer = csv.DictWriter(csvfile, fieldnames=context.table.headings)
            writer.writeheader()
            for row in context.table:
                writer.writerow(row.as_dict())


@given("a standard BOM test schematic that contains:")
def given_standard_bom_test_schematic(context):
    """Legacy: create standard BOM test schematic."""
    project_centric_steps.given_simple_schematic(context)


@given("a minimal test schematic that contains:")
def given_minimal_test_schematic_contains(context):
    """Legacy: delegate to canonical schematic creation."""
    project_centric_steps.given_simple_schematic(context)
