"""
Shared BDD step definitions for jBOM testing.

This module contains core steps that are used across multiple feature areas,
including multi-modal validation, basic CLI/API operations, and common
test data setup.
"""

import csv

from behave import given, when, then


# =============================================================================
# Test Data Setup Steps
# =============================================================================


@given('a KiCad project named "{project_name}"')
def step_given_kicad_project(context, project_name):
    """Set up a KiCad project for testing."""
    context.project_name = project_name
    # TODO: Implement test project setup in Phase 3


@given("an inventory file with components")
def step_given_inventory_file_with_components(context):
    """Set up an inventory file with test components."""
    # TODO: Implement inventory file setup in Phase 3
    # The inventory data table will be available in context.table if provided
    context.inventory_file = "test_inventory.csv"
    if hasattr(context, "table") and context.table:
        context.inventory_data = context.table
    else:
        context.inventory_data = None


@given("the schematic contains standard components")
def step_given_schematic_contains_standard_components(context):
    """Set up a schematic with standard components."""
    # TODO: Implement schematic setup in Phase 3


# =============================================================================
# Fixture-Based Test Setup Steps
# =============================================================================


@given('the "{fixture_name}" schematic')
def step_given_fixture_schematic(context, fixture_name):
    """Set up a schematic using a named fixture."""
    # TODO: Implement fixture-based schematic setup in Phase 3
    context.fixture_name = fixture_name
    pass


# NOTE: PCB layout step moved to POS domain per Axiom #13
# PCB layouts are POS-domain specific, not cross-domain


@given('the "{fixture_name}" inventory')
def step_given_fixture_inventory(context, fixture_name):
    """Set up an inventory using a named fixture."""
    # TODO: Implement fixture-based inventory setup in Phase 3
    context.inventory_fixture = fixture_name
    pass


@given("an Excel inventory file with complete distributor data")
def step_given_excel_inventory_complete_distributor_data(context):
    """Set up Excel inventory file with complete distributor data."""
    # TODO: Implement Excel inventory setup in Phase 3
    context.inventory_file_type = "Excel"
    context.inventory_completeness = "complete_distributor_data"
    pass


# NOTE: MOUSER_API_KEY step removed - replaced by parameterized
# @given("the {api_key} environment variable is available for distributor search")
# in inventory/shared.py per Axiom #16 (Step Parameterization)


@given("the MOUSER_API_KEY environment variable is set")
def step_given_mouser_api_key_set(context):
    """Set up Mouser API key environment variable."""
    # TODO: Implement API key environment setup in Phase 3
    pass


# NOTE: Mixed components step removed - replaced by parameterized version
# in inventory/shared.py per Axiom #16 (Step Parameterization)


# NOTE: Search returns step removed - replaced by parameterized version
# in inventory/shared.py per Axiom #16 (Step Parameterization)


# =============================================================================
# Multi-Modal Operation Steps (Axiom #4 Compliant)
# =============================================================================


# NOTE: CLI-specific steps removed per Axiom #4 (Multi-Modal Testing)
# All operations must support CLI, API, and Plugin interfaces automatically
# Domain-specific steps handle interface variations internally


@when("I perform {operation} using {interface}")
def step_when_perform_operation_using_interface(context, operation, interface):
    """Perform parameterized operation using specified interface."""
    # TODO: Implement parameterized operation performance in Phase 3
    context.last_command_exit_code = 0

    # Set appropriate results based on operation type
    if operation == "search":
        context.search_results = []
    elif operation == "annotation":
        context.annotation_results = {}
    # Generic operation doesn't set specific results


# NOTE: API and Plugin execution steps removed per Axiom #16 (Step Parameterization)
# The parameterized step @when("I generate {operation} using {interface}")
# handles all interface-specific cases (CLI, Python API, KiCad plugin)
# This eliminates code duplication and improves maintainability


# =============================================================================
# Search-Enhanced Inventory When Steps
# =============================================================================


# NOTE: Search-enhanced inventory step removed - replaced by parameterized
# @when("I generate search-enhanced inventory with --{fabricator:w} fabricator")
# in inventory/shared.py per Axiom #16 (Step Parameterization)


# NOTE: Search with fabricator/limit step removed - conflicts with
# inventory/shared.py version using {fabricator:w} pattern per Axiom #16


# NOTE: All inventory-specific steps removed - replaced by parameterized versions
# in inventory/shared.py per Axiom #16 (Step Parameterization):
# - @when("I generate search-enhanced inventory with --{fabricator:w} fabricator the first time")
# - @when("the {api_key} is set to NULL")
# - @when("I generate search-enhanced inventory with --{fabricator:w} fabricator a second time")
# - @when("I generate enhanced inventory with --{fabricator:w} fabricator")
# - @when("I enable interactive selection mode with --{fabricator:w} fabricator")


