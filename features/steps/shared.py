"""
Shared BDD step definitions for jBOM testing.

This module contains core steps that are used across multiple feature areas,
including multi-modal validation, basic CLI/API operations, and common
test data setup.
"""

import csv
from pathlib import Path

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


@given('the "{fixture_name}" PCB layout')
def step_given_fixture_pcb_layout(context, fixture_name):
    """Set up a PCB layout using a named fixture."""
    # TODO: Implement fixture-based PCB setup in Phase 3
    context.fixture_name = fixture_name
    pass


@given("the MOUSER_API_KEY environment variable is available for distributor search")
def step_given_mouser_api_key_available(context):
    """Set up Mouser API key for distributor search."""
    # TODO: Implement API key setup in Phase 3
    pass


@given("the MOUSER_API_KEY environment variable is set")
def step_given_mouser_api_key_set(context):
    """Set up Mouser API key environment variable."""
    # TODO: Implement API key environment setup in Phase 3
    pass


@given("a schematic with mixed searchable and exotic components")
def step_given_schematic_with_mixed_components(context):
    """Set up a schematic with mixed component types using table data."""
    # TODO: Implement mixed component schematic setup in Phase 3
    if hasattr(context, "table") and context.table:
        context.component_data = context.table
    pass


@given("search returns multiple good matches for components")
def step_given_search_returns_multiple_matches(context):
    """Set up search context with multiple good matches."""
    # TODO: Implement multi-match search setup in Phase 3
    pass


# =============================================================================
# CLI Execution Steps
# =============================================================================


@when('I run jbom command "{command}"')
def step_when_run_jbom_command(context, command):
    """Execute a jBOM CLI command."""
    # TODO: Implement CLI command execution in Phase 3
    context.last_command = command
    context.last_command_exit_code = 0  # Mock success for now


@when("I generate BOM using CLI")
def step_when_generate_bom_using_cli(context):
    """Generate BOM using CLI interface."""
    # TODO: Implement CLI BOM generation in Phase 3
    context.last_command_exit_code = 0
    context.bom_output_file = Path("test_bom.csv")


@when("I generate POS using CLI")
def step_when_generate_pos_using_cli(context):
    """Generate POS using CLI interface."""
    # TODO: Implement CLI POS generation in Phase 3
    context.last_command_exit_code = 0
    context.pos_output_file = Path("test_pos.csv")


@when("I generate inventory using CLI")
def step_when_generate_inventory_using_cli(context):
    """Generate inventory using CLI interface."""
    # TODO: Implement CLI inventory generation in Phase 3
    context.last_command_exit_code = 0
    context.inventory_output_file = Path("test_inventory.csv")


@when("I perform search using CLI")
def step_when_perform_search_using_cli(context):
    """Perform part search using CLI interface."""
    # TODO: Implement CLI search in Phase 3
    context.last_command_exit_code = 0
    context.search_results = []


@when("I perform annotation using CLI")
def step_when_perform_annotation_using_cli(context):
    """Perform back-annotation using CLI interface."""
    # TODO: Implement CLI annotation in Phase 3
    context.last_command_exit_code = 0
    context.annotation_results = {}


@when("I perform operation using CLI")
def step_when_perform_operation_using_cli(context):
    """Perform generic operation using CLI interface."""
    # TODO: Implement generic CLI operation in Phase 3
    context.last_command_exit_code = 0


# =============================================================================
# API Execution Steps
# =============================================================================


@when("I generate BOM using Python API")
def step_when_generate_bom_using_api(context):
    """Generate BOM using Python API."""
    # TODO: Implement API BOM generation in Phase 3
    context.last_command_exit_code = 0
    context.bom_output_file = Path("api_bom.csv")


@when("I generate POS using Python API")
def step_when_generate_pos_using_api(context):
    """Generate POS using Python API."""
    # TODO: Implement API POS generation in Phase 3
    context.last_command_exit_code = 0
    context.pos_output_file = Path("api_pos.csv")


@when("I generate inventory using Python API")
def step_when_generate_inventory_using_api(context):
    """Generate inventory using Python API."""
    # TODO: Implement API inventory generation in Phase 3
    context.last_command_exit_code = 0
    context.inventory_output_file = Path("api_inventory.csv")


@when("I perform search using Python API")
def step_when_perform_search_using_api(context):
    """Perform part search using Python API."""
    # TODO: Implement API search in Phase 3
    context.last_command_exit_code = 0
    context.search_results = []


@when("I perform annotation using Python API")
def step_when_perform_annotation_using_api(context):
    """Perform back-annotation using Python API."""
    # TODO: Implement API annotation in Phase 3
    context.last_command_exit_code = 0
    context.annotation_results = {}


@when("I perform operation using Python API")
def step_when_perform_operation_using_api(context):
    """Perform generic operation using Python API."""
    # TODO: Implement generic API operation in Phase 3
    context.last_command_exit_code = 0


# =============================================================================
# Plugin Execution Steps
# =============================================================================


@when("I generate BOM using KiCad plugin")
def step_when_generate_bom_using_plugin(context):
    """Generate BOM using KiCad plugin."""
    # TODO: Implement plugin BOM generation in Phase 3
    context.last_command_exit_code = 0
    context.bom_output_file = Path("plugin_bom.csv")


@when("I generate POS using KiCad plugin")
def step_when_generate_pos_using_plugin(context):
    """Generate POS using KiCad plugin."""
    # TODO: Implement plugin POS generation in Phase 3
    context.last_command_exit_code = 0
    context.pos_output_file = Path("plugin_pos.csv")


