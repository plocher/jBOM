"""
BDD step definitions for fabricator format generation.

This module contains domain-specific steps that automatically test
fabricator format generation across CLI, Python API, and KiCad plugin interfaces.
"""

from behave import then


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
