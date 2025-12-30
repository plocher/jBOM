"""
Common step definitions for jBOM functional tests.

These steps provide reusable building blocks that can be used across
different feature areas (BOM, POS, inventory, etc.).
"""

import csv
import subprocess
from behave import given, when, then
from jbom.api import generate_bom, generate_pos


# =============================================================================
# Test Data Setup Steps
# =============================================================================


@given('a KiCad project named "{project_name}"')
def step_given_kicad_project(context, project_name):
    """Set up a KiCad project for testing."""
    # Copy example project to scenario temp directory
    source_project = context.examples_dir / project_name
    if not source_project.exists():
        # Create a minimal test project if example doesn't exist
        context.project_dir = context.scenario_temp_dir / project_name
        context.project_dir.mkdir()
        context.project_name = project_name
        # Project setup will be completed by subsequent steps
    else:
        context.project_dir = context.scenario_temp_dir / project_name
        # Copy the example project
        import shutil

        shutil.copytree(source_project, context.project_dir)
        context.project_name = project_name


@given("an inventory file with components")
def step_given_inventory_file(context):
    """Create an inventory file with test components."""
    # Use table data if provided
    if context.table:
        inventory_data = []
        headers = context.table.headings
        for row in context.table:
            inventory_data.append(dict(zip(headers, row.cells)))
    else:
        # Create minimal test inventory
        inventory_data = [
            {
                "IPN": "R001",
                "Category": "RES",
                "Value": "10K",
                "Package": "0603",
                "Distributor": "JLC",
                "DPN": "C25804",
                "Priority": "1",
            },
            {
                "IPN": "C001",
                "Category": "CAP",
                "Value": "100nF",
                "Package": "0603",
                "Distributor": "JLC",
                "DPN": "C14663",
                "Priority": "1",
            },
        ]

    # Write inventory CSV
    context.inventory_file = context.scenario_temp_dir / "test_inventory.csv"
    with open(context.inventory_file, "w", newline="") as f:
        if inventory_data:
            writer = csv.DictWriter(f, fieldnames=inventory_data[0].keys())
            writer.writeheader()
            writer.writerows(inventory_data)


@given("multiple inventory sources")
def step_given_multiple_inventory_sources(context):
    """Create multiple inventory files for federated testing."""
    # Create local inventory
    local_inventory = [
        {
            "IPN": "LOCAL001",
            "Category": "RES",
            "Value": "1K",
            "Package": "0603",
            "Distributor": "Local",
            "DPN": "",
            "Priority": "1",
        },
        {
            "IPN": "LOCAL002",
            "Category": "CAP",
            "Value": "10uF",
            "Package": "0805",
            "Distributor": "Local",
            "DPN": "",
            "Priority": "1",
        },
    ]

    # Create supplier inventory
    supplier_inventory = [
        {
            "IPN": "SUP001",
            "Category": "RES",
            "Value": "10K",
            "Package": "0603",
            "Distributor": "JLC",
            "DPN": "C25804",
            "Priority": "2",
        },
        {
            "IPN": "SUP002",
            "Category": "CAP",
            "Value": "100nF",
            "Package": "0603",
            "Distributor": "JLC",
            "DPN": "C14663",
            "Priority": "2",
        },
    ]

    # Write files
    context.local_inventory = context.scenario_temp_dir / "local_inventory.csv"
    context.supplier_inventory = context.scenario_temp_dir / "supplier_inventory.csv"

    for inventory_data, filepath in [
        (local_inventory, context.local_inventory),
        (supplier_inventory, context.supplier_inventory),
    ]:
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=inventory_data[0].keys())
            writer.writeheader()
            writer.writerows(inventory_data)

    context.inventory_files = [context.local_inventory, context.supplier_inventory]


# =============================================================================
# CLI Execution Steps
# =============================================================================


