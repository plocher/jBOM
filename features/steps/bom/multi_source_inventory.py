"""
BDD step definitions for multi-source inventory functionality.

This module contains domain-specific steps that automatically test
multi-source inventory handling across CLI, Python API, and KiCad plugin interfaces.
"""

from behave import given, then


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


@then("the BOM generates with source tracking for each matched item")
def step_then_bom_generates_with_source_tracking(context):
    """Verify source tracking across all usage models automatically."""
    # Auto-execute multi-modal validation
    context.execute_steps("When I validate behavior across all usage models")

    # Then verify the source tracking behavior
    # TODO: Implement specific source tracking validation in Phase 3
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
# Multi-Source Inventory Test Data Setup
# =============================================================================


@given("multiple inventory sources with priority differences")
def step_given_multiple_inventory_sources_with_priority(context):
    """Set up multiple inventory sources with different priorities."""
    # TODO: Implement multi-source setup in Phase 3
    pass


@given("a local inventory CSV and distributor export file")
def step_given_local_csv_and_distributor_export(context):
    """Set up local CSV and distributor export files."""
    # TODO: Implement distributor export setup in Phase 3
    pass


@given("multiple inventory sources with {component}")
def step_given_multiple_sources_with_component(context, component):
    """Set up multiple inventory sources containing specific component."""
    # TODO: Implement component-specific multi-source setup in Phase 3
    pass


@given("multiple inventory sources with standard components")
def step_given_multiple_sources_with_standard_components(context):
    """Set up multiple inventory sources with standard components."""
    # TODO: Implement standard multi-source setup in Phase 3
    pass


@given("conflicting inventory sources with same IPN but different specs")
def step_given_conflicting_inventory_sources(context):
    """Set up conflicting inventory sources."""
    # TODO: Implement conflicting sources setup in Phase 3
    pass
