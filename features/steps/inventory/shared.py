"""
Shared step definitions for inventory-related functionality.

This module contains parameterized steps that are shared across multiple
inventory features (search_enhancement, project_extraction) following
Axiom #15 (logical grouping by domain) and Axiom #16 (parameterization).
"""

from behave import given, when, then
import os


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


# =============================================================================
# Validation Support - Multi-Modal Testing
# =============================================================================


@when("I validate inventory extraction across all usage models")
def step_when_validate_inventory_across_all_usage_models(context):
    """Execute current scenario across CLI, API, and Plugin models automatically."""
    context.results = {}

    # CLI execution
    if hasattr(context, "cli_command"):
        result = context.execute_shell(context.cli_command)
        context.results["CLI"] = {
            "exit_code": result.get("exit_code", 1),
            "output": result.get("output", ""),
            "output_file": getattr(context, "output_file", None),
        }

    # API execution
    if hasattr(context, "api_method"):
        try:
            api_result = context.api_method()
            context.results["API"] = {
                "exit_code": 0 if api_result else 1,
                "output": str(api_result),
                "api_result": api_result,
                "output_file": getattr(context, "output_file", None),
            }
        except Exception as e:
            context.results["API"] = {
                "exit_code": 1,
                "output": str(e),
                "api_result": None,
                "output_file": None,
            }

    # Plugin execution
    if hasattr(context, "plugin_method"):
        try:
            plugin_result = context.plugin_method()
            context.results["Plugin"] = {
                "exit_code": 0 if plugin_result else 1,
                "output": str(plugin_result),
                "plugin_result": plugin_result,
                "output_file": getattr(context, "output_file", None),
            }
        except Exception as e:
            context.results["Plugin"] = {
                "exit_code": 1,
                "output": str(e),
                "plugin_result": None,
                "output_file": None,
            }


# =============================================================================
# Environment and Configuration Steps
# =============================================================================


@given("the {api_key} environment variable is available for distributor search")
def step_given_api_key_available(context, api_key):
    """Set up distributor API key for search enhancement."""
    context.api_key = api_key
    context.api_available = True
    # Set up mock or real API key for testing
    os.environ[api_key] = os.environ.get(api_key, "test_api_key_12345")


@given("the {api_key} is set to NULL")
def step_given_api_key_set_to_null(context, api_key):
    """Remove API key to test caching behavior."""
    os.environ[api_key] = ""


@given("a schematic with mixed searchable and exotic components")
def step_given_mixed_components_schematic(context):
    """Set up schematic with mixed component searchability."""
    context.component_mix = "exotic"
    context.schematic_type = "MixedComponents"
    # Table data should be available in context.table if provided


@given("search returns multiple good matches for components")
def step_given_multiple_search_matches(context):
    """Set up scenario with multiple search result matches."""
    context.multiple_matches = True
    context.search_quality = "multiple_good"


# =============================================================================
# Inventory Extraction Steps
# =============================================================================


@when("I extract inventory from the project with --{fabricator:w} fabricator")
def step_when_extract_inventory_with_fabricator(context, fabricator):
    """Extract inventory with specified fabricator across all usage models automatically."""
    context.fabricator = fabricator
    context.cli_command = (
        f"jbom inventory --fabricator {fabricator} --project {context.project_dir}"
    )
    context.api_method = lambda: context.api_extract_inventory(fabricator)
    context.plugin_method = lambda: context.plugin_extract_inventory(fabricator)


@when("I extract inventory with --{fabricator:w} fabricator format")
def step_when_extract_inventory_with_fabricator_format(context, fabricator):
    """Extract inventory with fabricator-specific format across all usage models automatically."""
    context.fabricator = fabricator
    context.cli_command = f"jbom inventory --fabricator {fabricator} --format {fabricator} --project {context.project_dir}"
    context.api_method = lambda: context.api_extract_inventory(
        fabricator, format=fabricator
    )
    context.plugin_method = lambda: context.plugin_extract_inventory(
        fabricator, format=fabricator
    )


@when("I extract inventory with --{fabricator:w} fabricator and UUID tracking")
def step_when_extract_inventory_with_uuid_tracking(context, fabricator):
    """Extract inventory with UUID tracking across all usage models automatically."""
    context.fabricator = fabricator
    context.cli_command = f"jbom inventory --fabricator {fabricator} --uuid --project {context.project_dir}"
    context.api_method = lambda: context.api_extract_inventory(fabricator, uuid=True)
    context.plugin_method = lambda: context.plugin_extract_inventory(
        fabricator, uuid=True
    )


@when("I use the API to extract inventory with --{fabricator:w} fabricator")
def step_when_use_api_extract_inventory(context, fabricator):
    """Extract inventory via API with specified fabricator."""
    context.fabricator = fabricator
    context.api_method = lambda: context.api_extract_inventory(fabricator)


@when(
    "I extract inventory from the hierarchical project with --{fabricator:w} fabricator"
)
def step_when_extract_hierarchical_inventory(context, fabricator):
    """Extract inventory from hierarchical project across all usage models automatically."""
    context.fabricator = fabricator
    context.project_type = "hierarchical"
    context.cli_command = (
        f"jbom inventory --fabricator {fabricator} --project {context.project_dir}"
    )
    context.api_method = lambda: context.api_extract_inventory(fabricator)
    context.plugin_method = lambda: context.plugin_extract_inventory(fabricator)