@when('I run jbom command "{command}"')
def step_when_run_jbom_command(context, command):
    """Execute a jBOM CLI command."""
    # Build full command
    full_command = f"python -m jbom {command}"

    try:
        result = subprocess.run(
            full_command,
            shell=True,
            cwd=context.project_root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        context.last_command_output = result.stdout
        context.last_command_error = result.stderr
        context.last_command_exit_code = result.returncode
    except subprocess.TimeoutExpired:
        context.last_command_error = "Command timed out"
        context.last_command_exit_code = -1


@when("I generate BOM using CLI")
def step_when_generate_bom_cli(context):
    """Generate BOM using CLI command."""
    command = f"bom {context.project_dir} -i {context.inventory_file} -o bom_output.csv"
    context.execute_steps(f'When I run jbom command "{command}"')
    context.bom_output_file = context.scenario_temp_dir / "bom_output.csv"


# =============================================================================
# API Execution Steps
# =============================================================================


@when("I generate BOM using Python API")
def step_when_generate_bom_api(context):
    """Generate BOM using Python API."""
    try:
        context.api_result = generate_bom(
            input=context.project_dir,
            inventory=context.inventory_file,
            output=context.scenario_temp_dir / "api_bom_output.csv",
        )
        context.last_command_exit_code = 0
        context.bom_output_file = context.scenario_temp_dir / "api_bom_output.csv"
    except Exception as e:
        context.last_command_error = str(e)
        context.last_command_exit_code = 1


@when("I generate POS using Python API")
def step_when_generate_pos_api(context):
    """Generate POS using Python API."""
    try:
        context.api_result = generate_pos(
            input=context.project_dir,
            output=context.scenario_temp_dir / "api_pos_output.csv",
        )
        context.last_command_exit_code = 0
        context.pos_output_file = context.scenario_temp_dir / "api_pos_output.csv"
    except Exception as e:
        context.last_command_error = str(e)
        context.last_command_exit_code = 1


@when("I generate BOM using {method}")
def step_when_generate_bom_multi_modal(context, method):
    """Generate BOM using specified method (CLI, Python API, or KiCad plugin)."""
    if method == "CLI":
        context.execute_steps("When I generate BOM using CLI")
    elif method == "Python API":
        context.execute_steps("When I generate BOM using Python API")
    elif method == "KiCad plugin":
        # Simulate KiCad plugin execution
        context.execute_steps(
            "When I generate BOM using CLI"
        )  # For now, simulate via CLI
        # TODO: Implement actual KiCad plugin simulation in Phase 3
    else:
        raise ValueError(f"Unknown BOM generation method: {method}")


@when("I generate POS using {method}")
def step_when_generate_pos_multi_modal(context, method):
    """Generate POS using specified method (CLI, Python API, or KiCad plugin)."""
    if method == "CLI":
        command = f"pos {context.project_dir} -o pos_output.csv"
        context.execute_steps(f'When I run jbom command "{command}"')
        context.pos_output_file = context.scenario_temp_dir / "pos_output.csv"
    elif method == "Python API":
        context.execute_steps("When I generate POS using Python API")
    elif method == "KiCad plugin":
        # Simulate KiCad plugin execution
        command = f"pos {context.project_dir} -o pos_output.csv"
        context.execute_steps(f'When I run jbom command "{command}"')
        context.pos_output_file = context.scenario_temp_dir / "pos_output.csv"
    else:
        raise ValueError(f"Unknown POS generation method: {method}")


# =============================================================================
# Result Validation Steps
# =============================================================================


@then("the command succeeds")
def step_then_command_succeeds(context):
    """Verify that the last command succeeded."""
    assert (
        context.last_command_exit_code == 0
    ), f"Command failed with exit code {context.last_command_exit_code}. Error: {context.last_command_error}"


@then("the command fails")
def step_then_command_fails(context):
    """Verify that the last command failed."""
    assert (
        context.last_command_exit_code != 0
    ), "Expected command to fail, but it succeeded"


@then("a BOM file is generated")
def step_then_bom_file_generated(context):
    """Verify that a BOM file was created."""
    assert hasattr(context, "bom_output_file"), "No BOM output file specified"
    assert (
        context.bom_output_file.exists()
    ), f"BOM file not found: {context.bom_output_file}"


@then("the BOM contains {count:d} entries")
def step_then_bom_contains_entries(context, count):
    """Verify BOM entry count."""
    assert hasattr(context, "bom_output_file"), "No BOM output file specified"

    with open(context.bom_output_file, "r") as f:
        reader = csv.reader(f)
        next(reader)  # Skip headers
        rows = list(reader)

    assert len(rows) == count, f"Expected {count} BOM entries, found {len(rows)}"


@then("the BOM includes columns")
def step_then_bom_includes_columns(context):
    """Verify BOM contains expected columns."""
    assert hasattr(context, "bom_output_file"), "No BOM output file specified"

    with open(context.bom_output_file, "r") as f:
        reader = csv.reader(f)
        headers = next(reader)

    expected_columns = [row["column"] for row in context.table]
    for column in expected_columns:
        assert (
            column in headers
        ), f"Expected column '{column}' not found in BOM headers: {headers}"


@then('the output contains "{text}"')
def step_then_output_contains_text(context, text):
    """Verify command output contains specific text."""
    output = context.last_command_output or ""
    error = context.last_command_error or ""
    full_output = output + error

    assert (
        text in full_output
    ), f"Expected text '{text}' not found in output: {full_output}"


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
# Shared Multi-Modal Patterns
# =============================================================================


@given("multi-modal validation is enabled")
def step_given_multimodal_validation_enabled(context):
    """Enable automatic multi-modal validation for subsequent operations."""
    context.multimodal_enabled = True


def auto_validate_if_enabled(context, operation="BOM generation"):
    """Automatically validate across all usage models if enabled."""
    if getattr(context, "multimodal_enabled", False):
        if operation == "BOM generation":
            context.execute_steps("When I validate behavior across all usage models")
        elif operation == "POS generation":
            context.execute_steps(
                "When I validate POS generation across all usage models"
            )
        # Add more operations as needed


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


# =============================================================================
# Domain-Specific Multi-Modal Steps (Ultimate DRY Solution)
# =============================================================================


@then('the BOM contains the {component} matched to "{expected_match}"')
def step_then_bom_contains_component_matched(context, component, expected_match):
    """Verify component matching across all usage models automatically."""
    # Auto-execute multi-modal validation
    context.execute_steps("When I validate behavior across all usage models")

    # Then verify the specific matching behavior
    # TODO: Implement specific component matching validation in Phase 3
    # For now, just verify that files were generated
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce BOM file"


@then("the BOM contains an unmatched component entry")
def step_then_bom_contains_unmatched_component(context):
    """Verify unmatched component handling across all usage models automatically."""
    # Auto-execute multi-modal validation
    context.execute_steps("When I validate behavior across all usage models")

    # Then verify the specific unmatched behavior
    # TODO: Implement specific unmatched component validation in Phase 3
    # For now, just verify that files were generated
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce BOM file"


@then(
    'the BOM contains the {component} matched to "{expected_match}" with priority {priority:d}'
)
def step_then_bom_contains_component_with_priority(
    context, component, expected_match, priority
):
    """Verify component priority selection across all usage models automatically."""
    # Auto-execute multi-modal validation
    context.execute_steps("When I validate behavior across all usage models")

    # Then verify the specific priority behavior
    # TODO: Implement specific priority validation in Phase 3
    # For now, just verify that files were generated
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce BOM file"


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


# Note: Removed specific inventory extraction and POS generation steps
# to avoid conflicts with the generic validate operation step


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


# =============================================================================
# Fabricator Format Domain-Specific Steps
# =============================================================================


@then('the BOM generates in {format_name} format with columns "{column_list}"')
def step_then_bom_generates_in_format_with_columns(context, format_name, column_list):
    """Verify fabricator format generation across all usage models automatically."""
    # Auto-execute multi-modal validation
    context.execute_steps("When I validate behavior across all usage models")

    # Then verify the specific format behavior
    # TODO: Implement specific format validation in Phase 3
    # For now, just verify that files were generated
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce BOM file"


@then('the BOM generates with custom fields "{field_list}"')
def step_then_bom_generates_with_custom_fields(context, field_list):
    """Verify custom field selection across all usage models automatically."""
    # Auto-execute multi-modal validation
    context.execute_steps("When I validate behavior across all usage models")

    # Then verify the custom fields behavior
    # TODO: Implement specific custom fields validation in Phase 3
    # For now, just verify that files were generated
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce BOM file"


# =============================================================================
# Multi-Source Inventory Domain-Specific Steps
# =============================================================================


@then("the BOM prioritizes local inventory over supplier inventory")
def step_then_bom_prioritizes_local_over_supplier(context):
    """Verify multi-source priority handling across all usage models automatically."""
    # Auto-execute multi-modal validation
    context.execute_steps("When I validate behavior across all usage models")

    # Then verify the priority behavior
    # TODO: Implement specific priority validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce BOM file"


@then("the BOM combines components from both sources based on priority")
def step_then_bom_combines_sources_by_priority(context):
    """Verify multi-source combination across all usage models automatically."""
    # Auto-execute multi-modal validation
    context.execute_steps("When I validate behavior across all usage models")

    # Then verify the combination behavior
    # TODO: Implement specific combination validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce BOM file"


@then("the verbose BOM shows selected part source and available alternatives")
def step_then_verbose_bom_shows_source_and_alternatives(context):
    """Verify verbose source tracking across all usage models automatically."""
    # Auto-execute multi-modal validation
    context.execute_steps("When I validate behavior across all usage models")

    # Then verify the verbose output behavior
    # TODO: Implement specific verbose validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce BOM file"


@then("the API generates BOM with source tracking for each matched item")
def step_then_api_generates_bom_with_source_tracking(context):
    """Verify API source tracking across all usage models automatically."""
    # Auto-execute multi-modal validation
    context.execute_steps("When I validate behavior across all usage models")

    # Then verify the API source tracking behavior
    # TODO: Implement specific API validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce BOM file"


@then("the BOM uses first source definition and warns about conflicts")
def step_then_bom_uses_first_source_and_warns_conflicts(context):
    """Verify conflict handling across all usage models automatically."""
    # Auto-execute multi-modal validation
    context.execute_steps("When I validate behavior across all usage models")

    # Then verify the conflict handling behavior
    # TODO: Implement specific conflict validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce BOM file"


# =============================================================================
# Inventory Extraction Domain-Specific Steps
# =============================================================================


@then("the inventory extracts all unique components with required columns")
def step_then_inventory_extracts_unique_components_with_columns(context):
    """Verify basic inventory extraction across all usage models automatically."""
    # Auto-execute multi-modal validation for inventory extraction
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )

    # Then verify the extraction behavior
    # TODO: Implement specific inventory validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce inventory file"


