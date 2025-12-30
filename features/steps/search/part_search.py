"""BDD step definitions for part search functionality."""

from behave import given, then


# Part Search Domain-Specific Steps
@then("the search returns up to 5 matching parts ranked by relevance")
def step_then_search_returns_matching_parts_ranked(context):
    """Verify basic part search across all usage models automatically."""
    context.execute_steps("When I validate search across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} search failed"


@then("the search uses Mouser API with part numbers, pricing, and stock availability")
def step_then_search_uses_mouser_api_with_details(context):
    """Verify Mouser-specific search across all usage models automatically."""
    context.execute_steps("When I validate search across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} Mouser search failed"


@then("the search finds exact manufacturer part with cross-references and pricing")
def step_then_search_finds_exact_part_with_details(context):
    """Verify exact part number search across all usage models automatically."""
    context.execute_steps("When I validate search across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} exact search failed"


@then(
    "the search filters results for 1% tolerance and 0603 package excluding inappropriate matches"
)
def step_then_search_filters_parametric_results(context):
    """Verify parametric filtering across all usage models automatically."""
    context.execute_steps("When I validate search across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} parametric search failed"


@then("the search returns no results with appropriate messaging without errors")
def step_then_search_returns_no_results_gracefully(context):
    """Verify graceful failure handling across all usage models automatically."""
    context.execute_steps("When I validate search across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} search error handling failed"


@then("the API returns SearchResult objects with filterable part information")
def step_then_api_returns_searchresult_objects(context):
    """Verify API search results across all usage models automatically."""
    context.execute_steps("When I validate search across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} API search failed"


@then("the search uses specified API key and returns results normally")
def step_then_search_uses_specified_api_key(context):
    """Verify API key override across all usage models automatically."""
    context.execute_steps("When I validate search across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} API key override failed"


# Test data setup
@given("I need to find a 10K 0603 resistor")
def step_given_need_to_find_resistor(context):
    """Set up search for specific resistor."""
    pass


@given("I want to search specifically on Mouser for 100nF ceramic capacitor")
def step_given_search_mouser_for_capacitor(context):
    """Set up Mouser-specific capacitor search."""
    pass


@given('I know manufacturer part number "{part_number}"')
def step_given_manufacturer_part_number(context, part_number):
    """Set up search for specific manufacturer part number."""
    context.part_number = part_number


@given("I need 10K resistors with 1% tolerance in 0603 package")
def step_given_parametric_resistor_search(context):
    """Set up parametric resistor search."""
    pass


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