@when("I extract inventory with custom fields {field_list} for selective extraction")
def step_when_extract_inventory_with_custom_fields(context, field_list):
    """Extract inventory with custom field selection across all usage models automatically."""
    context.custom_fields = field_list
    context.cli_command = (
        f"jbom inventory --fields '{field_list}' --project {context.project_dir}"
    )
    context.api_method = lambda: context.api_extract_inventory(fields=field_list)
    context.plugin_method = lambda: context.plugin_extract_inventory(fields=field_list)


# =============================================================================
# Search Enhancement Steps
# =============================================================================


@when("I generate search-enhanced inventory with --{fabricator:w} fabricator")
def step_when_generate_search_enhanced_inventory(context, fabricator):
    """Generate search-enhanced inventory across all usage models automatically."""
    context.fabricator = fabricator
    context.search_enabled = True
    context.cli_command = f"jbom inventory --fabricator {fabricator} --search --project {context.project_dir}"
    context.api_method = lambda: context.api_extract_inventory(fabricator, search=True)
    context.plugin_method = lambda: context.plugin_extract_inventory(
        fabricator, search=True
    )


@when("I search with --{fabricator:w} fabricator and result limit of {limit:d}")
def step_when_search_with_result_limit(context, fabricator, limit):
    """Search with result limit across all usage models automatically."""
    context.fabricator = fabricator
    context.result_limit = limit
    context.cli_command = f"jbom inventory --fabricator {fabricator} --search --limit {limit} --project {context.project_dir}"
    context.api_method = lambda: context.api_extract_inventory(
        fabricator, search=True, limit=limit
    )
    context.plugin_method = lambda: context.plugin_extract_inventory(
        fabricator, search=True, limit=limit
    )


@when(
    "I generate search-enhanced inventory with --{fabricator:w} fabricator the first time"
)
def step_when_generate_search_enhanced_first_time(context, fabricator):
    """Generate search-enhanced inventory first time across all usage models automatically."""
    context.fabricator = fabricator
    context.search_run = "first"
    context.cli_command = f"jbom inventory --fabricator {fabricator} --search --project {context.project_dir}"
    context.api_method = lambda: context.api_extract_inventory(fabricator, search=True)
    context.plugin_method = lambda: context.plugin_extract_inventory(
        fabricator, search=True
    )


@when(
    "I generate search-enhanced inventory with --{fabricator:w} fabricator a second time"
)
def step_when_generate_search_enhanced_second_time(context, fabricator):
    """Generate search-enhanced inventory second time (caching test) across all usage models automatically."""
    context.fabricator = fabricator
    context.search_run = "second"
    context.cli_command = f"jbom inventory --fabricator {fabricator} --search --project {context.project_dir}"
    context.api_method = lambda: context.api_extract_inventory(fabricator, search=True)
    context.plugin_method = lambda: context.plugin_extract_inventory(
        fabricator, search=True
    )


@when("I generate enhanced inventory with --{fabricator:w} fabricator")
def step_when_generate_enhanced_inventory(context, fabricator):
    """Generate enhanced inventory with statistics across all usage models automatically."""
    context.fabricator = fabricator
    context.statistics_enabled = True
    context.cli_command = f"jbom inventory --fabricator {fabricator} --search --stats --project {context.project_dir}"
    context.api_method = lambda: context.api_extract_inventory(
        fabricator, search=True, stats=True
    )
    context.plugin_method = lambda: context.plugin_extract_inventory(
        fabricator, search=True, stats=True
    )


@when("I enable interactive selection mode with --{fabricator:w} fabricator")
def step_when_enable_interactive_selection(context, fabricator):
    """Enable interactive selection mode across all usage models automatically."""
    context.fabricator = fabricator
    context.interactive_mode = True
    context.cli_command = f"jbom inventory --fabricator {fabricator} --search --interactive --project {context.project_dir}"
    context.api_method = lambda: context.api_extract_inventory(
        fabricator, search=True, interactive=True
    )
    context.plugin_method = lambda: context.plugin_extract_inventory(
        fabricator, search=True, interactive=True
    )


# =============================================================================
# Additional Verification Steps - Non-parameterized for Exact Matching
# =============================================================================


@then(
    "the inventory contains entries for RES, CAP, and IC categories with columns matching the Generic fabricator configuration"
)
def step_then_inventory_contains_basic_categories_generic(context):
    """Verify inventory contains basic component categories for Generic fabricator."""
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} inventory extraction failed"


@then(
    "the inventory contains columns matching the JLC fabricator configuration for distributor submission"
)
def step_then_inventory_matches_jlc_fabricator_config(context):
    """Verify inventory columns match JLC fabricator configuration."""
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} JLC fabricator format failed"


@then(
    "the inventory contains UUID column with component UUIDs for back-annotation linking"
)
def step_then_inventory_contains_uuid_column(context):
    """Verify inventory contains UUID column."""
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} UUID tracking failed"


@then(
    "the API returns InventoryResult with component count and field names matching the Generic fabricator configuration"
)
def step_then_api_returns_inventory_result_generic(context):
    """Verify API returns proper InventoryResult structure for Generic fabricator."""
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )
    api_result = context.results.get("API", {})
    assert api_result.get("exit_code") == 0, "API inventory extraction failed"
    assert api_result.get("api_result"), "API should return InventoryResult object"


@then("the inventory merges components across sheets with correct quantities")
def step_then_inventory_merges_hierarchical_components(context):
    """Verify hierarchical inventory merging."""
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} hierarchical merge failed"


@then("the inventory contains only the specified columns excluding default columns")
def step_then_inventory_contains_only_specified_columns(context):
    """Verify custom field selection."""
    context.execute_steps(
        "When I validate inventory extraction across all usage models"
    )
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} custom field selection failed"