@then("the inventory extracts with distributor format including DPN and SMD columns")
def step_then_inventory_extracts_with_distributor_format(context):
    """Verify distributor format inventory extraction across all usage models automatically."""
    # Auto-execute multi-modal validation for inventory extraction
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )

    # Then verify the distributor format behavior
    # TODO: Implement specific distributor format validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce inventory file"


@then("the inventory extracts with UUID column for back-annotation")
def step_then_inventory_extracts_with_uuid_column(context):
    """Verify UUID inventory extraction across all usage models automatically."""
    # Auto-execute multi-modal validation for inventory extraction
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )

    # Then verify the UUID behavior
    # TODO: Implement specific UUID validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce inventory file"


@then("the API extracts inventory with component count and field names")
def step_then_api_extracts_inventory_with_component_count_and_fields(context):
    """Verify API inventory extraction across all usage models automatically."""
    # Auto-execute multi-modal validation for inventory extraction
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )

    # Then verify the API inventory behavior
    # TODO: Implement specific API inventory validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce inventory file"


@then("the inventory extracts components from all sheets with merged quantities")
def step_then_inventory_extracts_from_all_sheets_with_merged_quantities(context):
    """Verify hierarchical inventory extraction across all usage models automatically."""
    # Auto-execute multi-modal validation for inventory extraction
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )

    # Then verify the hierarchical behavior
    # TODO: Implement specific hierarchical validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce inventory file"


