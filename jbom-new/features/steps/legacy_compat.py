"""Legacy compatibility steps remaining for cleanup."""
from __future__ import annotations

from behave import given, then
import project_centric_steps
import common_steps


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


@given('"{main}" contains component "{ref}" with value "{value}"')
def given_schematic_contains_component(context, main, ref, value):
    """Legacy: add component to specific schematic."""
    from behave.model import Table, Row

    # Create table context for the component
    context.table = Table(
        headings=["Reference", "Value", "Footprint"],
        rows=[Row(table=None, cells=[ref, value, "R_0805_2012"])],
    )
    project_centric_steps.given_named_schematic_contains(context, main)


@then('the file "{filename}" should not contain "{text}"')
def then_file_should_not_contain(context, filename, text):
    """Legacy: check file does not contain text."""
    from pathlib import Path

    file_path = Path(context.project_root) / filename
    assert file_path.exists(), f"File not found: {file_path}"
    content = file_path.read_text(encoding="utf-8")
    assert (
        text not in content
    ), f"File '{filename}' should not contain '{text}' but it does.\nContent:\n{content}"


@then('the error should contain "{text}"')
def then_error_should_contain(context, text):
    """Legacy: check error output contains text."""
    common_steps.step_error_output_should_mention(context, text)


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
