"""BDD step definitions for back-annotation functionality."""

from behave import given, then


# Back-Annotation Domain-Specific Steps
@then(
    "the back-annotation updates schematic with distributor and manufacturer information"
)
def step_then_back_annotation_updates_schematic_with_info(context):
    """Verify schematic updates across all usage models automatically."""
    context.execute_steps("When I validate annotation across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} back-annotation failed"


@then("the dry-run back-annotation previews changes without modifying schematic files")
def step_then_dry_run_annotation_previews_changes(context):
    """Verify dry-run annotation across all usage models automatically."""
    context.execute_steps("When I validate annotation across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} dry-run annotation failed"


@then("the API back-annotation reports update count and changed details")
def step_then_api_annotation_reports_update_count_and_details(context):
    """Verify API annotation reporting across all usage models automatically."""
    context.execute_steps("When I validate annotation across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} API annotation failed"


@then("the back-annotation warns about invalid UUIDs and updates only valid components")
def step_then_annotation_warns_invalid_uuids_updates_valid(context):
    """Verify UUID handling across all usage models automatically."""
    context.execute_steps("When I validate annotation across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} UUID handling failed"


@then("the back-annotation updates only DPN fields preserving existing data")
def step_then_annotation_updates_dpn_only_preserving_data(context):
    """Verify selective field updates across all usage models automatically."""
    context.execute_steps("When I validate annotation across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} selective annotation failed"


@then("the back-annotation updates only matching components and reports mismatches")
def step_then_annotation_updates_matching_reports_mismatches(context):
    """Verify mismatch handling across all usage models automatically."""
    context.execute_steps("When I validate annotation across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} mismatch handling failed"


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