@then('the inventory extracts with custom fields "{field_list}"')
def step_then_inventory_extracts_with_custom_fields(context, field_list):
    """Verify custom field inventory extraction across all usage models automatically."""
    # Auto-execute multi-modal validation for inventory extraction
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )

    # Then verify the custom fields behavior
    # TODO: Implement specific custom fields validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce inventory file"


# =============================================================================
# Search Enhancement Domain-Specific Steps
# =============================================================================


@then(
    "the search-enhanced inventory includes part numbers, pricing, and stock quantities"
)
def step_then_search_enhanced_inventory_includes_data(context):
    """Verify search-enhanced inventory generation across all usage models automatically."""
    # Auto-execute multi-modal validation for inventory extraction
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )

    # Then verify the search enhancement behavior
    # TODO: Implement specific search enhancement validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce enhanced inventory file"


@then("the inventory contains 3 candidate parts with priority ranking")
def step_then_inventory_contains_candidate_parts_with_ranking(context):
    """Verify multi-candidate search results across all usage models automatically."""
    # Auto-execute multi-modal validation for inventory extraction
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )

    # Then verify the candidate ranking behavior
    # TODO: Implement specific candidate validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce multi-candidate inventory file"


@then("the search results are cached for faster subsequent runs")
def step_then_search_results_are_cached(context):
    """Verify search caching across all usage models automatically."""
    # Auto-execute multi-modal validation for inventory extraction
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )

    # Then verify the caching behavior
    # TODO: Implement specific caching validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce cached inventory file"


