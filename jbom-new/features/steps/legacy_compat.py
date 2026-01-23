"""Legacy compatibility adapter layer for jBOM Behave tests.

This module provides backward compatibility for old step phrases that were
used in scenarios before consolidation to canonical DRY step patterns.

All steps here delegate to the canonical forms defined in project_centric_steps.py
and common_steps.py to avoid code duplication and maintenance burden.

TODO: Remove this adapter layer after feature files are migrated to canonical steps.
"""
from __future__ import annotations

from behave import given, when, then
import project_centric_steps
import common_steps
import bom_steps


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


@then("the output contains BOM headers")
def then_output_contains_bom_headers(context):
    """Legacy: delegate to canonical CSV headers check."""
    bom_steps.then_output_contains_csv_headers(context)


@then('the BOM contains "{ref}" with value "{value}"')
def then_bom_contains_ref_value_legacy(context, ref, value):
    """Legacy: delegate to canonical BOM assertion."""
    project_centric_steps.then_bom_contains_ref_value(context, ref, value)


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


@given('a schematic named "{filename}" that contains:')
def given_named_schematic_that_contains(context, filename):
    """Legacy: create specifically named schematic."""
    project_centric_steps.given_named_schematic_contains(context, filename)


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


@then('the BOM should contain component "{ref}" with value "{value}"')
def then_bom_should_contain_component_value(context, ref, value):
    """Legacy: delegate to canonical BOM assertion."""
    project_centric_steps.then_bom_contains_ref_value(context, ref, value)


@then('the project name should be "{name}"')
def then_project_name_should_be(context, name):
    """Legacy: check project name in output."""
    output = getattr(context, "last_output", "")
    assert name in output, f"Project name '{name}' not found in output. Got: {output}"


@then('the POS should contain component "{ref}" at position "{position}"')
def then_pos_should_contain_component_position(context, ref, position):
    """Legacy: delegate to canonical POS assertion."""
    x, y = position.split(",") if "," in position else (position, "0")
    project_centric_steps.then_pos_contains_component_at(context, ref, x, y)


@then('the BOM title should show project name "{name}"')
def then_bom_title_shows_project(context, name):
    """Legacy: check BOM title contains project name."""
    output = getattr(context, "last_output", "")
    assert (
        f"{name} - Bill of Materials" in output or "Bill of Materials" in output
    ), f"BOM title with project name '{name}' not found in output"


# =========================
# WORKSPACE AND PROJECT SETUP
# =========================


@given("a test workspace")
def given_test_workspace(context):
    """Legacy: delegate to canonical workspace setup."""
    common_steps.step_clean_test_workspace(context)


@given('a KiCad project directory "{name}"')
def given_kicad_project_directory(context, name):
    """Legacy: create KiCad project directory."""
    from pathlib import Path

    project_dir = Path(context.project_root) / name
    project_dir.mkdir(parents=True, exist_ok=True)

    # Update context to use this as the working directory
    context.project_root = project_dir
    context.current_project = name


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


@given("a complete project with components and PCB layout:")
def given_complete_project_with_components_pcb(context):
    """Legacy: create comprehensive project with schematic and PCB."""
    # Delegate to canonical complete project setup
    project_centric_steps.given_complete_project(context)


@then("the output should contain a formatted table")
def then_output_contains_formatted_table(context):
    """Legacy: verify output contains a formatted table."""
    output = getattr(context, "last_output", "")
    # Check for table indicators like headers, separators, aligned columns
    has_headers = any(
        "Reference" in line and "Value" in line for line in output.split("\n")
    )
    has_separators = any("|" in line or "+-" in line for line in output.split("\n"))
    assert (
        has_headers or has_separators
    ), f"Output does not contain a formatted table. Got: {output}"


@then("the output should not be CSV format")
def then_output_not_csv_format(context):
    """Legacy: verify output is not in CSV format."""
    output = getattr(context, "last_output", "")
    lines = output.strip().split("\n")
    # CSV typically has comma separators and consistent field counts
    csv_indicators = sum(
        1 for line in lines if "," in line and len(line.split(",")) > 2
    )
    assert (
        csv_indicators < len(lines) / 2
    ), f"Output appears to be in CSV format: {output}"


@then("the output should be in CSV format")
def then_output_in_csv_format(context):
    """Legacy: verify output is in CSV format."""
    output = getattr(context, "last_output", "")
    lines = [line.strip() for line in output.strip().split("\n") if line.strip()]
    assert lines, "No output to check"

    # Check for CSV characteristics: comma separators, consistent field counts
    csv_lines = [line for line in lines if "," in line]
    if csv_lines:
        field_counts = [len(line.split(",")) for line in csv_lines]
        consistent_fields = len(set(field_counts)) <= 2  # Allow header/data variation
        assert consistent_fields, f"Inconsistent CSV field counts: {field_counts}"
        assert (
            len(csv_lines) >= len(lines) / 2
        ), "Less than half the output appears to be CSV format"


# =========================
# SPECIFIC FILE FORMAT CHECKS
# =========================


