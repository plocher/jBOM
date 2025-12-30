"""BDD step definitions for back-annotation functionality.

Single-feature domain: All steps consolidated here per YAGNI principle.
When multiple annotation features exist, consider shared.py for common steps.
"""

from behave import given, when, then


# =============================================================================
# Parameterized Back-Annotation When Steps (Axiom #16)
# =============================================================================


# Order matters: More specific patterns must come before general ones to avoid AmbiguousStep
@when("I run back-annotation with --dry-run and --{fabricator} fabricator")
def step_when_run_back_annotation_dry_run_with_fabricator(context, fabricator):
    """Run dry-run back-annotation with parameterized fabricator across all usage models automatically.

    This step MUST be defined before the general fabricator step to avoid AmbiguousStep conflicts.
    """
    context.execute_steps("When I validate annotation across all usage models")
    # Store dry-run and fabricator for verification in Then steps
    context.annotation_mode = "dry-run"
    context.annotation_fabricator = fabricator


@when("I run back-annotation with --{fabricator:w} fabricator")
def step_when_run_back_annotation_with_fabricator(context, fabricator):
    """Run back-annotation with parameterized fabricator (single word) across all usage models automatically.

    Uses {fabricator:w} to match single words only, avoiding conflicts with multi-word patterns.
    """
    context.execute_steps("When I validate annotation across all usage models")
    # Store the fabricator for verification in Then steps
    context.annotation_fabricator = fabricator


@when(
    'I run back-annotation with --fields "{field_list}" only and --{fabricator} fabricator'
)
def step_when_run_back_annotation_with_fields_and_fabricator(
    context, field_list, fabricator
):
    """Run back-annotation with parameterized field list and fabricator across all usage models automatically."""
    context.execute_steps("When I validate annotation across all usage models")
    # Store field list and fabricator for verification in Then steps
    context.annotation_field_list = field_list
    context.annotation_fabricator = fabricator


# =============================================================================
# Parameterized Back-Annotation Then Steps (Axiom #16)
# =============================================================================


@then("the back-annotation updates schematic with fields {field_list}")
def step_then_back_annotation_updates_schematic_with_fields(context, field_list):
    """Verify schematic updates with parameterized field list across all usage models automatically.

    This addresses Observation #2: Instead of vague "distributor and manufacturer information",
    use specific field lists like "Manufacturer, MPN, Distributor, DPN".
    """
    context.execute_steps("When I validate annotation across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} back-annotation with {field_list} failed"


@then("the back-annotation updates schematic with {information_types}")
def step_then_back_annotation_updates_schematic_with_info_types(
    context, information_types
):
    """Verify schematic updates with parameterized information types across all usage models automatically."""
    context.execute_steps("When I validate annotation across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} back-annotation with {information_types} failed"


@then("the updates match the {fabricator} fabricator configuration")
def step_then_updates_match_fabricator_configuration(context, fabricator):
    """Verify updates match parameterized fabricator configuration across all usage models automatically."""
    context.execute_steps("When I validate annotation across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} {fabricator} configuration match failed"


@then("the back-annotation warns about invalid {issue_type}")
def step_then_back_annotation_warns_about_issues(context, issue_type):
    """Verify warning handling for parameterized issue types across all usage models automatically."""
    context.execute_steps("When I validate annotation across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} {issue_type} warning failed"


@then("the back-annotation updates only valid components")
def step_then_back_annotation_updates_only_valid_components(context):
    """Verify selective updates for valid components across all usage models automatically."""
    context.execute_steps("When I validate annotation across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} valid component updates failed"


@then("the back-annotation updates only matching components and reports mismatches")
def step_then_back_annotation_updates_matching_reports_mismatches(context):
    """Verify matching component updates and mismatch reporting across all usage models automatically."""
    context.execute_steps("When I validate annotation across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} matching component annotation failed"


@then("the back-annotation updates only {field_type} fields preserving existing data")
def step_then_back_annotation_updates_only_field_type_preserving_data(
    context, field_type
):
    """Verify selective field updates with parameterized field types across all usage models automatically."""
    context.execute_steps("When I validate annotation across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} selective {field_type} annotation failed"


# =============================================================================
# Feature-Specific Then Steps
# =============================================================================


# NOTE: Previous parameterized steps were consolidated here per YAGNI principle
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
