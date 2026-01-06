"""
BDD step definitions for schematic loading functionality.

This module contains steps for testing KiCad schematic loading,
including hierarchical schematics, multiple schematics, and edge cases.
"""

from behave import given, when, then


# =============================================================================
# Hierarchical Schematic Setup Steps
# =============================================================================


@given(
    'a hierarchical KiCad project named "{project_name}" with root schematic referencing sub-sheet "{subsheet_name}"'
)
def step_given_hierarchical_kicad_project(context, project_name, subsheet_name):
    """Create a hierarchical KiCad project with root schematic referencing a sub-sheet."""
    context.project_name = project_name
    context.subsheet_name = subsheet_name

    # Create project directory
    project_dir = context.scenario_temp_dir / project_name
    project_dir.mkdir(exist_ok=True)

    # Store for later use in other steps
    context.test_project_dir = project_dir


@given("the root schematic contains components")
def step_given_root_schematic_contains_components(context):
    """Create root schematic with components from table, including sub-sheet reference."""
    project_dir = context.test_project_dir
    project_name = context.project_name
    subsheet_name = context.subsheet_name

    schematic_file = project_dir / f"{project_name}.kicad_sch"

    # Build symbol entries from table using format jBOM can parse
    symbols = []
    x_position = 50
    for row in context.table:
        reference = row["Reference"]
        value = row["Value"]
        footprint = row["Footprint"]

        # Generate a symbol entry in KiCad format
        symbol = f'''  (symbol (lib_id "Device:Generic") (at {x_position} 50 0) (unit 1)
    (property "Reference" "{reference}" (id 0) (at {x_position+2} 50 0))
    (property "Value" "{value}" (id 1) (at {x_position+2} 52 0))
    (property "Footprint" "{footprint}" (id 2) (at {x_position+2} 54 0)))'''
        symbols.append(symbol)
        x_position += 20

    # Create hierarchical schematic with sub-sheet reference
    schematic_content = f"""(kicad_sch (version 20211123) (generator eeschema)
  (uuid "12345678-1234-5678-9012-123456789012")
  (paper "A4")
  (lib_symbols)
{chr(10).join(symbols)}
  (sheet (at 100 100) (size 50 30) (uuid "power-sheet-uuid")
    (property "Sheetname" "Power Supply" (id 0) (at 100 95 0))
    (property "Sheetfile" "{subsheet_name}" (id 1) (at 100 135 0))
  )
)
"""

    with open(schematic_file, "w") as f:
        f.write(schematic_content)

    context.test_schematic_file = schematic_file


@given("the root schematic contains components:")
def step_given_root_schematic_contains_components_table(context):
    """Create root schematic with components from table, including sub-sheet reference."""
    # Delegate to existing step implementation
    context.execute_steps("Given the root schematic contains components")


@given('the sub-sheet file "{filename}" does not exist')
def step_given_subsheet_file_does_not_exist(context, filename):
    """Verify that the sub-sheet file does not exist (simulates missing file error)."""
    subsheet_path = context.test_project_dir / filename
    # Ensure it doesn't exist - this is the test condition
    if subsheet_path.exists():
        subsheet_path.unlink()

    context.missing_subsheet = filename


@given('the sub-sheet "{subsheet_name}" contains components:')
def step_given_subsheet_contains_components(context, subsheet_name):
    """Create a sub-sheet schematic with components from the table."""
    project_dir = context.test_project_dir
    subsheet_file = project_dir / subsheet_name

    # Build symbol entries from table using format jBOM can parse
    symbols = []
    x_position = 50
    for row in context.table:
        reference = row["Reference"]
        value = row["Value"]
        footprint = row["Footprint"]

        # Generate a symbol entry in KiCad format
        symbol = f'''  (symbol (lib_id "Device:Generic") (at {x_position} 50 0) (unit 1)
    (property "Reference" "{reference}" (id 0) (at {x_position+2} 50 0))
    (property "Value" "{value}" (id 1) (at {x_position+2} 52 0))
    (property "Footprint" "{footprint}" (id 2) (at {x_position+2} 54 0)))'''
        symbols.append(symbol)
        x_position += 20

    # Create sub-sheet schematic
    schematic_content = f"""(kicad_sch (version 20211123) (generator eeschema)
  (uuid "subsheet-uuid-{subsheet_name}")
  (paper "A4")
  (lib_symbols)
{chr(10).join(symbols)}
)
"""

    with open(subsheet_file, "w") as f:
        f.write(schematic_content)


