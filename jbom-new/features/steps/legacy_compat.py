"""Legacy compatibility adapter layer for jBOM Behave tests.

This module provides backward compatibility for old step phrases that were
used in scenarios before consolidation to canonical DRY step patterns.

All steps here delegate to the canonical forms defined in project_centric_steps.py
and common_steps.py to avoid code duplication and maintenance burden.

TODO: Remove this adapter layer after feature files are migrated to canonical steps.
"""
from __future__ import annotations

from behave import given, then
import project_centric_steps
import common_steps


# --------------------------
# Legacy schematic creation patterns → canonical "a schematic that contains:"
# --------------------------


# Redundant schematic patterns removed - normalized in feature files via transformation


# --------------------------
# Legacy PCB creation patterns → canonical "a PCB that contains:"
# --------------------------


# Redundant PCB patterns removed - normalized in feature files via transformation


# --------------------------
# Legacy fabricator patterns → canonical fabricator selection
# --------------------------


# Redundant fabricator patterns removed - normalized in feature files via transformation


# --------------------------
# Legacy command execution patterns → canonical command steps
# --------------------------


# Redundant command execution patterns removed - normalized in feature files via transformation


# --------------------------
# Legacy assertion patterns → canonical assertion steps
# --------------------------


# Redundant assertion patterns removed - normalized in feature files via transformation


# Redundant CSV file patterns removed - normalized in feature files via transformation


# --------------------------
# Legacy output format patterns → canonical BOM assertions
# --------------------------


# --------------------------
# Legacy file operations → canonical file steps
# --------------------------


# --------------------------
# Legacy workspace patterns → canonical workspace steps
# --------------------------


# Redundant workspace patterns removed - normalized in feature files via transformation


# --------------------------
# Catch-all patterns for common variations
# --------------------------


# Redundant result patterns removed - normalized in feature files via transformation


# =========================
# FILE OPERATIONS WITH CONTENT TABLE
# =========================


# Implementation-focused backup assertion steps removed
# These tested jBOM's internal backup naming conventions rather than backup behavior
# The calling scenarios should be refactored to test functional backup behavior


# =========================
# COMPREHENSIVE SCHEMATIC PATTERNS
# =========================


# Redundant comprehensive schematic pattern removed - normalized in feature files via transformation


# =========================
# OUTPUT ORDERING AND CONTENT ASSERTIONS
# =========================


@then("{ref1} appears before {ref2} in the output")
def then_ref_appears_before_ref(context, ref1, ref2):
    """Legacy: check component order in output."""
    output = getattr(context, "last_output", "")
    assert output, "No output captured"

    pos1 = output.find(ref1)
    pos2 = output.find(ref2)

    assert pos1 >= 0, f"Component {ref1} not found in output"
    assert pos2 >= 0, f"Component {ref2} not found in output"
    assert pos1 < pos2, f"Expected {ref1} to appear before {ref2} in output"


# =========================
# PROJECT AND BOM CONTENT ASSERTIONS
# =========================


# used in project_centric/architecture.feature
@then('the BOM should contain component "{ref}" with value "{value}"')
def then_bom_should_contain_component_value(context, ref, value):
    """Legacy: delegate to canonical BOM assertion."""
    project_centric_steps.then_bom_contains_ref_value(context, ref, value)


# =========================
# WORKSPACE AND PROJECT SETUP
# =========================


@given('the project contains a file "{filename}" with content:')
def given_project_contains_file_with_content(context, filename):
    """Legacy: create file in project with table content."""
    from pathlib import Path
    import csv
    import io

    if context.table:
        # Create CSV content from table
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=context.table.headings)
        writer.writeheader()
        for row in context.table:
            writer.writerow(row.as_dict())
        content = output.getvalue()
    else:
        content = ""

    file_path = Path(context.project_root) / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")


# =========================
# FINAL REMAINING UNDEFINED STEP PATTERNS
# =========================


# =========================
# SPECIFIC FILE FORMAT CHECKS
# =========================


# =========================
# PROJECT SETUP PATTERNS
# =========================


@given("a project with no components")
def given_project_with_no_components(context):
    """Legacy: create empty project setup."""
    from behave.model import Table

    context.table = Table(headings=["Reference", "Value", "Footprint"], rows=[])
    project_centric_steps.given_simple_schematic(context)


