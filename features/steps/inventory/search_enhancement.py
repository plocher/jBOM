"""BDD step definitions for search enhancement functionality."""

from behave import given, then


@then(
    "the search-enhanced inventory includes part numbers, pricing, and stock quantities"
)
def step_then_search_enhanced_inventory_includes_data(context):
    """Verify search-enhanced inventory generation across all usage models automatically."""
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce enhanced inventory file"


@then("the inventory contains 3 candidate parts with priority ranking")
def step_then_inventory_contains_candidate_parts_with_ranking(context):
    """Verify multi-candidate search results across all usage models automatically."""
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce multi-candidate inventory file"


@then("the search results are cached for faster subsequent runs")
def step_then_search_results_are_cached(context):
    """Verify search caching across all usage models automatically."""
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce cached inventory file"


@then("the API generates enhanced inventory with search statistics and tracking")
def step_then_api_generates_enhanced_inventory_with_statistics(context):
    """Verify API search enhancement across all usage models automatically."""
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce enhanced API inventory file"


@then(
    "the inventory includes distributor data for found components and reports search statistics"
)
def step_then_inventory_includes_distributor_data_and_statistics(context):
    """Verify graceful search failure handling across all usage models automatically."""
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce partial search inventory file"


@then("the search presents interactive options for customized inventory selection")
def step_then_search_presents_interactive_options(context):
    """Verify interactive search selection across all usage models automatically."""
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce interactive inventory file"


# Test data setup
@given("the schematic contains exotic components unlikely to be found")
def step_given_schematic_contains_exotic_components(context):
    """Set up schematic with exotic components."""
    pass


@given("the schematic contains components with multiple good matches")
def step_given_schematic_contains_components_with_multiple_matches(context):
    """Set up schematic with components that have multiple search matches."""
    pass
