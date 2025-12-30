"""
Error Handling domain BDD step definitions.

This module provides comprehensive step definitions for error handling scenarios
with automatic multi-modal testing across CLI, API, and Plugin interfaces.
Follows Axiom #14 (parameterization) and Axiom #4 (multi-modal testing).
"""

from behave import given, when, then
import os


# =============================================================================
# Validation Support - Multi-Modal Testing
# =============================================================================


@when("I validate error behavior across all usage models")
def step_when_validate_error_behavior_across_all_usage_models(context):
    """Execute current error scenario across CLI, API, and Plugin models automatically."""
    context.results = {}

    # CLI execution
    if hasattr(context, "cli_command"):
        result = context.execute_shell(context.cli_command)
        context.results["CLI"] = {
            "exit_code": result.get("exit_code", 1),
            "output": result.get("output", ""),
            "error_message": result.get("stderr", ""),
        }

    # API execution
    if hasattr(context, "api_method"):
        try:
            api_result = context.api_method()
            context.results["API"] = {
                "exit_code": 0,
                "output": str(api_result),
                "api_result": api_result,
            }
        except Exception as e:
            context.results["API"] = {
                "exit_code": 1,
                "output": str(e),
                "error_message": str(e),
                "api_result": None,
            }

    # Plugin execution
    if hasattr(context, "plugin_method"):
        try:
            plugin_result = context.plugin_method()
            context.results["Plugin"] = {
                "exit_code": 0,
                "output": str(plugin_result),
                "plugin_result": plugin_result,
            }
        except Exception as e:
            context.results["Plugin"] = {
                "exit_code": 1,
                "output": str(e),
                "error_message": str(e),
                "plugin_result": None,
            }


# =============================================================================
# File System Error Setup Steps
# =============================================================================


@given('I specify nonexistent inventory file "{file_path}"')
def step_given_specify_nonexistent_inventory_file(context, file_path):
    """Set up test with nonexistent inventory file path."""
    context.inventory_file = file_path
    context.file_exists = False
    context.cli_command = f"jbom bom --inventory {file_path}"
    context.api_method = lambda: context.api_generate_bom(inventory=file_path)
    context.plugin_method = lambda: context.plugin_generate_bom(inventory=file_path)


@given('I specify nonexistent project directory "{project_path}"')
def step_given_specify_nonexistent_project_directory(context, project_path):
    """Set up test with nonexistent project directory path."""
    context.project_dir = project_path
    context.directory_exists = False
    context.cli_command = f"jbom bom --project {project_path}"
    context.api_method = lambda: context.api_generate_bom(project=project_path)
    context.plugin_method = lambda: context.plugin_generate_bom(project=project_path)


@given("an inventory file with invalid format")
def step_given_inventory_file_with_invalid_format(context):
    """Set up inventory file with invalid column structure."""
    context.invalid_inventory = True
    context.invalid_data = context.table if hasattr(context, "table") else []
    context.cli_command = "jbom bom --inventory invalid_format.csv"
    context.api_method = lambda: context.api_generate_bom(
        inventory="invalid_format.csv"
    )
    context.plugin_method = lambda: context.plugin_generate_bom(
        inventory="invalid_format.csv"
    )


@given('the schematic file contains corrupted syntax "{syntax_error}"')
def step_given_schematic_file_contains_corrupted_syntax(context, syntax_error):
    """Set up test with corrupted schematic syntax."""
    context.corrupted_syntax = syntax_error
    context.schematic_corrupted = True
    context.cli_command = f"jbom bom --project {context.project_name}"
    context.api_method = lambda: context.api_generate_bom(project=context.project_name)
    context.plugin_method = lambda: context.plugin_generate_bom(
        project=context.project_name
    )


# =============================================================================
# Permission and Access Error Steps
# =============================================================================


@given("a KiCad project and forbidden output path")
def step_given_kicad_project_and_forbidden_output_path(context):
    """Set up test with permission-denied output path."""
    context.output_path_forbidden = True
    context.cli_command = "jbom bom --output /root/forbidden.csv"
    context.api_method = lambda: context.api_generate_bom(output="/root/forbidden.csv")
    context.plugin_method = lambda: context.plugin_generate_bom(
        output="/root/forbidden.csv"
    )


# =============================================================================
# Empty Data Condition Steps
# =============================================================================


@given("a KiCad project and empty inventory file")
def step_given_kicad_project_and_empty_inventory_file(context):
    """Set up test with empty inventory file."""
    context.empty_inventory = True
    context.cli_command = "jbom bom --inventory empty.csv"
    context.api_method = lambda: context.api_generate_bom(inventory="empty.csv")
    context.plugin_method = lambda: context.plugin_generate_bom(inventory="empty.csv")


@given("a KiCad project with empty schematic")
def step_given_kicad_project_with_empty_schematic(context):
    """Set up test with schematic containing no components."""
    context.empty_schematic = True
    context.cli_command = "jbom bom --project empty_project"
    context.api_method = lambda: context.api_generate_bom(project="empty_project")
    context.plugin_method = lambda: context.plugin_generate_bom(project="empty_project")


# =============================================================================
# Network and API Error Steps
# =============================================================================


@given("invalid API key for search")
def step_given_invalid_api_key_for_search(context):
    """Set up test with invalid API key."""
    context.invalid_api_key = True
    os.environ["MOUSER_API_KEY"] = "invalid_key_12345"
    context.cli_command = "jbom inventory --search"
    context.api_method = lambda: context.api_extract_inventory(search=True)
    context.plugin_method = lambda: context.plugin_extract_inventory(search=True)


@given("network connectivity issues during search")
def step_given_network_connectivity_issues_during_search(context):
    """Set up test with network connectivity problems."""
    context.network_issues = True
    context.cli_command = "jbom inventory --search"
    context.api_method = lambda: context.api_extract_inventory(search=True)
    context.plugin_method = lambda: context.plugin_extract_inventory(search=True)


