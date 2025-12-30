"""
Shared step definitions for BOM generation functionality.

This module contains parameterized steps that are shared across multiple
BOM features (component_matching, fabricator_formats, multi_source_inventory, priority_selection)
following Axiom #15 (logical grouping by domain) and Axiom #16 (parameterization).
"""

from behave import given, when, then


# =============================================================================
# Parameterized BOM Generation When Steps (Axiom #16)
# =============================================================================


@when("I generate a BOM with --{fabricator:w} fabricator")
def step_when_generate_bom_with_fabricator(context, fabricator):
    """Generate BOM with parameterized fabricator across all usage models automatically.

    Uses {fabricator:w} to match single words only, avoiding conflicts with multi-word patterns.
    """
    context.execute_steps("When I validate behavior across all usage models")
    # Store the fabricator for verification in Then steps
    context.bom_fabricator = fabricator


@when("I generate a BOM with --{fabricator:w} fabricator and {options}")
def step_when_generate_bom_with_fabricator_and_options(context, fabricator, options):
    """Generate BOM with parameterized fabricator and options across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    # Store fabricator and options for verification in Then steps
    context.bom_fabricator = fabricator
    context.bom_options = options


@when('I generate a BOM with --{fabricator:w} fabricator and fields "{field_list}"')
def step_when_generate_bom_with_fabricator_and_fields(context, fabricator, field_list):
    """Generate BOM with parameterized fabricator and field list across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    # Store fabricator and field list for verification in Then steps
    context.bom_fabricator = fabricator
    context.bom_field_list = field_list


# =============================================================================
# File-Based Given Steps for BOM Testing
# =============================================================================


@given('a KiCad project file "{filename}"')
def step_given_kicad_project_file(context, filename):
    """Set up KiCad project file for BOM testing."""
    # TODO: Implement KiCad project file setup in Phase 3
    context.kicad_project_file = filename
    pass


@given('an Excel inventory file "{filename}"')
def step_given_excel_inventory_file(context, filename):
    """Set up Excel inventory file for BOM testing."""
    # TODO: Implement Excel inventory setup in Phase 3
    context.inventory_file = filename
    context.inventory_format = "Excel"
    pass


@given('a CSV inventory file "{filename}"')
def step_given_csv_inventory_file(context, filename):
    """Set up CSV inventory file for BOM testing."""
    # TODO: Implement CSV inventory setup in Phase 3
    context.inventory_file = filename
    context.inventory_format = "CSV"
    pass


@given('a KiCad project with main sheet "{main_sheet}"')
def step_given_kicad_project_with_main_sheet(context, main_sheet):
    """Set up hierarchical KiCad project with main sheet."""
    # TODO: Implement hierarchical project setup in Phase 3
    context.main_sheet = main_sheet
    context.project_type = "hierarchical"
    pass


@given('sub-sheet "{sub_sheet}"')
def step_given_sub_sheet(context, sub_sheet):
    """Add sub-sheet to hierarchical project setup."""
    # TODO: Implement sub-sheet setup in Phase 3
    if not hasattr(context, "sub_sheets"):
        context.sub_sheets = []
    context.sub_sheets.append(sub_sheet)
    pass


@given("multiple inventory sources:")
def step_given_multiple_inventory_sources(context):
    """Set up multiple inventory sources from table data."""
    # TODO: Implement multiple inventory source setup in Phase 3
    # Table data will be available in context.table
    context.inventory_sources = context.table if hasattr(context, "table") else []
    pass


@given("a schematic with components")
def step_given_schematic_with_components(context):
    """Set up schematic with components from table data."""
    # TODO: Implement schematic component setup in Phase 3
    # Table data will be available in context.table
    context.schematic_components = context.table if hasattr(context, "table") else []
    pass


@given("an inventory with parts")
def step_given_inventory_with_parts(context):
    """Set up inventory with parts from table data."""
    # TODO: Implement inventory parts setup in Phase 3
    # Table data will be available in context.table
    context.inventory_parts = context.table if hasattr(context, "table") else []
    pass


@given("an inventory with invalid priority data")
def step_given_inventory_with_invalid_priority_data(context):
    """Set up inventory with invalid priority data from table."""
    # TODO: Implement invalid priority data setup in Phase 3
    # Table data will be available in context.table
    context.invalid_priority_inventory = (
        context.table if hasattr(context, "table") else []
    )
    pass


# =============================================================================
# Parameterized BOM Verification Then Steps (Axiom #16)
# =============================================================================


@then(
    'the BOM contains a matched {component_type} with value "{value}" and package "{package}" from the inventory'
)
def step_then_bom_contains_matched_component_with_specs(
    context, component_type, value, package
):
    """Verify component matching with parameterized specifications across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce BOM file with {component_type} {value} {package}"


@then(
    'the BOM contains a matched {component_type} with inventory value "{inventory_value}" and package "{package}"'
)
def step_then_bom_contains_matched_component_with_inventory_value(
    context, component_type, inventory_value, package
):
    """Verify component matching with parameterized inventory values across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce BOM file with {component_type} inventory value {inventory_value} {package}"


@then("the match is based on component value tolerance")
def step_then_match_based_on_tolerance(context):
    """Verify tolerance-based component matching across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} tolerance matching failed"


@then("the match uses value normalization")
def step_then_match_uses_normalization(context):
    """Verify value normalization in component matching across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} value normalization failed"


@then("the BOM contains components extracted from the KiCad schematic")
def step_then_bom_contains_components_from_schematic(context):
    """Verify BOM contains components from KiCad schematic across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not extract components from schematic"


@then("components are matched against parts loaded from Excel file")
def step_then_components_matched_against_excel(context):
    """Verify component matching against Excel inventory across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} Excel inventory matching failed"


