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


@given("a standard test schematic that contains:")
def given_standard_test_schematic(context):
    """Legacy: delegate to canonical schematic creation."""
    project_centric_steps.given_simple_schematic(context)


@given("a basic schematic that contains:")
def given_basic_schematic(context):
    """Legacy: delegate to canonical schematic creation."""
    project_centric_steps.given_simple_schematic(context)


@given("a test schematic that contains:")
def given_test_schematic(context):
    """Legacy: delegate to canonical schematic creation."""
    project_centric_steps.given_simple_schematic(context)


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


@given("a standard test PCB that contains:")
def given_standard_test_pcb(context):
    """Legacy: delegate to canonical PCB creation."""
    project_centric_steps.given_simple_pcb(context)


@given("a basic PCB that contains:")
def given_basic_pcb(context):
    """Legacy: delegate to canonical PCB creation."""
    project_centric_steps.given_simple_pcb(context)


@given("a test PCB that contains:")
def given_test_pcb(context):
    """Legacy: delegate to canonical PCB creation."""
    project_centric_steps.given_simple_pcb(context)


# --------------------------
# Legacy fabricator patterns → canonical fabricator selection
# --------------------------


@given("the default fabricator is selected")
def given_default_fabricator(context):
    """Legacy: delegate to generic fabricator."""
    project_centric_steps.given_generic_fabricator(context)


@given("using the generic fabricator")
def given_using_generic_fabricator(context):
    """Legacy: delegate to generic fabricator."""
    project_centric_steps.given_generic_fabricator(context)


@given("I select the generic fabricator")
def given_i_select_generic_fabricator(context):
    """Legacy: delegate to generic fabricator."""
    project_centric_steps.given_generic_fabricator(context)


# --------------------------
# Legacy command execution patterns → canonical command steps
# --------------------------


@when('I run the jbom command with "{args}"')
def when_run_jbom_command_with(context, args):
    """Legacy: delegate to canonical command execution."""
    common_steps.step_run_jbom_command(context, args)


@when('I execute "{command}"')
def when_execute_command(context, command):
    """Legacy: delegate to canonical command execution."""
    common_steps.step_run_command(context, command)


@when('I execute jbom "{args}"')
def when_execute_jbom(context, args):
    """Legacy: delegate to canonical jbom execution."""
    common_steps.step_run_jbom_command(context, args)


# --------------------------
# Legacy assertion patterns → canonical assertion steps
# --------------------------


@then("the command succeeds")
def then_command_succeeds(context):
    """Legacy: delegate to canonical success check."""
    common_steps.step_command_should_succeed(context)


@then("the command fails")
def then_command_fails(context):
    """Legacy: delegate to canonical failure check."""
    common_steps.step_command_should_fail(context)


@then('I see "{text}"')
def then_i_see_text(context, text):
    """Legacy: delegate to canonical text verification."""
    common_steps.step_see_text(context, text)


@then('the output includes "{text}"')
def then_output_includes(context, text):
    """Legacy: delegate to canonical output check."""
    common_steps.step_output_should_contain(context, text)


@then('the output does not include "{text}"')
def then_output_not_includes(context, text):
    """Legacy: delegate to canonical negative output check."""
    common_steps.step_output_should_not_contain(context, text)


@then('a CSV file "{filename}" should exist')
def then_csv_file_exists(context, filename):
    """Legacy: delegate to canonical file existence check."""
    common_steps.step_file_should_exist(context, filename)


@then('the CSV file "{filename}" should contain "{text}"')
def then_csv_file_contains(context, filename, text):
    """Legacy: delegate to canonical file content check."""
    common_steps.step_file_should_contain(context, filename, text)


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


@given("I am in a clean workspace")
def given_clean_workspace(context):
    """Legacy: delegate to canonical workspace setup."""
    common_steps.step_clean_test_workspace(context)


@given("I have a clean test environment")
def given_clean_test_environment(context):
    """Legacy: delegate to canonical workspace setup."""
    common_steps.step_clean_test_workspace(context)


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


@then("the result should be successful")
def then_result_successful(context):
    """Legacy: alternative success check."""
    common_steps.step_command_should_succeed(context)


@then("the result should fail")
def then_result_should_fail(context):
    """Legacy: alternative failure check."""
    common_steps.step_command_should_fail(context)


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