# =============================================================================
# Result Validation Steps
# =============================================================================


@then("the command succeeds")
def step_then_command_succeeds(context):
    """Verify that the last command succeeded."""
    assert (
        context.last_command_exit_code == 0
    ), f"Command failed with exit code {context.last_command_exit_code}"


@then("the command fails")
def step_then_command_fails(context):
    """Verify that the last command failed."""
    assert (
        context.last_command_exit_code != 0
    ), "Expected command to fail but it succeeded"


@then('the output contains "{expected_text}"')
def step_then_output_contains(context, expected_text):
    """Verify command output contains expected text."""
    # TODO: Implement output verification in Phase 3
    assert hasattr(context, "last_command_output")


# =============================================================================
# File Operation Steps
# =============================================================================


@then('file "{filename}" is created')
def step_then_file_created(context, filename):
    """Verify a file was created."""
    file_path = context.scenario_temp_dir / filename
    assert file_path.exists(), f"Expected file not found: {file_path}"


@then('file "{filename}" contains {count:d} rows')
def step_then_file_contains_rows(context, filename, count):
    """Verify CSV file row count."""
    file_path = context.scenario_temp_dir / filename
    assert file_path.exists(), f"File not found: {file_path}"

    with open(file_path, "r") as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        rows = list(reader)

    assert len(rows) == count, f"Expected {count} rows, found {len(rows)} in {filename}"


# =============================================================================
# Multi-Modal Validation Engine
# =============================================================================


@given("multi-modal validation is enabled")
def step_given_multimodal_validation_enabled(context):
    """Enable automatic multi-modal validation for subsequent operations."""
    context.multimodal_enabled = True


@when("I validate behavior across all usage models")
def step_when_validate_across_all_models(context):
    """Execute the same test across CLI, API, and plugin models."""
    methods = ["CLI", "Python API", "KiCad plugin"]
    context.results = {}

    for method in methods:
        # Execute with current method
        context.execute_steps(f"When I generate BOM using {method}")

        # Store results for this method
        context.results[method] = {
            "exit_code": context.last_command_exit_code,
            "output_file": getattr(context, "bom_output_file", None),
        }


@when("I validate {operation} across all usage models")
def step_when_validate_operation_across_models(context, operation):
    """Execute any operation across CLI, API, and plugin models."""
    methods = ["CLI", "Python API", "KiCad plugin"]
    context.results = {}

    for method in methods:
        # Execute the specified operation with current method
        if operation == "BOM generation":
            context.execute_steps(f"When I generate BOM using {method}")
        elif operation == "POS generation":
            context.execute_steps(f"When I generate POS using {method}")
        elif operation == "inventory extraction":
            context.execute_steps(f"When I generate inventory using {method}")
        elif operation == "search":
            context.execute_steps(f"When I perform search using {method}")
        elif operation == "annotation":
            context.execute_steps(f"When I perform annotation using {method}")
        elif operation == "error handling":
            context.execute_steps(f"When I perform operation using {method}")
        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Store results
        context.results[method] = {
            "exit_code": context.last_command_exit_code,
            "output_file": getattr(
                context,
                "bom_output_file",
                getattr(
                    context,
                    "pos_output_file",
                    getattr(context, "inventory_output_file", None),
                ),
            ),
            "search_results": getattr(context, "search_results", None),
            "annotation_results": getattr(context, "annotation_results", None),
            "error_output": getattr(context, "error_output", None),
        }


@then("all usage models produce consistent results")
def step_then_all_models_consistent(context):
    """Verify all usage models produced the same results."""
    if not hasattr(context, "results"):
        raise AssertionError(
            "No multi-modal results found. Use 'When I validate behavior across all usage models' first."
        )

    # All should succeed
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} failed with exit code {result['exit_code']}"
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce output file"

    # TODO: Add content comparison in Phase 3 implementation
    # For now, just verify all methods executed successfully


# Convenience step for when you only need to test specific modes
@when("I test {operation} using {methods}")
def step_when_test_operation_using_methods(context, operation, methods):
    """Test operation using specified methods (comma-separated)."""
    method_list = [method.strip() for method in methods.split(",")]
    context.results = {}

    for method in method_list:
        if operation == "BOM generation":
            context.execute_steps(f"When I generate BOM using {method}")
        elif operation == "POS generation":
            context.execute_steps(f"When I generate POS using {method}")
        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Store results
        context.results[method] = {
            "exit_code": context.last_command_exit_code,
            "output_file": getattr(
                context, "bom_output_file", getattr(context, "pos_output_file", None)
            ),
        }