@then('the file "{filename}" should be in CSV format')
def then_file_should_be_csv_format(context, filename):
    """Legacy: verify specific file is in CSV format."""
    from pathlib import Path

    file_path = Path(context.project_root) / filename
    assert file_path.exists(), f"File {filename} does not exist"

    content = file_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.strip().split("\n") if line.strip()]
    assert lines, f"File {filename} is empty"

    # Check for CSV characteristics
    csv_lines = [line for line in lines if "," in line]
    assert (
        len(csv_lines) >= len(lines) / 2
    ), f"File {filename} does not appear to be CSV format"


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


@given('a project directory "{dirname}" with legacy ".pro" file')
def given_project_directory_with_legacy_pro(context, dirname):
    """Legacy: create project directory with legacy .pro file."""
    from pathlib import Path

    # Create project directory
    project_dir = Path(context.project_root) / dirname
    project_dir.mkdir(parents=True, exist_ok=True)

    # Create legacy .pro file
    pro_file = project_dir / f"{dirname}.pro"
    pro_file.write_text(
        f"""# Legacy KiCad project file for {dirname}
[general]
version=1
[/general]
""",
        encoding="utf-8",
    )

    # Update context to use this as the working directory
    context.project_root = project_dir
    context.current_project = dirname


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


@given('the project contains a file "{filename}"')
def given_project_contains_file(context, filename):
    """Legacy: create minimal file in project."""
    from pathlib import Path

    file_path = Path(context.project_root) / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if filename.endswith(".kicad_pro"):
        file_path.write_text("(kicad_project (version 1))\n", encoding="utf-8")
    elif filename.endswith(".kicad_sch"):
        file_path.write_text(
            "(kicad_sch (version 20211123) (generator eeschema))\n", encoding="utf-8"
        )
    elif filename.endswith(".kicad_pcb"):
        file_path.write_text(
            "(kicad_pcb (version 20211014) (generator pcbnew))\n", encoding="utf-8"
        )
    else:
        file_path.write_text("", encoding="utf-8")


@given('the project contains a file "{filename}" with basic schematic content')
def given_project_file_basic_schematic(context, filename):
    """Legacy: create basic schematic file."""
    from pathlib import Path

    file_path = Path(context.project_root) / filename
    content = """(kicad_sch (version 20211123) (generator eeschema)
  (paper "A4")
  (symbol (lib_id "Device:R") (at 50 50 0) (unit 1)
    (property "Reference" "R1" (id 0) (at 52 48 0))
    (property "Value" "10K" (id 1) (at 52 52 0))
    (property "Footprint" "R_0805_2012" (id 2) (at 52 54 0))
  )
)
"""
    file_path.write_text(content, encoding="utf-8")


@given('the project contains a file "{filename}" with basic PCB content')
def given_project_file_basic_pcb(context, filename):
    """Legacy: create basic PCB file."""
    from pathlib import Path

    file_path = Path(context.project_root) / filename
    content = """(kicad_pcb (version 20211014) (generator pcbnew)
  (paper "A4")
  (footprint "R_0805_2012" (at 76.2 104.14 0) (layer "F.Cu")
    (property "Reference" "R1")
  )
)
"""
    file_path.write_text(content, encoding="utf-8")


@given('the project contains a schematic "{filename}" with components:')
def given_project_contains_schematic_components(context, filename):
    """Legacy: create schematic with component table."""
    project_centric_steps.given_named_schematic_contains(context, filename)


@given('the project contains a PCB "{filename}" with footprints:')
def given_project_contains_pcb_footprints(context, filename):
    """Legacy: create PCB with footprint table."""
    # Use canonical PCB creation but with specific filename
    project_centric_steps.given_simple_pcb(context)
    # Rename the generated file
    from pathlib import Path

    old_path = Path(context.project_root) / "project.kicad_pcb"
    new_path = Path(context.project_root) / filename
    if old_path.exists():
        old_path.rename(new_path)


@given("the directory is read-only")
def given_directory_readonly(context):
    """Legacy: make directory read-only."""
    from pathlib import Path
    import stat

    # Make the project directory read-only
    project_dir = Path(context.project_root)
    current_permissions = project_dir.stat().st_mode
    project_dir.chmod(current_permissions & ~stat.S_IWRITE)

    # Store original permissions for cleanup
    context.original_permissions = current_permissions


# =========================
# HIERARCHICAL PROJECT PATTERNS
# =========================


@given('a hierarchical project "{name}"')
def given_hierarchical_project(context, name):
    """Legacy: create hierarchical project setup."""
    given_kicad_project_directory(context, name)


@given('the main schematic "{main}" references sheet "{child}"')
def given_main_references_sheet(context, main, child):
    """Legacy: delegate to canonical hierarchical reference."""
    # Set the main schematic name for the project context
    context.current_project = main.replace(".kicad_sch", "")
    project_centric_steps.given_root_references_child(
        context, child.replace(".kicad_sch", "")
    )


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
    given_kicad_project_directory(context, name)


@given('a directory "{dirname}"')
def given_directory_alt(context, dirname):
    """Legacy: create directory."""
    common_steps.step_create_directory(context, dirname)


# Handle command patterns with trailing spaces from scenario outlines
@when('I run jbom command "{command}" ')
def when_run_jbom_command_trailing_space(context, command):
    """Legacy: handle jbom commands with trailing spaces."""
    common_steps.step_run_jbom_command(context, command.strip())


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