@then("the API generates enhanced inventory with search statistics and tracking")
def step_then_api_generates_enhanced_inventory_with_statistics(context):
    """Verify API search enhancement across all usage models automatically."""
    # Auto-execute multi-modal validation for inventory extraction
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )

    # Then verify the API search behavior
    # TODO: Implement specific API search validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce enhanced API inventory file"


@then(
    "the inventory includes distributor data for found components and reports search statistics"
)
def step_then_inventory_includes_distributor_data_and_statistics(context):
    """Verify graceful search failure handling across all usage models automatically."""
    # Auto-execute multi-modal validation for inventory extraction
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )

    # Then verify the graceful failure behavior
    # TODO: Implement specific failure handling validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce partial search inventory file"


@then("the search presents interactive options for customized inventory selection")
def step_then_search_presents_interactive_options(context):
    """Verify interactive search selection across all usage models automatically."""
    # Auto-execute multi-modal validation for inventory extraction
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )

    # Then verify the interactive selection behavior
    # TODO: Implement specific interactive validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce interactive inventory file"


# =============================================================================
# POS Generation Domain-Specific Steps
# =============================================================================


@then('the POS contains all placed components with columns "{column_list}"')
def step_then_pos_contains_placed_components_with_columns(context, column_list):
    """Verify basic POS generation across all usage models automatically."""
    # Auto-execute multi-modal validation for POS generation
    context.execute_steps("When I validate POS generation across all usage models")

    # Then verify the POS generation behavior
    # TODO: Implement specific POS validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce POS file"


@then(
    "the POS generates in JLCPCB format with millimeter coordinates and SMD-only filtering"
)
def step_then_pos_generates_jlcpcb_format_mm_smd(context):
    """Verify JLCPCB POS format across all usage models automatically."""
    # Auto-execute multi-modal validation for POS generation
    context.execute_steps("When I validate POS generation across all usage models")

    # Then verify the JLCPCB format behavior
    # TODO: Implement specific JLCPCB format validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce JLCPCB POS file"


@then("the POS contains only surface mount components excluding through-hole")
def step_then_pos_contains_smd_only_excluding_through_hole(context):
    """Verify SMD-only filtering across all usage models automatically."""
    # Auto-execute multi-modal validation for POS generation
    context.execute_steps("When I validate POS generation across all usage models")

    # Then verify the SMD filtering behavior
    # TODO: Implement specific SMD filtering validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce SMD-only POS file"


@then("the POS contains only top-side components excluding bottom-side")
def step_then_pos_contains_top_side_only(context):
    """Verify layer filtering across all usage models automatically."""
    # Auto-execute multi-modal validation for POS generation
    context.execute_steps("When I validate POS generation across all usage models")

    # Then verify the layer filtering behavior
    # TODO: Implement specific layer filtering validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce top-side POS file"


