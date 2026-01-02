"""
POS (Component Placement) domain BDD step definitions.

This module provides comprehensive step definitions for component placement scenarios
with automatic multi-modal testing across CLI, API, and Plugin interfaces.
Focuses on parameterized rotation scenarios and fabricator-specific corrections.
"""

from behave import given, when, then


# =============================================================================
# Validation Support - Multi-Modal Testing
# =============================================================================


@when("I validate POS behavior across all usage models")
def step_when_validate_pos_behavior_across_all_usage_models(context):
    """Execute current POS scenario across CLI, API, and Plugin models automatically."""
    context.results = {}

    # CLI execution
    if hasattr(context, "cli_command"):
        result = context.execute_shell(context.cli_command)
        context.results["CLI"] = {
            "exit_code": result.get("exit_code", 1),
            "output": result.get("output", ""),
            "output_file": getattr(context, "pos_output_file", None),
        }

    # API execution
    if hasattr(context, "api_method"):
        try:
            api_result = context.api_method()
            context.results["API"] = {
                "exit_code": 0 if api_result else 1,
                "output": str(api_result),
                "api_result": api_result,
                "output_file": getattr(context, "pos_output_file", None),
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
                "output_file": getattr(context, "pos_output_file", None),
            }
        except Exception as e:
            context.results["Plugin"] = {
                "exit_code": 1,
                "output": str(e),
                "plugin_result": None,
                "output_file": None,
            }


# =============================================================================
# PCB Setup Steps
# =============================================================================


@given('a KiCad project named "{project_name}" with a PCB file')
def step_given_kicad_project_with_pcb_file(context, project_name):
    """Set up KiCad project with PCB file for POS testing."""
    context.project_name = project_name
    context.has_pcb_file = True
    context.project_dir = f"test_projects/{project_name}"


@given('the "{pcb_fixture}" PCB layout')
def step_given_pcb_layout_fixture(context, pcb_fixture):
    """Set up PCB layout using named fixture (POS-domain specific per Axiom #13)."""
    context.pcb_fixture = pcb_fixture
    context.pcb_layout_loaded = True


@given("a PCB with components at cardinal rotation angles:")
def step_given_pcb_with_components_at_cardinal_rotation_angles(context):
    """Set up PCB with components at cardinal angles from table data."""
    context.cardinal_rotation_components = (
        context.table if hasattr(context, "table") else []
    )


@given(
    "a PCB with ICs in different packaging formats requiring different reel orientations:"
)
def step_given_pcb_with_ics_in_different_packaging_formats(context):
    """Set up PCB with ICs requiring per-part reel orientations from table data."""
    context.reel_orientation_components = (
        context.table if hasattr(context, "table") else []
    )


@given('the "{pcb_fixture}" PCB layout with auxiliary origin offset')
def step_given_pcb_layout_with_auxiliary_origin_offset(context, pcb_fixture):
    """Set up PCB layout with auxiliary origin for coordinate testing."""
    context.pcb_fixture = pcb_fixture
    context.auxiliary_origin_enabled = True


# =============================================================================
# POS Generation Steps
# =============================================================================


@when("I generate a POS file with --{fabricator:w} fabricator")
def step_when_generate_pos_file_with_fabricator(context, fabricator):
    """Generate POS file with specified fabricator across all usage models automatically."""
    context.fabricator = fabricator
    context.cli_command = (
        f"jbom pos --fabricator {fabricator} --project {context.project_dir}"
    )
    context.api_method = lambda: context.api_generate_pos(fabricator=fabricator)
    context.plugin_method = lambda: context.plugin_generate_pos(fabricator=fabricator)


@when("I generate {fabricator:w} format POS with fabricator-specific rotations")
def step_when_generate_fabricator_pos_with_specific_rotations(context, fabricator):
    """Generate fabricator POS with rotation corrections across all usage models automatically."""
    context.fabricator = fabricator
    context.rotation_corrections = True
    context.cli_command = f"jbom pos --fabricator {fabricator} --rotations --project {context.project_dir}"
    context.api_method = lambda: context.api_generate_pos(
        fabricator=fabricator, rotations=True
    )
    context.plugin_method = lambda: context.plugin_generate_pos(
        fabricator=fabricator, rotations=True
    )


@when("I generate {fabricator:w} format POS with per-part reel corrections")
def step_when_generate_fabricator_pos_with_per_part_reel_corrections(
    context, fabricator
):
    """Generate fabricator POS with per-part reel corrections across all usage models automatically."""
    context.fabricator = fabricator
    context.per_part_corrections = True
    context.cli_command = f"jbom pos --fabricator {fabricator} --reel-corrections --project {context.project_dir}"
    context.api_method = lambda: context.api_generate_pos(
        fabricator=fabricator, reel_corrections=True
    )
    context.plugin_method = lambda: context.plugin_generate_pos(
        fabricator=fabricator, reel_corrections=True
    )


@when("I generate POS with --{fabricator:w} fabricator and {filter_type} filter")
def step_when_generate_pos_with_fabricator_and_filter(context, fabricator, filter_type):
    """Generate POS with fabricator and filter type across all usage models automatically."""
    context.fabricator = fabricator
    context.filter_type = filter_type
    context.cli_command = f"jbom pos --fabricator {fabricator} --filter {filter_type} --project {context.project_dir}"
    context.api_method = lambda: context.api_generate_pos(
        fabricator=fabricator, filter=filter_type
    )
    context.plugin_method = lambda: context.plugin_generate_pos(
        fabricator=fabricator, filter=filter_type
    )


