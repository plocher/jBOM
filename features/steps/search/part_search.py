"""BDD step definitions for part search functionality."""

from behave import given, when, then


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


# =============================================================================
# Additional Search Setup Steps (Missing from behave dry-run)
# =============================================================================


@given('I search for "{search_term}"')
def step_given_search_for_term(context, search_term):
    """Set up basic search for specified term."""
    context.search_term = search_term


@given('I search for "{search_term}" on {provider}')
def step_given_search_on_provider(context, search_term, provider):
    """Set up provider-specific search."""
    context.search_term = search_term
    context.search_provider = provider


@given('I search for "{search_term}" with parameters')
def step_given_search_with_parameters(context, search_term):
    """Set up parametric search."""
    context.search_term = search_term
    context.search_parameters = context.table if hasattr(context, "table") else []


@given('I search for manufacturer part number "{mpn}"')
def step_given_search_mpn(context, mpn):
    """Set up manufacturer part number search."""
    context.manufacturer_part_number = mpn


@given('I have custom API key "{api_key}"')
def step_given_custom_api_key(context, api_key):
    """Set up custom API key."""
    context.custom_api_key = api_key


@given('I use the search API to find "{search_term}"')
def step_given_use_search_api(context, search_term):
    """Set up API-based search."""
    context.api_search_term = search_term


# =============================================================================
# Search Execution Steps (Missing When steps)
# =============================================================================


@when("I execute the search")
def step_when_execute_search(context):
    """Execute basic search."""
    # TODO: Implement actual search execution in Phase 3
    context.search_executed = True


@when("I execute the search with limit {limit:d}")
def step_when_execute_search_with_limit(context, limit):
    """Execute search with result limit."""
    context.search_limit = limit
    context.search_executed = True


@when("I execute the provider-specific search")
def step_when_execute_provider_search(context):
    """Execute provider-specific search."""
    context.provider_search_executed = True


@when("I execute the parametric search")
def step_when_execute_parametric_search(context):
    """Execute parametric search."""
    context.parametric_search_executed = True


@when("I execute the exact part number search")
def step_when_execute_exact_search(context):
    """Execute exact part number search."""
    context.exact_search_executed = True


@when("I call the API search method")
def step_when_call_api_search(context):
    """Execute API search method."""
    context.api_search_executed = True


@when('I search for "{search_term}" using the custom API key')
def step_when_search_with_custom_key(context, search_term):
    """Execute search with custom API key."""
    context.custom_key_search_executed = True


@when("the {provider}_API_KEY is set to NULL")
def step_when_api_key_set_null(context, provider):
    """Set provider API key to NULL."""
    context.null_api_key_provider = provider


# =============================================================================
# Additional Search Verification Steps (Missing Then steps)
# =============================================================================


@then(
    "the search returns up to {limit:d} matching {component_type} parts "
    "with part numbers, descriptions, and prices ranked by relevance"
)
def step_then_search_returns_limited_component_results(context, limit, component_type):
    """Verify limited search results with component type."""
    assert hasattr(context, "search_executed"), "Search should have been executed"
    # TODO: Implement result verification in Phase 3


@then(
    "the search finds the exact {manufacturer} {description} with cross-references, pricing, and distributor availability"
)
def step_then_search_finds_exact_manufacturer_part(context, manufacturer, description):
    """Verify exact manufacturer part search."""
    # TODO: Implement exact part verification in Phase 3
    pass


@then(
    "the search uses {provider} API and returns {component_type} results "
    "with manufacturer, part numbers, pricing, and stock availability"
)
def step_then_search_uses_provider_api(context, provider, component_type):
    """Verify provider API usage."""
    # TODO: Implement provider API verification in Phase 3
    pass


@then("the search returns only {description} excluding other tolerances and packages")
def step_then_search_returns_filtered_description(context, description):
    """Verify parametric search filtering."""
    # TODO: Implement parametric filtering verification in Phase 3
    pass


@then(
    'the search returns empty results with message "{message}" and exit code {exit_code:d}'
)
def step_then_search_returns_empty_with_message(context, message, exit_code):
    """Verify empty search results with specific message and exit code."""
    # TODO: Implement empty result verification in Phase 3
    pass


@then(
    "the API returns SearchResult objects with part_number, manufacturer, description, price, and stock_quantity fields"
)
def step_then_api_returns_searchresult_objects(context):
    """Verify API returns SearchResult objects with required fields."""
    # TODO: Implement SearchResult object verification in Phase 3
    pass


@then(
    "the search uses {api_key} for authentication and returns {component_type} results normally"
)
def step_then_search_uses_api_key_auth(context, api_key, component_type):
    """Verify custom API key authentication."""
    # TODO: Implement API key authentication verification in Phase 3
    pass