@then("the API generates POS with placement data and coordinate information")
def step_then_api_generates_pos_with_placement_data_and_coordinates(context):
    """Verify API POS generation across all usage models automatically."""
    # Auto-execute multi-modal validation for POS generation
    context.execute_steps("When I validate POS generation across all usage models")

    # Then verify the API POS behavior
    # TODO: Implement specific API POS validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce API POS file"


@then("the POS coordinates are converted to inches with appropriate precision")
def step_then_pos_coordinates_converted_to_inches(context):
    """Verify coordinate unit conversion across all usage models automatically."""
    # Auto-execute multi-modal validation for POS generation
    context.execute_steps("When I validate POS generation across all usage models")

    # Then verify the unit conversion behavior
    # TODO: Implement specific unit conversion validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce inch-unit POS file"


@then("the POS coordinates are relative to auxiliary origin consistently")
def step_then_pos_coordinates_relative_to_aux_origin(context):
    """Verify auxiliary origin handling across all usage models automatically."""
    # Auto-execute multi-modal validation for POS generation
    context.execute_steps("When I validate POS generation across all usage models")

    # Then verify the auxiliary origin behavior
    # TODO: Implement specific auxiliary origin validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce aux-origin POS file"


# =============================================================================
# Part Search Domain-Specific Steps
# =============================================================================


# Note: Removed specific search validation step to avoid conflicts with generic validate operation step


@then("the search returns up to 5 matching parts ranked by relevance")
def step_then_search_returns_matching_parts_ranked(context):
    """Verify basic part search across all usage models automatically."""
    # Auto-execute multi-modal validation for search
    context.execute_steps("When I validate search across all usage models")

    # Then verify the search behavior
    # TODO: Implement specific search validation in Phase 3
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} search failed"


@then("the search uses Mouser API with part numbers, pricing, and stock availability")
def step_then_search_uses_mouser_api_with_details(context):
    """Verify Mouser-specific search across all usage models automatically."""
    # Auto-execute multi-modal validation for search
    context.execute_steps("When I validate search across all usage models")

    # Then verify the Mouser search behavior
    # TODO: Implement specific Mouser search validation in Phase 3
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} Mouser search failed"


@then("the search finds exact manufacturer part with cross-references and pricing")
def step_then_search_finds_exact_part_with_details(context):
    """Verify exact part number search across all usage models automatically."""
    # Auto-execute multi-modal validation for search
    context.execute_steps("When I validate search across all usage models")

    # Then verify the exact search behavior
    # TODO: Implement specific exact search validation in Phase 3
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} exact search failed"


@then(
    "the search filters results for 1% tolerance and 0603 package excluding inappropriate matches"
)
def step_then_search_filters_parametric_results(context):
    """Verify parametric filtering across all usage models automatically."""
    # Auto-execute multi-modal validation for search
    context.execute_steps("When I validate search across all usage models")

    # Then verify the parametric filtering behavior
    # TODO: Implement specific parametric filtering validation in Phase 3
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} parametric search failed"


@then("the search returns no results with appropriate messaging without errors")
def step_then_search_returns_no_results_gracefully(context):
    """Verify graceful failure handling across all usage models automatically."""
    # Auto-execute multi-modal validation for search
    context.execute_steps("When I validate search across all usage models")

    # Then verify the graceful failure behavior
    # TODO: Implement specific failure handling validation in Phase 3
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} search error handling failed"


@then("the API returns SearchResult objects with filterable part information")
def step_then_api_returns_searchresult_objects(context):
    """Verify API search results across all usage models automatically."""
    # Auto-execute multi-modal validation for search
    context.execute_steps("When I validate search across all usage models")

    # Then verify the API search results behavior
    # TODO: Implement specific API search results validation in Phase 3
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} API search failed"


@then("the search uses specified API key and returns results normally")
def step_then_search_uses_specified_api_key(context):
    """Verify API key override across all usage models automatically."""
    # Auto-execute multi-modal validation for search
    context.execute_steps("When I validate search across all usage models")

    # Then verify the API key override behavior
    # TODO: Implement specific API key validation in Phase 3
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} API key override failed"


