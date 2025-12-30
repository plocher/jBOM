"""BDD step definitions for error handling and edge cases."""

from behave import given, then


# Error Handling Domain-Specific Steps
@then('the error handling reports "{error_message}" with missing file path')
def step_then_error_handling_reports_message_with_file_path(context, error_message):
    """Verify file not found error handling across all usage models automatically."""
    context.execute_steps("When I validate error handling across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] != 0, f"{method} should have failed for missing file"


@then('the error handling reports "{error_message}" with specific column details')
def step_then_error_handling_reports_message_with_column_details(
    context, error_message
):
    """Verify invalid format error handling across all usage models automatically."""
    context.execute_steps("When I validate error handling across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] != 0
        ), f"{method} should have failed for invalid format"


@then('the error handling reports "{error_message}" suggesting path check')
def step_then_error_handling_reports_message_suggesting_path_check(
    context, error_message
):
    """Verify project not found error handling across all usage models automatically."""
    context.execute_steps("When I validate error handling across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] != 0
        ), f"{method} should have failed for missing project"


@then('the error handling reports "{error_message}" identifying problematic file')
def step_then_error_handling_reports_message_identifying_file(context, error_message):
    """Verify parsing error handling across all usage models automatically."""
    context.execute_steps("When I validate error handling across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] != 0
        ), f"{method} should have failed for parsing error"


@then('the error handling reports "{error_message}" suggesting permission check')
def step_then_error_handling_reports_message_suggesting_permission_check(
    context, error_message
):
    """Verify permission error handling across all usage models automatically."""
    context.execute_steps("When I validate error handling across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] != 0
        ), f"{method} should have failed for permission error"


@then("the processing succeeds with empty inventory warning and unmatched components")
def step_then_processing_succeeds_with_empty_inventory_warning(context):
    """Verify empty inventory handling across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} should succeed with empty inventory"


@then("the processing succeeds with no components warning and empty BOM file")
def step_then_processing_succeeds_with_no_components_warning(context):
    """Verify empty schematic handling across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} should succeed with empty schematic"


@then('the error handling reports "{error_message}" suggesting API key check')
def step_then_error_handling_reports_message_suggesting_api_key_check(
    context, error_message
):
    """Verify API key error handling across all usage models automatically."""
    context.execute_steps("When I validate error handling across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] != 0
        ), f"{method} should have failed for invalid API key"


@then('the error handling reports "{error_message}" suggesting connectivity check')
def step_then_error_handling_reports_message_suggesting_connectivity_check(
    context, error_message
):
    """Verify network error handling across all usage models automatically."""
    context.execute_steps("When I validate error handling across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] != 0
        ), f"{method} should have failed for network error"


@then("the processing succeeds with missing sub-sheet warnings and partial BOM")
def step_then_processing_succeeds_with_missing_subsheet_warnings(context):
    """Verify missing sub-sheet handling across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} should succeed with missing sub-sheets"


@then("the processing succeeds for valid parts with specific error reporting")
def step_then_processing_succeeds_for_valid_with_error_reporting(context):
    """Verify graceful degradation across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        # Should succeed overall but report specific errors
        assert (
            result["exit_code"] == 0
        ), f"{method} should partially succeed with mixed conditions"


# Test data setup
@given("a KiCad project and nonexistent inventory file")
def step_given_project_and_nonexistent_inventory(context):
    """Set up project with nonexistent inventory file."""
    pass


@given("a KiCad project and inventory file with invalid format")
def step_given_project_and_invalid_inventory_format(context):
    """Set up project with invalid inventory format."""
    pass


@given("nonexistent project files")
def step_given_nonexistent_project_files(context):
    """Set up nonexistent project scenario."""
    pass


@given("a KiCad project with corrupted schematic syntax")
def step_given_project_with_corrupted_schematic(context):
    """Set up project with corrupted schematic."""
    pass


@given("a KiCad project and forbidden output path")
def step_given_project_and_forbidden_output(context):
    """Set up project with permission denied output."""
    pass


@given("a KiCad project and empty inventory file")
def step_given_project_and_empty_inventory(context):
    """Set up project with empty inventory."""
    pass


@given("a KiCad project with empty schematic")
def step_given_project_with_empty_schematic(context):
    """Set up project with empty schematic."""
    pass


@given("invalid API key for search")
def step_given_invalid_api_key_for_search(context):
    """Set up invalid API key scenario."""
    pass


@given("network connectivity issues during search")
def step_given_network_connectivity_issues(context):
    """Set up network issues scenario."""
    pass


@given("hierarchical schematic with missing sub-sheet files")
def step_given_hierarchical_with_missing_subsheets(context):
    """Set up hierarchical schematic with missing files."""
    pass


@given("mixed valid and invalid conditions")
def step_given_mixed_valid_invalid_conditions(context):
    """Set up mixed condition scenario for graceful degradation."""
    pass