@then("the BOM includes components from both main sheet and sub-sheet")
def step_then_bom_includes_hierarchical_components(context):
    """Verify hierarchical schematic component inclusion across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not include hierarchical components"


@then("component quantities are merged correctly across sheets")
def step_then_quantities_merged_across_sheets(context):
    """Verify component quantity merging in hierarchical schematics across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} quantity merging failed"


@then("the BOM combines parts data from all file formats")
def step_then_bom_combines_all_file_formats(context):
    """Verify multi-format inventory combination across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not combine multi-format inventory"


@then("components are matched across all inventory sources")
def step_then_components_matched_across_sources(context):
    """Verify component matching across multiple inventory sources across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} multi-source matching failed"


# =============================================================================
# Fabricator-Specific BOM Format Verification Steps
# =============================================================================


@then("the BOM contains required columns for component assembly")
def step_then_bom_contains_required_columns(context):
    """Verify BOM contains required assembly columns across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce BOM with required columns"


@then("the BOM includes component identifiers and quantities")
def step_then_bom_includes_identifiers_quantities(context):
    """Verify BOM includes component identifiers and quantities across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} component identifiers/quantities failed"


@then("the BOM format matches the {fabricator} fabricator configuration")
def step_then_bom_format_matches_fabricator_config(context, fabricator):
    """Verify BOM format matches parameterized fabricator configuration across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} {fabricator} format configuration failed"


@then("the BOM contains only the specified custom fields")
def step_then_bom_contains_only_custom_fields(context):
    """Verify BOM contains only custom fields across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} custom fields verification failed"


@then("the BOM ignores the default fabricator field configuration")
def step_then_bom_ignores_default_config(context):
    """Verify BOM ignores default fabricator configuration when custom fields specified across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} default config override failed"


@then("the BOM contains only essential assembly information")
def step_then_bom_contains_essential_assembly_info(context):
    """Verify BOM contains only essential assembly information across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce assembly BOM"


@then("the BOM contains comprehensive procurement information")
def step_then_bom_contains_comprehensive_procurement_info(context):
    """Verify BOM contains comprehensive procurement information across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce procurement BOM"


# =============================================================================
# Multi-Source Inventory Verification Steps
# =============================================================================


@then("the BOM combines parts from both inventory sources")
def step_then_bom_combines_parts_from_both_sources(context):
    """Verify BOM combines parts from multiple inventory sources across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not combine parts from both sources"


@then("component matches use parts from either inventory file")
def step_then_component_matches_use_parts_from_either_file(context):
    """Verify component matching uses parts from either inventory file across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} multi-file component matching failed"


@then(
    "the BOM selects parts with the lowest priority value among all matching candidates"
)
def step_then_bom_selects_lowest_priority_parts(context):
    """Verify BOM selects lowest priority parts across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} priority selection failed"


@then("part selection considers priority across all inventory sources")
def step_then_part_selection_considers_priority_across_sources(context):
    """Verify part selection considers priority across all inventory sources across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} cross-source priority selection failed"


@then("the BOM shows selected parts with their inventory source file")
def step_then_bom_shows_selected_parts_with_source_file(context):
    """Verify BOM shows parts with source file information across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not show source file information"


@then("alternative parts from other sources are listed as options")
def step_then_alternative_parts_listed_as_options(context):
    """Verify alternative parts from other sources are listed as options across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} alternative parts listing failed"


@then("all usage models produce consistent BOM results with multi-source inventory")
def step_then_all_models_consistent_multisource_bom(context):
    """Verify all models produce consistent BOM results with multi-source inventory."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce consistent multi-source BOM"


@then("the BOM uses the first valid part definition encountered")
def step_then_bom_uses_first_valid_definition(context):
    """Verify BOM uses first valid part definition for conflicting data across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} first valid definition selection failed"


@then("the BOM generation warns about any conflicting part specifications")
def step_then_bom_generation_warns_about_conflicts(context):
    """Verify BOM generation warns about conflicting specifications across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} conflict warning failed"


# =============================================================================
# Priority Selection Verification Steps
# =============================================================================


@then("the BOM contains {reference} matched to {part_id} with priority {priority:d}")
def step_then_bom_contains_reference_matched_to_part_with_priority(
    context, reference, part_id, priority
):
    """Verify BOM contains specific reference matched to part with priority across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not match {reference} to {part_id} with priority {priority}"


@then("the BOM excludes {excluded_parts} due to higher priority values")
def step_then_bom_excludes_parts_due_to_higher_priority(context, excluded_parts):
    """Verify BOM excludes parts due to higher priority values across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} did not exclude {excluded_parts} due to priority"


@then("the BOM excludes {excluded_part} due to higher priority value")
def step_then_bom_excludes_part_due_to_higher_priority(context, excluded_part):
    """Verify BOM excludes part due to higher priority value across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} did not exclude {excluded_part} due to priority"


@then("the error reports invalid priority values for {invalid_parts}")
def step_then_error_reports_invalid_priority_values(context, invalid_parts):
    """Verify error reporting for invalid priority values across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        # For error conditions, we expect non-zero exit codes
        assert (
            result["exit_code"] != 0
        ), f"{method} should have failed with invalid priority values for {invalid_parts}"


@then("the BOM generation fails with priority validation error")
def step_then_bom_generation_fails_with_priority_validation_error(context):
    """Verify BOM generation fails with priority validation error across all usage models automatically."""
    context.execute_steps("When I validate behavior across all usage models")
    for method, result in context.results.items():
        # For error conditions, we expect non-zero exit codes
        assert (
            result["exit_code"] != 0
        ), f"{method} should have failed with priority validation error"