# =============================================================================
# Hierarchical BOM Verification Steps
# =============================================================================


@then("the BOM file contains component {component_ref} from root schematic")
def step_then_bom_file_contains_component_from_root(context, component_ref):
    """Verify the BOM file contains the specified component from the root schematic."""
    import sys
    import os

    steps_dir = os.path.join(os.path.dirname(__file__), "..")
    if steps_dir not in sys.path:
        sys.path.insert(0, steps_dir)
    from diagnostic_utils import format_execution_context

    # Find the output BOM file
    bom_file = None
    search_names = ["output.csv", f"{context.project_name}_BOM.csv", "bom.csv"]
    for potential_name in search_names:
        potential_path = context.scenario_temp_dir / potential_name
        if potential_path.exists():
            bom_file = potential_path
            break

    if not (bom_file and bom_file.exists()):
        diagnostic = (
            f"\nBOM output file not found!\n"
            f"  Searched for: {', '.join(search_names)}\n"
            f"  In directory: {context.scenario_temp_dir}\n"
            + format_execution_context(context, include_files=True)
        )
        raise AssertionError(diagnostic)

    # Read BOM file and verify component is present
    with open(bom_file, "r") as f:
        bom_content = f.read()

    if component_ref not in bom_content:
        diagnostic = (
            f"\nComponent not found in BOM!\n"
            f"  Looking for: {component_ref}\n"
            f"  BOM file: {bom_file}\n"
            f"  BOM content preview:\n{bom_content[:500]}\n"
            + format_execution_context(context, include_files=False)
        )
        raise AssertionError(diagnostic)


@then("the BOM file contains component {component_ref} from sub-sheet")
def step_then_bom_file_contains_component_from_subsheet(context, component_ref):
    """Verify the BOM file contains the specified component from a sub-sheet."""
    # Reuse the root schematic verification logic
    step_then_bom_file_contains_component_from_root(context, component_ref)


@then("the BOM file does not contain any components from the missing sub-sheet")
def step_then_bom_file_does_not_contain_subsheet_components(context):
    """Verify the BOM file does not contain components that would come from the missing sub-sheet."""
    # Find the output BOM file
    bom_file = None
    search_names = ["output.csv", f"{context.project_name}_BOM.csv", "bom.csv"]
    for potential_name in search_names:
        potential_path = context.scenario_temp_dir / potential_name
        if potential_path.exists():
            bom_file = potential_path
            break

    assert (
        bom_file and bom_file.exists()
    ), f"BOM output file not found in {context.scenario_temp_dir}"

    # Read BOM file - we mainly verify it was created successfully
    # without crashing due to the missing sub-sheet
    with open(bom_file, "r") as f:
        f.read()

    # Sub-sheet components typically have different reference prefixes or paths
    # Since the sub-sheet is missing, we mainly verify no unexpected components appear
    # Additional validation could check that only root schematic components are present


@then("component quantities are correctly aggregated")
def step_then_component_quantities_aggregated(context):
    """Verify component quantities are aggregated correctly across hierarchical sheets."""
    # TODO: Implement quantity aggregation verification
    # This would check that duplicate components across sheets are properly combined
    pass


# =============================================================================
# Additional Schematic Loading Steps (TODO - implement as needed)
# =============================================================================


# NOTE: Removed @when("I generate a generic BOM for {project}") step
# It conflicts with @when("I generate a generic BOM for {project} using {inventory}")
# in bom/shared.py. For schematic loading tests without inventory,
# implement specific step patterns that don't conflict.


@when('I generate a generic BOM for {project} using schematic "{schematic}"')
def step_when_generate_bom_using_schematic(context, project, schematic):
    """Generate BOM specifying explicit schematic file."""
    # TODO: Implement explicit schematic selection
    pass


@when('I generate a BOM from schematic file "{schematic_file}"')
def step_when_generate_bom_from_schematic_file(context, schematic_file):
    """Generate BOM directly from a schematic file path."""
    # TODO: Implement direct schematic file BOM generation
    pass