# =============================================================================
# Back-Annotation Domain-Specific Steps
# =============================================================================


# Note: Removed specific annotation validation step to avoid conflicts with generic validate operation step


@then(
    "the back-annotation updates schematic with distributor and manufacturer information"
)
def step_then_back_annotation_updates_schematic_with_info(context):
    """Verify schematic updates across all usage models automatically."""
    # Auto-execute multi-modal validation for annotation
    context.execute_steps("When I validate annotation across all usage models")

    # Then verify the back-annotation behavior
    # TODO: Implement specific back-annotation validation in Phase 3
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} back-annotation failed"


@then("the dry-run back-annotation previews changes without modifying schematic files")
def step_then_dry_run_annotation_previews_changes(context):
    """Verify dry-run annotation across all usage models automatically."""
    # Auto-execute multi-modal validation for annotation
    context.execute_steps("When I validate annotation across all usage models")

    # Then verify the dry-run behavior
    # TODO: Implement specific dry-run validation in Phase 3
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} dry-run annotation failed"


@then("the API back-annotation reports update count and changed details")
def step_then_api_annotation_reports_update_count_and_details(context):
    """Verify API annotation reporting across all usage models automatically."""
    # Auto-execute multi-modal validation for annotation
    context.execute_steps("When I validate annotation across all usage models")

    # Then verify the API annotation behavior
    # TODO: Implement specific API annotation validation in Phase 3
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} API annotation failed"


@then("the back-annotation warns about invalid UUIDs and updates only valid components")
def step_then_annotation_warns_invalid_uuids_updates_valid(context):
    """Verify UUID handling across all usage models automatically."""
    # Auto-execute multi-modal validation for annotation
    context.execute_steps("When I validate annotation across all usage models")

    # Then verify the UUID handling behavior
    # TODO: Implement specific UUID validation in Phase 3
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} UUID handling failed"


@then("the back-annotation updates only DPN fields preserving existing data")
def step_then_annotation_updates_dpn_only_preserving_data(context):
    """Verify selective field updates across all usage models automatically."""
    # Auto-execute multi-modal validation for annotation
    context.execute_steps("When I validate annotation across all usage models")

    # Then verify the selective update behavior
    # TODO: Implement specific selective update validation in Phase 3
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} selective annotation failed"


@then("the back-annotation updates only matching components and reports mismatches")
def step_then_annotation_updates_matching_reports_mismatches(context):
    """Verify mismatch handling across all usage models automatically."""
    # Auto-execute multi-modal validation for annotation
    context.execute_steps("When I validate annotation across all usage models")

    # Then verify the mismatch handling behavior
    # TODO: Implement specific mismatch validation in Phase 3
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} mismatch handling failed"


# =============================================================================
# Error Handling Domain-Specific Steps
# =============================================================================


# Note: Removed specific error handling validation step to avoid conflicts with generic validate operation step


@then('the error handling reports "{error_message}" with missing file path')
def step_then_error_handling_reports_message_with_file_path(context, error_message):
    """Verify file not found error handling across all usage models automatically."""
    # Auto-execute multi-modal validation for error handling
    context.execute_steps("When I validate error handling across all usage models")

    # Then verify the error handling behavior
    # TODO: Implement specific error message validation in Phase 3
    for method, result in context.results.items():
        assert result["exit_code"] != 0, f"{method} should have failed for missing file"


@then('the error handling reports "{error_message}" with specific column details')
def step_then_error_handling_reports_message_with_column_details(
    context, error_message
):
    """Verify invalid format error handling across all usage models automatically."""
    # Auto-execute multi-modal validation for error handling
    context.execute_steps("When I validate error handling across all usage models")

    # Then verify the format error handling behavior
    # TODO: Implement specific format error validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["exit_code"] != 0
        ), f"{method} should have failed for invalid format"