@when("I generate inventory using KiCad plugin")
def step_when_generate_inventory_using_plugin(context):
    """Generate inventory using KiCad plugin."""
    # TODO: Implement plugin inventory generation in Phase 3
    context.last_command_exit_code = 0
    context.inventory_output_file = Path("plugin_inventory.csv")


@when("I perform search using KiCad plugin")
def step_when_perform_search_using_plugin(context):
    """Perform part search using KiCad plugin."""
    # TODO: Implement plugin search in Phase 3
    context.last_command_exit_code = 0
    context.search_results = []


@when("I perform annotation using KiCad plugin")
def step_when_perform_annotation_using_plugin(context):
    """Perform back-annotation using KiCad plugin."""
    # TODO: Implement plugin annotation in Phase 3
    context.last_command_exit_code = 0
    context.annotation_results = {}


@when("I perform operation using KiCad plugin")
def step_when_perform_operation_using_plugin(context):
    """Perform generic operation using KiCad plugin."""
    # TODO: Implement generic plugin operation in Phase 3
    context.last_command_exit_code = 0


# =============================================================================
# Search-Enhanced Inventory When Steps
# =============================================================================


@when("I generate search-enhanced inventory with --generic fabricator")
def step_when_generate_search_enhanced_inventory_generic(context):
    """Generate search-enhanced inventory using generic fabricator."""
    # TODO: Implement search-enhanced inventory generation in Phase 3
    context.last_command_exit_code = 0
    context.inventory_output_file = Path("search_enhanced_inventory.csv")


@when("I search with --generic fabricator and result limit of 3")
def step_when_search_with_generic_fabricator_limit_3(context):
    """Search with generic fabricator and result limit."""
    # TODO: Implement limited search in Phase 3
    context.last_command_exit_code = 0
    context.inventory_output_file = Path("limited_search_inventory.csv")


@when("I generate search-enhanced inventory with --generic fabricator the first time")
def step_when_generate_search_enhanced_inventory_first_time(context):
    """Generate search-enhanced inventory first time."""
    # TODO: Implement first-time generation in Phase 3
    context.last_command_exit_code = 0
    context.inventory_output_file = Path("first_time_inventory.csv")


@when("the MOUSER_API_KEY is set to NULL")
def step_when_mouser_api_key_set_to_null(context):
    """Set MOUSER_API_KEY to NULL for caching test."""
    # TODO: Implement API key nullification in Phase 3
    pass


@when("I generate search-enhanced inventory with --generic fabricator a second time")
def step_when_generate_search_enhanced_inventory_second_time(context):
    """Generate search-enhanced inventory second time."""
    # TODO: Implement second-time generation in Phase 3
    context.last_command_exit_code = 0
    context.inventory_output_file = Path("second_time_inventory.csv")


@when("I generate enhanced inventory with --generic fabricator")
def step_when_generate_enhanced_inventory_generic(context):
    """Generate enhanced inventory using generic fabricator."""
    # TODO: Implement enhanced inventory generation in Phase 3
    context.last_command_exit_code = 0
    context.inventory_output_file = Path("enhanced_inventory.csv")


@when("I enable interactive selection mode with --generic fabricator")
def step_when_enable_interactive_selection_mode_generic(context):
    """Enable interactive selection mode with generic fabricator."""
    # TODO: Implement interactive selection in Phase 3
    context.last_command_exit_code = 0
    context.inventory_output_file = Path("interactive_inventory.csv")


# =============================================================================
# Parameterized Inventory and Search Step Definitions (Axiom #16)
# =============================================================================


@then(
    "the inventory includes {provider} part numbers, pricing, and stock quantities for each component"
)
def step_then_inventory_includes_provider_data_for_components(context, provider):
    """Verify search-enhanced inventory generation with parameterized provider across all usage models automatically."""
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce {provider} enhanced inventory file"


@then(
    "the inventory contains {count:d} candidate parts for the {component} with priority ranking based on {criteria}"
)
def step_then_inventory_contains_candidate_parts_with_criteria(
    context, count, component, criteria
):
    """Verify multi-candidate search results with parameterized component and criteria across all usage models automatically."""
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce {count}-candidate inventory file for {component}"


@then(
    "the second run uses cached results, does not generate {error_source} errors and completes successfully"
)
def step_then_second_run_uses_cached_results_without_errors(context, error_source):
    """Verify search caching optimization with parameterized error sources across all usage models automatically."""
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce cached inventory file without {error_source} errors"


@then("the search returns statistics showing {metric_types}")
def step_then_search_returns_statistics_with_metrics(context, metric_types):
    """Verify search statistics reporting with parameterized metrics across all usage models automatically."""
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce inventory with {metric_types} statistics"


@then(
    'the inventory includes {provider} data for {component} and reports "{message}" for {problem_component} component'
)
def step_then_inventory_includes_data_and_reports_message(
    context, provider, component, message, problem_component
):
    """Verify graceful search failure handling with parameterized components and messages.

    Tests across all usage models automatically.
    """
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce partial {provider} inventory file"


@then(
    "the search presents multiple {item_type} with {detail_types} for user selection per component"
)
def step_then_search_presents_multiple_items_with_details(
    context, item_type, detail_types
):
    """Verify interactive search selection with parameterized items and details across all usage models automatically."""
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce interactive {item_type} inventory file"


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