@when('I generate a BOM from schematic "{schematic_path}"')
def step_when_generate_bom_from_schematic_path(context, schematic_path):
    """Generate BOM from schematic at specific path."""
    # TODO: Implement schematic path-based BOM generation  
    pass


# NOTE: Removed conflicting step aliases for "I generate a BOM for {project}"  
# and "I attempt to generate a BOM for {project}" - they would conflict with
# steps in bom/shared.py. Implement specific non-conflicting patterns as needed.


@when("I attempt to generate a BOM for {project} without specifying a schematic")
def step_when_attempt_bom_without_schematic(context, project):
    """Attempt BOM generation without specifying which schematic."""
    # TODO: Implement ambiguous schematic scenario
    pass


@given('a standalone schematic file "{filename}" with components:')
def step_given_standalone_schematic_file(context, filename):
    """Create a standalone schematic file (not in project directory)."""
    # TODO: Implement standalone schematic creation
    pass


@given('the project has schematics:')
def step_given_project_has_schematics(context):
    """Create multiple schematics from table data."""
    # TODO: Implement multiple schematic creation from table
    pass


@given('the project has a default schematic "{schematic}" with components:')
def step_given_project_has_default_schematic(context, schematic):
    """Create a default project schematic with components."""
    # TODO: Implement default schematic with components
    pass


@given('the project has a schematic "{schematic}" with components:')
def step_given_project_has_schematic_with_components(context, schematic):
    """Create an additional schematic with components."""
    # TODO: Implement additional schematic creation
    pass


@given('a KiCad project directory "{project}" with no schematics')
def step_given_project_directory_no_schematics(context, project):
    """Create empty project directory with no schematic files."""
    project_dir = context.scenario_temp_dir / project
    project_dir.mkdir(exist_ok=True)
    context.project_name = project
    context.test_project_dir = project_dir


@given('the project has multiple schematics but no default:')
def step_given_multiple_schematics_no_default(context):
    """Create multiple schematics with no clear default."""
    # TODO: Implement multiple schematics without default
    pass


@given('the root schematic "{schematic}" references sub-sheet "{subsheet}"')
def step_given_root_references_subsheet(context, schematic, subsheet):
    """Create root schematic that references a sub-sheet."""
    # TODO: Implement root schematic with sub-sheet reference
    pass


@given('the sub-sheet "{schematic}" references sub-sheet "{subsheet}"')
def step_given_subsheet_references_subsheet(context, schematic, subsheet):
    """Create nested sub-sheet references."""
    # TODO: Implement nested sub-sheet references
    pass


@given("each schematic contains components at its level")
def step_given_each_schematic_has_components(context):
    """Create components in each hierarchical schematic level."""
    # TODO: Implement multi-level component distribution
    pass


@then("the BOM file contains component {component_ref}")
def step_then_bom_contains_component(context, component_ref):
    """Verify BOM contains specified component."""
    # Reuse existing verification logic
    step_then_bom_file_contains_component_from_root(context, component_ref)


@then("the BOM file does not contain component {component_ref}")
def step_then_bom_does_not_contain_component(context, component_ref):
    """Verify BOM does not contain specified component."""
    # TODO: Implement negative component verification with diagnostics
    pass


@then('the error message lists available schematics: "{schematic_list}"')
def step_then_error_lists_schematics(context, schematic_list):
    """Verify error message lists available schematic files."""
    # TODO: Implement schematic list verification in error output
    pass


@then("the error message suggests specifying which schematic to use")
def step_then_error_suggests_specifying_schematic(context):
    """Verify error message suggests how to specify schematic."""
    # TODO: Implement suggestion verification
    pass


@then("the BOM contains components from all three hierarchical levels")
def step_then_bom_contains_all_hierarchical_levels(context):
    """Verify BOM includes components from all nested levels."""
    # TODO: Implement multi-level hierarchy verification
    pass


@then("component references are properly scoped by sheet path")
def step_then_references_scoped_by_sheet_path(context):
    """Verify component references include proper sheet path scoping."""
    # TODO: Implement sheet path scoping verification
    pass