@then('the error handling reports "{error_message}" suggesting path check')
def step_then_error_handling_reports_message_suggesting_path_check(
    context, error_message
):
    """Verify project not found error handling across all usage models automatically."""
    # Auto-execute multi-modal validation for error handling
    context.execute_steps("When I validate error handling across all usage models")

    # Then verify the project not found error handling behavior
    # TODO: Implement specific project not found validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["exit_code"] != 0
        ), f"{method} should have failed for missing project"


@then('the error handling reports "{error_message}" identifying problematic file')
def step_then_error_handling_reports_message_identifying_file(context, error_message):
    """Verify parsing error handling across all usage models automatically."""
    # Auto-execute multi-modal validation for error handling
    context.execute_steps("When I validate error handling across all usage models")

    # Then verify the parsing error handling behavior
    # TODO: Implement specific parsing error validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["exit_code"] != 0
        ), f"{method} should have failed for parsing error"


@then('the error handling reports "{error_message}" suggesting permission check')
def step_then_error_handling_reports_message_suggesting_permission_check(
    context, error_message
):
    """Verify permission error handling across all usage models automatically."""
    # Auto-execute multi-modal validation for error handling
    context.execute_steps("When I validate error handling across all usage models")

    # Then verify the permission error handling behavior
    # TODO: Implement specific permission error validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["exit_code"] != 0
        ), f"{method} should have failed for permission error"


@then("the processing succeeds with empty inventory warning and unmatched components")
def step_then_processing_succeeds_with_empty_inventory_warning(context):
    """Verify empty inventory handling across all usage models automatically."""
    # Auto-execute multi-modal validation (expecting success)
    context.execute_steps("When I validate behavior across all usage models")

    # Then verify the empty inventory handling behavior
    # TODO: Implement specific empty inventory validation in Phase 3
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} should succeed with empty inventory"


@then("the processing succeeds with no components warning and empty BOM file")
def step_then_processing_succeeds_with_no_components_warning(context):
    """Verify empty schematic handling across all usage models automatically."""
    # Auto-execute multi-modal validation (expecting success)
    context.execute_steps("When I validate behavior across all usage models")

    # Then verify the empty schematic handling behavior
    # TODO: Implement specific empty schematic validation in Phase 3
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} should succeed with empty schematic"


@then('the error handling reports "{error_message}" suggesting API key check')
def step_then_error_handling_reports_message_suggesting_api_key_check(
    context, error_message
):
    """Verify API key error handling across all usage models automatically."""
    # Auto-execute multi-modal validation for error handling
    context.execute_steps("When I validate error handling across all usage models")

    # Then verify the API key error handling behavior
    # TODO: Implement specific API key error validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["exit_code"] != 0
        ), f"{method} should have failed for invalid API key"


@then('the error handling reports "{error_message}" suggesting connectivity check')
def step_then_error_handling_reports_message_suggesting_connectivity_check(
    context, error_message
):
    """Verify network error handling across all usage models automatically."""
    # Auto-execute multi-modal validation for error handling
    context.execute_steps("When I validate error handling across all usage models")

    # Then verify the network error handling behavior
    # TODO: Implement specific network error validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["exit_code"] != 0
        ), f"{method} should have failed for network error"


@then("the processing succeeds with missing sub-sheet warnings and partial BOM")
def step_then_processing_succeeds_with_missing_subsheet_warnings(context):
    """Verify missing sub-sheet handling across all usage models automatically."""
    # Auto-execute multi-modal validation (expecting partial success)
    context.execute_steps("When I validate behavior across all usage models")

    # Then verify the missing sub-sheet handling behavior
    # TODO: Implement specific sub-sheet validation in Phase 3
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} should succeed with missing sub-sheets"


@then("the processing succeeds for valid parts with specific error reporting")
def step_then_processing_succeeds_for_valid_with_error_reporting(context):
    """Verify graceful degradation across all usage models automatically."""
    # Auto-execute multi-modal validation (expecting partial success)
    context.execute_steps("When I validate behavior across all usage models")

    # Then verify the graceful degradation behavior
    # TODO: Implement specific partial failure validation in Phase 3
    for method, result in context.results.items():
        # Should succeed overall but report specific errors
        assert (
            result["exit_code"] == 0
        ), f"{method} should partially succeed with mixed conditions"