# =============================================================================
# Hierarchical Project Error Steps
# =============================================================================


@given("hierarchical schematic with missing sub-sheet files")
def step_given_hierarchical_schematic_with_missing_subsheet_files(context):
    """Set up test with hierarchical schematic missing sub-sheets."""
    context.missing_subsheets = True
    context.hierarchical_project = True
    context.cli_command = "jbom bom --project hierarchical_missing"
    context.api_method = lambda: context.api_generate_bom(
        project="hierarchical_missing"
    )
    context.plugin_method = lambda: context.plugin_generate_bom(
        project="hierarchical_missing"
    )


# =============================================================================
# Mixed Condition Steps
# =============================================================================


@given("mixed valid and invalid conditions")
def step_given_mixed_valid_and_invalid_conditions(context):
    """Set up test with combination of valid and invalid inputs."""
    context.mixed_conditions = True
    context.cli_command = "jbom bom --project valid_project --inventory invalid.csv"
    context.api_method = lambda: context.api_generate_bom(
        project="valid_project", inventory="invalid.csv"
    )
    context.plugin_method = lambda: context.plugin_generate_bom(
        project="valid_project", inventory="invalid.csv"
    )


# =============================================================================
# Basic Operation Steps
# =============================================================================


@when("I generate a BOM")
def step_when_generate_a_bom(context):
    """Generate BOM and capture error conditions across all usage models automatically."""
    context.execute_steps("When I validate error behavior across all usage models")


# =============================================================================
# Error Message Verification Steps
# =============================================================================


@then(
    'the error message reports "{expected_message}" and exits with code {exit_code:d}'
)
def step_then_error_message_reports_and_exits_with_code(
    context, expected_message, exit_code
):
    """Verify error message and exit code across all usage models automatically."""
    context.execute_steps("When I validate error behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == exit_code
        ), f"{method} wrong exit code: expected {exit_code}, got {result['exit_code']}"
        error_text = result.get("error_message", result.get("output", ""))
        assert (
            expected_message in error_text
        ), f"{method} missing error message: '{expected_message}' not in '{error_text}'"


@then('the error message reports "{message_text}" and suggests checking the path')
def step_then_error_message_reports_and_suggests_checking_path(context, message_text):
    """Verify error message includes path checking suggestion across all usage models automatically."""
    context.execute_steps("When I validate error behavior across all usage models")
    for method, result in context.results.items():
        error_text = result.get("error_message", result.get("output", ""))
        assert (
            message_text in error_text
        ), f"{method} missing error message: '{message_text}' not in '{error_text}'"
        assert (
            "path" in error_text.lower()
        ), f"{method} missing path suggestion in error message"


@then('the error message reports "{message_text}" with syntax error details')
def step_then_error_message_reports_with_syntax_error_details(context, message_text):
    """Verify error message includes syntax error details across all usage models automatically."""
    context.execute_steps("When I validate error behavior across all usage models")
    for method, result in context.results.items():
        error_text = result.get("error_message", result.get("output", ""))
        assert (
            message_text in error_text
        ), f"{method} missing error message: '{message_text}' not in '{error_text}'"
        assert "syntax" in error_text.lower(), f"{method} missing syntax error details"


# =============================================================================
# Warning and Success with Error Steps
# =============================================================================


@then('the error handling reports "{error_type}" suggesting {suggestion_type} check')
def step_then_error_handling_reports_error_suggesting_check(
    context, error_type, suggestion_type
):
    """Verify error handling with specific suggestion across all usage models automatically."""
    context.execute_steps("When I validate error behavior across all usage models")
    for method, result in context.results.items():
        error_text = result.get("error_message", result.get("output", ""))
        assert (
            error_type in error_text
        ), f"{method} missing error type: '{error_type}' not in '{error_text}'"
        assert (
            suggestion_type in error_text
        ), f"{method} missing suggestion: '{suggestion_type}' not in '{error_text}'"


@then("the processing succeeds with empty inventory warning and unmatched components")
def step_then_processing_succeeds_with_empty_inventory_warning(context):
    """Verify successful processing with empty inventory warning across all usage models automatically."""
    context.execute_steps("When I validate error behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} should succeed with warnings"
        output = result.get("output", "")
        assert (
            "empty" in output.lower() and "inventory" in output.lower()
        ), f"{method} missing empty inventory warning"


@then("the processing succeeds with no components warning and empty BOM file")
def step_then_processing_succeeds_with_no_components_warning(context):
    """Verify successful processing with no components warning across all usage models automatically."""
    context.execute_steps("When I validate error behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} should succeed with warnings"
        output = result.get("output", "")
        assert (
            "no components" in output.lower() or "empty" in output.lower()
        ), f"{method} missing no components warning"


@then("the processing succeeds with missing sub-sheet warnings and partial BOM")
def step_then_processing_succeeds_with_missing_subsheet_warnings(context):
    """Verify successful processing with sub-sheet warnings across all usage models automatically."""
    context.execute_steps("When I validate error behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} should succeed with warnings"
        output = result.get("output", "")
        assert "missing" in output.lower() and (
            "sub-sheet" in output.lower() or "sheet" in output.lower()
        ), f"{method} missing sub-sheet warning"


@then("the processing succeeds for valid parts with specific error reporting")
def step_then_processing_succeeds_for_valid_parts_with_error_reporting(context):
    """Verify mixed success/failure processing across all usage models automatically."""
    context.execute_steps("When I validate error behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} should succeed for valid parts"
        output = result.get("output", "")
        assert (
            "error" in output.lower() or "warning" in output.lower()
        ), f"{method} missing specific error reporting"