# =========================
# SPECIFIC SCHEMATIC FILE PATTERNS
# =========================


@given('a KiCad schematic file "{filename}" with basic components')
def given_kicad_schematic_file_with_components(context, filename):
    """Legacy: create specific KiCad schematic file."""
    from behave.model import Table, Row

    # Create basic components for the schematic
    context.table = Table(
        headings=["Reference", "Value", "Footprint"],
        rows=[
            Row(table=None, cells=["R1", "10K", "R_0805_2012"]),
            Row(table=None, cells=["C1", "100nF", "C_0603_1608"]),
            Row(table=None, cells=["U1", "LM358", "SOIC-8_3.9x4.9mm"]),
        ],
    )

    # Create the named schematic file
    project_centric_steps.given_named_schematic_contains(context, filename)


# =========================
# INVENTORY FILE PATTERNS
# =========================


@given('an inventory file with a very long name "{filename}" with contents:')
def given_inventory_file_long_name_with_contents(context, filename):
    """Legacy: create inventory file with very long name."""
    from pathlib import Path
    import csv
    import io

    if context.table:
        # Create CSV content from table
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=context.table.headings)
        writer.writeheader()
        for row in context.table:
            writer.writerow(row.as_dict())
        content = output.getvalue()
    else:
        content = ""

    file_path = Path(context.project_root) / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")


# =========================
# LEGACY PROJECT PATTERNS
# =========================


@given('the project contains a schematic with component "{ref}" with value "{value}"')
def given_project_contains_schematic_with_component(context, ref, value):
    """Legacy: add specific component to project schematic."""
    from behave.model import Table, Row

    # Create minimal schematic with the specified component
    context.table = Table(
        headings=["Reference", "Value", "Footprint"],
        rows=[
            Row(table=None, cells=[ref, value, "Generic_Footprint"]),
        ],
    )
    project_centric_steps.given_simple_schematic(context)


# =========================
# HIERARCHICAL PROJECT PATTERNS
# =========================


@given('a hierarchical project "{name}"')
def given_hierarchical_project(context, name):
    """Legacy: create hierarchical project setup."""
    project_centric_steps.given_kicad_project_directory(context, name)


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


# =========================
# ADDITIONAL FILE AND CONTENT PATTERNS
# =========================


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


@given('an empty inventory file "{filename}" with headers only:')
def given_empty_inventory_file_headers(context, filename):
    """Legacy: create empty inventory with headers from table."""
    from pathlib import Path
    import csv
    import io

    # Create CSV with headers but no data rows
    output = io.StringIO()
    if context.table and context.table.headings:
        writer = csv.DictWriter(output, fieldnames=context.table.headings)
        writer.writeheader()

    file_path = Path(context.project_root) / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(output.getvalue(), encoding="utf-8")


@then('the error should contain "{text}"')
def then_error_should_contain(context, text):
    """Legacy: check error output contains text."""
    common_steps.step_error_output_should_mention(context, text)


@given("multiple inventory files with unique IPNs:")
def given_multiple_inventory_files_unique_ipns(context):
    """Legacy: create multiple inventory files from table."""
    # This step would typically be followed by table data
    # For now, delegate to basic inventory creation
    given_inventory_file_with_contents(context, "inventory1.csv")


@given('an inaccessible inventory file "{filename}" with no read permissions')
def given_inaccessible_inventory_file(context, filename):
    """Legacy: create inventory file and make it inaccessible."""
    from pathlib import Path
    import stat

    file_path = Path(context.project_root) / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("IPN,Category\nRES_1K,RESISTOR", encoding="utf-8")
    # Remove read permissions
    file_path.chmod(stat.S_IWUSR)


@given('a project named "{name}"')
def given_project_named(context, name):
    """Legacy: create named project."""
    project_centric_steps.given_kicad_project_directory(context, name)


@given('a directory "{dirname}"')
def given_directory_alt(context, dirname):
    """Legacy: create directory."""
    common_steps.step_create_directory(context, dirname)


# Trailing space command handler removed - fixed scenario outlines to use explicit location context


# --------------------------
# Legacy inventory and file patterns
# --------------------------


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


# Note: File operations already exist in canonical form in common_steps.py
# - 'a file named "{filename}" should exist'
# - 'the file "{filename}" should contain "{text}"'
# - 'I create file "{rel_path}" with content "{text}"'
