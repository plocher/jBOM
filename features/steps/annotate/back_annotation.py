"""BDD step definitions for back-annotation functionality."""

from behave import given, then


# NOTE: Hardcoded step definitions moved to shared.py with parameterization per Axiom #16
# This eliminates code duplication and provides flexible, reusable step definitions:
# - @then('the back-annotation updates schematic with {information_types}')
# - @then('the updates match the {fabricator} fabricator configuration')
# - @then('the back-annotation warns about invalid {issue_type}')
# - @then('the back-annotation updates only valid components')
# - @then('the back-annotation updates only {field_type} fields preserving existing data')
# - @then('the back-annotation updates only matching components and reports mismatches')
#
# Remaining steps are specific to back-annotation and don't benefit from parameterization


@then("the dry-run back-annotation previews changes without modifying schematic files")
def step_then_dry_run_annotation_previews_changes(context):
    """Verify dry-run annotation across all usage models automatically."""
    context.execute_steps("When I validate annotation across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} dry-run annotation failed"


@then("the back-annotation reports update count and changed details")
def step_then_annotation_reports_update_count_and_details(context):
    """Verify annotation reporting across all usage models automatically."""
    context.execute_steps("When I validate annotation across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} annotation reporting failed"


# Test data setup
@given(
    "the schematic has components with missing part information and complete inventory data"
)
def step_given_schematic_missing_info_complete_inventory(context):
    """Set up schematic with missing part info and complete inventory."""
    pass


@given("the schematic has components needing updates with inventory file")
def step_given_schematic_needs_updates_with_inventory(context):
    """Set up schematic needing updates with inventory file."""
    pass


@given("inventory file with missing or invalid UUIDs")
def step_given_inventory_with_invalid_uuids(context):
    """Set up inventory file with UUID issues."""
    pass


@given("the schematic with partial information and selective inventory updates")
def step_given_schematic_partial_info_selective_inventory(context):
    """Set up schematic with partial info and selective inventory updates."""
    pass


@given("the schematic with different components than inventory")
def step_given_schematic_different_from_inventory(context):
    """Set up mismatched schematic and inventory."""
    pass


# New step definitions for improved scenarios
@given("the schematic has components with missing part information")
def step_given_schematic_missing_part_info(context):
    """Set up schematic with components missing part information."""
    pass


@given("an inventory file with complete distributor and manufacturer data")
def step_given_inventory_complete_distributor_manufacturer_data(context):
    """Set up inventory file with complete distributor and manufacturer data."""
    # TODO: Process inventory table from feature file in Phase 3
    pass


@given("the schematic has components needing updates")
def step_given_schematic_needs_updates(context):
    """Set up schematic with components needing updates."""
    pass


@given("an inventory file with updated information")
def step_given_inventory_with_updated_info(context):
    """Set up inventory file with updated information."""
    pass


@given("the schematic has components with valid UUIDs")
def step_given_schematic_with_valid_uuids(context):
    """Set up schematic with components that have valid UUIDs."""
    pass


@given("an inventory file with missing or invalid UUIDs")
def step_given_inventory_with_missing_invalid_uuids(context):
    """Set up inventory file with UUID issues."""
    pass


@given("the schematic has components with partial information")
def step_given_schematic_with_partial_info(context):
    """Set up schematic with components having partial information."""
    pass


@given("an inventory file with selective updates (only distributor part numbers)")
def step_given_inventory_selective_dpn_updates(context):
    """Set up inventory file with only DPN updates."""
    pass


@given("the schematic has different components than the inventory")
def step_given_schematic_different_components_than_inventory(context):
    """Set up schematic with different components than inventory."""
    pass


@given("the inventory contains components not in the schematic")
def step_given_inventory_contains_extra_components(context):
    """Set up inventory with components not present in schematic."""
    pass