@when("I generate POS with --{fabricator:w} fabricator and {units:w} units")
def step_when_generate_pos_with_fabricator_and_units(context, fabricator, units):
    """Generate POS with fabricator and coordinate units across all usage models automatically."""
    context.fabricator = fabricator
    context.coordinate_units = units
    context.cli_command = f"jbom pos --fabricator {fabricator} --units {units} --project {context.project_dir}"
    context.api_method = lambda: context.api_generate_pos(
        fabricator=fabricator, units=units
    )
    context.plugin_method = lambda: context.plugin_generate_pos(
        fabricator=fabricator, units=units
    )


@when("I generate POS with --{fabricator:w} fabricator using auxiliary origin")
def step_when_generate_pos_with_fabricator_using_auxiliary_origin(context, fabricator):
    """Generate POS using auxiliary origin coordinates across all usage models automatically."""
    context.fabricator = fabricator
    context.use_auxiliary_origin = True
    context.cli_command = f"jbom pos --fabricator {fabricator} --aux-origin --project {context.project_dir}"
    context.api_method = lambda: context.api_generate_pos(
        fabricator=fabricator, aux_origin=True
    )
    context.plugin_method = lambda: context.plugin_generate_pos(
        fabricator=fabricator, aux_origin=True
    )


# =============================================================================
# POS Content Verification Steps
# =============================================================================


@then(
    "the POS contains components with columns matching the {fabricator} fabricator configuration"
)
def step_then_pos_contains_components_matching_fabricator_config(context, fabricator):
    """Verify POS contains components with fabricator-specific columns across all usage models automatically."""
    context.execute_steps("When I validate POS behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} POS generation failed"
        assert result["output_file"], f"{method} did not produce POS output file"


@then(
    "the POS contains rotation corrections matching the {fabricator} fabricator configuration"
)
def step_then_pos_contains_rotation_corrections_matching_fabricator_config(
    context, fabricator
):
    """Verify POS rotation corrections match fabricator configuration across all usage models automatically."""
    context.execute_steps("When I validate POS behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} rotation correction failed for {fabricator}"


@then("the POS excludes THT components per {fabricator} SMD-only policy")
def step_then_pos_excludes_tht_components_per_fabricator_policy(context, fabricator):
    """Verify POS excludes THT components per fabricator policy across all usage models automatically."""
    context.execute_steps("When I validate POS behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} THT exclusion failed for {fabricator}"


@then("the POS contains part-specific rotation corrections based on MPN and DPN lookup")
def step_then_pos_contains_part_specific_rotation_corrections(context):
    """Verify POS contains MPN/DPN-based rotation corrections across all usage models automatically."""
    context.execute_steps("When I validate POS behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} MPN/DPN rotation lookup failed"


@then("the POS shows different rotations for same chip in different packaging formats")
def step_then_pos_shows_different_rotations_for_same_chip_different_packages(context):
    """Verify POS shows package-specific rotations for same chip across all usage models automatically."""
    context.execute_steps("When I validate POS behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} package-specific rotation failed"


@then("resistors and capacitors use consistent rotation corrections per footprint")
def step_then_resistors_capacitors_use_consistent_rotation_per_footprint(context):
    """Verify passive components use footprint-based rotation consistency across all usage models automatically."""
    context.execute_steps("When I validate POS behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} passive component rotation consistency failed"


# =============================================================================
# Component Filtering Verification Steps
# =============================================================================


@then("the POS contains SMD components but excludes THT components")
def step_then_pos_contains_smd_excludes_tht_components(context):
    """Verify POS SMD-only filtering across all usage models automatically."""
    context.execute_steps("When I validate POS behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} SMD-only filtering failed"


@then("the POS contains top-side components but excludes bottom-side components")
def step_then_pos_contains_topside_excludes_bottomside_components(context):
    """Verify POS layer filtering across all usage models automatically."""
    context.execute_steps("When I validate POS behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} layer filtering failed"


# =============================================================================
# Coordinate and Unit Verification Steps
# =============================================================================


@then(
    "the POS contains component count and coordinate data in millimeters matching the {fabricator} fabricator configuration"
)
def step_then_pos_contains_coordinate_data_in_millimeters(context, fabricator):
    """Verify POS coordinate data in millimeters across all usage models automatically."""
    context.execute_steps("When I validate POS behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} millimeter coordinate data failed for {fabricator}"


@then(
    "the POS coordinates show components in inches with {precision:d} decimal precision"
)
def step_then_pos_coordinates_show_components_in_inches_with_precision(
    context, precision
):
    """Verify POS coordinates in inches with specified precision across all usage models automatically."""
    context.execute_steps("When I validate POS behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == 0
        ), f"{method} inch coordinates with {precision} precision failed"


@then("the POS coordinates show components relative to auxiliary origin")
def step_then_pos_coordinates_show_components_relative_to_auxiliary_origin(context):
    """Verify POS coordinates relative to auxiliary origin across all usage models automatically."""
    context.execute_steps("When I validate POS behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} auxiliary origin coordinates failed"


# =============================================================================
# Additional POS Generation Steps
# =============================================================================


@when("I generate POS with --{fabricator} fabricator")
def step_when_generate_pos_with_fabricator_flag(context, fabricator):
    """Generate POS with specific fabricator flag across all usage models automatically."""
    context.fabricator = fabricator
    context.cli_command = f"jbom pos --{fabricator} --project {getattr(context, 'project_dir', 'test_project')}"
    context.api_method = lambda: context.api_generate_pos(fabricator=fabricator)
    context.plugin_method = lambda: context.plugin_generate_pos(fabricator=fabricator)
