"""
BDD step definitions for fabricator format generation.

This module contains domain-specific steps that automatically test
fabricator format generation across CLI, Python API, and KiCad plugin interfaces.
"""

from behave import given, then


# =============================================================================
# Test Data Setup for Fabricator Formats
# =============================================================================


@given('I want custom BOM fields "{field_list}"')
def step_given_custom_bom_fields(context, field_list):
    """Set the custom fields for BOM generation."""
    context.custom_fields = field_list


@given("I want to generate a {format_name} format BOM")
def step_given_format_request(context, format_name):
    """Set the requested BOM format."""
    context.requested_format = format_name


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


@then("the BOM generates with the specified custom fields")
def step_then_bom_generates_with_specified_custom_fields(context):
    """Verify BOM generation with custom fields specified in scenario."""
    # Auto-execute multi-modal validation
    context.execute_steps("When I validate behavior across all usage models")

    # Then verify the custom fields behavior using the fields from context
    # TODO: Implement specific custom fields validation in Phase 3
    # Fields should be available in context.custom_fields
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce BOM file"


@then('the BOM generates in the requested format with columns "{column_list}"')
def step_then_bom_generates_in_requested_format_with_columns(context, column_list):
    """Verify BOM generation in the format and columns specified in scenario."""
    # Auto-execute multi-modal validation
    context.execute_steps("When I validate behavior across all usage models")

    # Then verify the format and columns behavior using context.requested_format
    # TODO: Implement specific format and column validation in Phase 3
    # Format should be available in context.requested_format
    # Columns should be validated against column_list
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce BOM file"
