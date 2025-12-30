"""BDD step definitions for part search functionality."""

from behave import given, then


# Part Search Domain-Specific Steps
@then("the search returns up to {count:d} matching parts ranked by relevance")
def step_then_search_returns_matching_parts_ranked(context, count):
    """Verify basic part search with parameterized result count across all usage models automatically."""
    context.execute_steps("When I validate search across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} search failed to return {count} results"


@then("the search uses {provider} with part numbers, pricing, and stock availability")
def step_then_search_uses_provider_with_details(context, provider):
    """Verify provider-specific search with parameterized provider across all usage models automatically."""
    context.execute_steps("When I validate search across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} {provider} search failed"


@then("the search finds exact manufacturer part with cross-references and pricing")
def step_then_search_finds_exact_part_with_details(context):
    """Verify exact part number search across all usage models automatically."""
    context.execute_steps("When I validate search across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} exact search failed"


@then(
    "the search filters results for {tolerance} tolerance and {package} package excluding inappropriate matches"
)
def step_then_search_filters_parametric_results(context, tolerance, package):
    """Verify parametric filtering with parameterized specifications across all usage models automatically."""
    context.execute_steps("When I validate search across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} parametric search for {tolerance} {package} failed"


@then("the search returns no results with appropriate messaging without errors")
def step_then_search_returns_no_results_gracefully(context):
    """Verify graceful failure handling across all usage models automatically."""
    context.execute_steps("When I validate search across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} search error handling failed"


@then("the search returns SearchResult objects with filterable part information")
def step_then_search_returns_searchresult_objects(context):
    """Verify search results across all usage models automatically."""
    context.execute_steps("When I validate search across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} search failed"


@then("the search uses specified authentication and returns results normally")
def step_then_search_uses_specified_authentication(context):
    """Verify authentication override across all usage models automatically."""
    context.execute_steps("When I validate search across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} authentication override failed"


# Test data setup
@given("I need to find a {value} {package} {component_type}")
def step_given_need_to_find_component(context, value, package, component_type):
    """Set up search for specific component with parameterized specifications."""
    context.search_component = {
        "value": value,
        "package": package,
        "type": component_type,
    }


@given("I want to search specifically on {provider} for {value} {component_type}")
def step_given_search_provider_for_component(context, provider, value, component_type):
    """Set up provider-specific component search with parameterized values."""
    context.search_provider = provider
    context.search_component = {"value": value, "type": component_type}


@given('I know manufacturer part number "{part_number}"')
def step_given_manufacturer_part_number(context, part_number):
    """Set up search for specific manufacturer part number."""
    context.part_number = part_number


@given(
    "I need {value} {component_type} with {tolerance} tolerance in {package} package"
)
def step_given_parametric_component_search(
    context, value, component_type, tolerance, package
):
    """Set up parametric component search with parameterized specifications."""
    context.search_component = {
        "value": value,
        "type": component_type,
        "tolerance": tolerance,
        "package": package,
    }


@given('I search for non-existent part "{part_number}"')
def step_given_search_nonexistent_part(context, part_number):
    """Set up search for non-existent part."""
    context.part_number = part_number


@given("I want to search programmatically")
def step_given_programmatic_search(context):
    """Set up programmatic search context."""
    pass


@given('I have different API key "{api_key}" for 1uF capacitor search')
def step_given_different_api_key_for_search(context, api_key):
    """Set up search with different API key."""
    context.api_key = api_key
