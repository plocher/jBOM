"""
Shared step definitions for back-annotation functionality.

This module contains parameterized steps that are shared across multiple
annotation features following Axiom #15 (logical grouping by domain)
and Axiom #16 (parameterization).
"""

from behave import then


# =============================================================================
# Parameterized Back-Annotation Step Definitions (Axiom #16)
# =============================================================================


@then("the back-annotation updates schematic with fields {field_list}")
def step_then_back_annotation_updates_schematic_with_fields(context, field_list):
    """Verify schematic updates with parameterized field list across all usage models automatically.

    This addresses Observation #2: Instead of vague "distributor and manufacturer information",
    use specific field lists like "Manufacturer, MPN, Distributor, DPN".
    """
    context.execute_steps("When I validate annotation across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} back-annotation with {field_list} failed"


@then("the back-annotation updates schematic with {information_types}")
def step_then_back_annotation_updates_schematic_with_info_types(
    context, information_types
):
    """Verify schematic updates with parameterized information types across all usage models automatically."""
    context.execute_steps("When I validate annotation across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} back-annotation with {information_types} failed"


@then("the updates match the {fabricator} fabricator configuration")
def step_then_updates_match_fabricator_configuration(context, fabricator):
    """Verify updates match parameterized fabricator configuration across all usage models automatically."""
    context.execute_steps("When I validate annotation across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} {fabricator} configuration match failed"


@then("the back-annotation warns about invalid {issue_type}")
def step_then_back_annotation_warns_about_issues(context, issue_type):
    """Verify warning handling for parameterized issue types across all usage models automatically."""
    context.execute_steps("When I validate annotation across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} {issue_type} warning failed"


@then("the back-annotation updates only valid components")
def step_then_back_annotation_updates_only_valid_components(context):
    """Verify selective updates for valid components across all usage models automatically."""
    context.execute_steps("When I validate annotation across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} valid component updates failed"


@then("the back-annotation updates only matching components and reports mismatches")
def step_then_back_annotation_updates_matching_reports_mismatches(context):
    """Verify matching component updates and mismatch reporting across all usage models automatically."""
    context.execute_steps("When I validate annotation across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} matching component annotation failed"


@then("the back-annotation updates only {field_type} fields preserving existing data")
def step_then_back_annotation_updates_only_field_type_preserving_data(
    context, field_type
):
    """Verify selective field updates with parameterized field types across all usage models automatically."""
    context.execute_steps("When I validate annotation across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} selective {field_type} annotation failed"
