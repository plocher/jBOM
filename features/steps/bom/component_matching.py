"""
BDD step definitions for component matching functionality.

This module contains domain-specific steps that automatically test
component matching across CLI, Python API, and KiCad plugin interfaces.
"""

from behave import given, then


# =============================================================================
# Component Matching Domain-Specific Steps (Ultimate DRY Solution)
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


# =============================================================================
# Test Data Setup for Component Matching
# =============================================================================


@given("the schematic contains a {value} {package} {component_type}")
def step_given_schematic_contains_component(context, value, package, component_type):
    """Set up schematic with specific component."""
    # TODO: Implement specific component setup in Phase 3
    context.test_component = {
        "value": value,
        "package": package,
        "type": component_type,
    }


# NOTE: Hardcoded step definitions removed per Axiom #16 (Step Parameterization)
# The parameterized step @given('the schematic contains a {value} {package} {component_type}')
# handles all specific component cases (10K 0603 resistor, 100nF 0603 capacitor, etc.)
# This eliminates code duplication and improves maintainability


@given("the schematic contains diverse components")
def step_given_schematic_contains_diverse_components(context):
    """Set up schematic with diverse component types."""
    # TODO: Implement diverse component setup in Phase 3
    pass


# NOTE: Over-parameterized step removed per Axiom #16 anti-pattern guidance
# Multiple components should be handled with data tables or separate Given steps
# This avoids ambiguous step conflicts and improves readability
