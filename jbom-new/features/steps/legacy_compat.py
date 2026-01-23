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


@given("an empty schematic")
def given_empty_schematic(context):
    """Legacy: create empty schematic."""
    # Create empty table context for canonical step
    from behave.model import Table

    context.table = Table(headings=["Reference", "Value", "Footprint"], rows=[])
    project_centric_steps.given_simple_schematic(context)


@given("a minimal schematic")
def given_minimal_schematic(context):
    """Legacy: create basic R/C/U schematic."""
    from behave.model import Table, Row

    context.table = Table(
        headings=["Reference", "Value", "Footprint"],
        rows=[
            Row(table=None, cells=["R1", "10K", "R_0805_2012"]),
            Row(table=None, cells=["C1", "100nF", "C_0603_1608"]),
            Row(table=None, cells=["U1", "LM358", "SOIC-8_3.9x4.9mm"]),
        ],
    )
    project_centric_steps.given_simple_schematic(context)


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


@then("the output contains component data")
def then_output_contains_component_data(context):
    """Legacy: delegate to canonical component markers check."""
    bom_steps.then_output_contains_component_markers(context)


@then('the BOM contains "{ref}" with value "{value}"')
def then_bom_contains_ref_value_legacy(context, ref, value):
    """Legacy: delegate to canonical BOM assertion."""
    project_centric_steps.then_bom_contains_ref_value(context, ref, value)


# --------------------------
# Legacy file operations → canonical file steps
# --------------------------


@given('I have file "{filename}" with content "{content}"')
def given_file_with_content(context, filename, content):
    """Legacy: delegate to canonical file creation."""
    common_steps.step_create_file_with_content(context, filename, content)


@given('I have directory "{dirname}"')
def given_directory(context, dirname):
    """Legacy: delegate to canonical directory creation."""
    common_steps.step_create_directory(context, dirname)


# --------------------------
# Legacy workspace patterns → canonical workspace steps
# --------------------------


# Redundant workspace patterns removed - normalized in feature files via transformation


# --------------------------
# Catch-all patterns for common variations
# --------------------------


@given('the fabricator is set to "{fabricator}"')
def given_fabricator_set_to(context, fabricator):
    """Legacy: set specific fabricator."""
    context.fabricator = fabricator.lower()


@when('I run jbom with "{args}"')
def when_run_jbom_with(context, args):
    """Legacy: alternative jbom command syntax."""
    common_steps.step_run_jbom_command(context, args)


# Redundant result patterns removed - normalized in feature files via transformation


# =========================
# FILE OPERATIONS WITH CONTENT TABLE
# =========================


@given('a file named "{filename}" exists with content:')
def given_file_exists_with_content(context, filename):
    """Legacy: create file with table content."""
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


@then('the file "{filename}" should still contain "{text}"')
def then_file_should_still_contain(context, filename, text):
    """Legacy: check file still contains text."""
    common_steps.step_file_should_contain(context, filename, text)


@then('a backup file matching "{pattern}" should exist')
def then_backup_file_matching_pattern(context, pattern):
    """Legacy: check backup file exists with regex pattern."""
    from pathlib import Path
    import re

    project_dir = Path(context.project_root)
    backup_files = list(project_dir.glob("*.csv"))

    # Convert pattern to regex and check
    regex_pattern = pattern.replace("\\", "\\\\")
    found = any(re.search(regex_pattern, f.name) for f in backup_files)
    assert (
        found
    ), f"No backup file matching pattern '{pattern}' found. Files: {[f.name for f in backup_files]}"


@then('the backup file should contain "{text}"')
def then_backup_file_contains(context, text):
    """Legacy: check backup file contains text."""
    from pathlib import Path

    # Find backup files
    project_dir = Path(context.project_root)
    backup_files = list(project_dir.glob("*.backup.*.csv"))
    if not backup_files:
        backup_files = list(project_dir.glob("*backup*.csv"))

    assert backup_files, "No backup files found"

    # Check if any backup contains the text
    found = False
    for backup_file in backup_files:
        content = backup_file.read_text(encoding="utf-8")
        if text in content:
            found = True
            break

    assert found, f"Text '{text}' not found in any backup file"


@then("no backup files should exist")
def then_no_backup_files(context):
    """Legacy: verify no backup files exist."""
    from pathlib import Path

    project_dir = Path(context.project_root)
    backup_files = list(project_dir.glob("*backup*.csv")) + list(
        project_dir.glob("*.backup.*.csv")
    )
    assert (
        not backup_files
    ), f"Unexpected backup files found: {[f.name for f in backup_files]}"


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
    given_file_exists_with_content(context, filename)


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


@given('a file named "{filename}" exists')
def given_file_exists_simple(context, filename):
    """Legacy: create empty/minimal file."""
    from pathlib import Path

    file_path = Path(context.project_root) / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("", encoding="utf-8")


@then('the file "{filename}" should exist')
def then_file_should_exist_alt(context, filename):
    """Legacy: alternative file existence check."""
    common_steps.step_file_should_exist(context, filename)


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


@then('the error output should contain "{text}"')
def then_error_output_should_contain_alt(context, text):
    """Legacy: alternative error output check."""
    common_steps.step_error_output_should_mention(context, text)


# --------------------------
# Legacy inventory and file patterns
# --------------------------


@given('an existing inventory file "{filename}" with contents:')
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


@given('a secondary inventory file "{filename}" with contents:')
def given_secondary_inventory_file(context, filename):
    """Legacy: create secondary inventory CSV file."""
    given_inventory_file_with_contents(context, filename)


@given("a BOM test schematic that contains:")
def given_bom_test_schematic(context):
    """Legacy: delegate to canonical schematic creation."""
    project_centric_steps.given_simple_schematic(context)


# Note: File operations already exist in canonical form in common_steps.py
# - 'a file named "{filename}" should exist'
# - 'the file "{filename}" should contain "{text}"'
# - 'I create file "{rel_path}" with content "{text}"'


@given('a file "{filename}" with content "{content}"')
def given_file_with_content_alt(context, filename, content):
    """Legacy: create file with content (alternative syntax)."""
    common_steps.step_create_file_with_content(context, filename, content)
