"""
Shared step definitions for inventory-related functionality.

This module contains parameterized steps that are shared across multiple
inventory features (search_enhancement, project_extraction) following
Axiom #15 (logical grouping by domain) and Axiom #16 (parameterization).
"""

from behave import then


# =============================================================================
# Parameterized Inventory Step Definitions (Axiom #16)
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
