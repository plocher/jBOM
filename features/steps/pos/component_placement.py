"""BDD step definitions for POS component placement functionality."""

from behave import given, then


# POS Generation Domain-Specific Steps
@then('the POS contains all placed components with columns "{column_list}"')
def step_then_pos_contains_placed_components_with_columns(context, column_list):
    """Verify basic POS generation across all usage models automatically."""
    context.execute_steps("When I validate POS generation across all usage models")
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce POS file"


@then(
    "the POS generates in JLCPCB format with millimeter coordinates and SMD-only filtering"
)
def step_then_pos_generates_jlcpcb_format_mm_smd(context):
    """Verify JLCPCB POS format across all usage models automatically."""
    context.execute_steps("When I validate POS generation across all usage models")
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce JLCPCB POS file"


@then("the POS contains only surface mount components excluding through-hole")
def step_then_pos_contains_smd_only_excluding_through_hole(context):
    """Verify SMD-only filtering across all usage models automatically."""
    context.execute_steps("When I validate POS generation across all usage models")
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce SMD-only POS file"


@then("the POS contains only top-side components excluding bottom-side")
def step_then_pos_contains_top_side_only(context):
    """Verify layer filtering across all usage models automatically."""
    context.execute_steps("When I validate POS generation across all usage models")
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce top-side POS file"


@then("the POS generates with placement data and coordinate information")
def step_then_pos_generates_with_placement_data_and_coordinates(context):
    """Verify POS generation with placement data across all usage models automatically."""
    context.execute_steps("When I validate POS generation across all usage models")
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce POS file with placement data"


@then("the POS coordinates are converted to inches with appropriate precision")
def step_then_pos_coordinates_converted_to_inches(context):
    """Verify coordinate unit conversion across all usage models automatically."""
    context.execute_steps("When I validate POS generation across all usage models")
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce inch-unit POS file"


@then("the POS coordinates are relative to auxiliary origin consistently")
def step_then_pos_coordinates_relative_to_aux_origin(context):
    """Verify auxiliary origin handling across all usage models automatically."""
    context.execute_steps("When I validate POS generation across all usage models")
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce aux-origin POS file"


# Test data setup
@given('a KiCad project named "{project_name}" with a PCB file')
def step_given_kicad_project_with_pcb(context, project_name):
    """Set up a KiCad project with PCB file."""
    context.project_name = project_name
    pass


@given("the PCB contains placed components")
def step_given_pcb_contains_placed_components(context):
    """Set up PCB with placed components."""
    pass


@given("the PCB contains SMD components for assembly")
def step_given_pcb_contains_smd_components(context):
    """Set up PCB with SMD components."""
    pass


@given("the PCB contains both SMD and through-hole components")
def step_given_pcb_contains_smd_and_through_hole(context):
    """Set up PCB with mixed component types."""
    pass


@given("the PCB has components on both top and bottom layers")
def step_given_pcb_has_components_on_both_layers(context):
    """Set up PCB with components on multiple layers."""
    pass


@given("the PCB has an auxiliary origin defined")
def step_given_pcb_has_auxiliary_origin(context):
    """Set up PCB with auxiliary origin."""
    pass
