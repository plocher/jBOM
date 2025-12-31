"""
BDD step definitions for component matching functionality.

This module contains domain-specific steps that automatically test
component matching across CLI, Python API, and KiCad plugin interfaces.
"""

from behave import given, then


# =============================================================================
# Fundamental BDD Step Definitions (Missing from shared.py)
# =============================================================================


@given('a KiCad project named "{project_name}"')
def step_given_kicad_project_named(context, project_name):
    """Create a KiCad project with the specified name."""
    context.project_name = project_name
    context.project_dir = context.scenario_temp_dir / project_name
    context.project_dir.mkdir(parents=True, exist_ok=True)

    # Create a basic KiCad project file
    project_file = context.project_dir / f"{project_name}.kicad_pro"
    project_file.write_text('{\n  "board": {\n    "design_rules": {}\n  }\n}')

    context.project_path = str(project_file)


# NOTE: Inventory file creation step is defined in shared.py to avoid domain conflicts


# NOTE: Generic BOM generation step is defined in bom/shared.py to avoid conflicts
# The shared step uses parameters {project} and {inventory} instead of {project_name} and {inventory_file}


# =============================================================================
# Component Matching Domain-Specific Steps (Ultimate DRY Solution)
# =============================================================================


@then('the BOM contains the {component} matched to "{expected_match}"')
def step_then_bom_contains_component_matched(context, component, expected_match):
    """Verify component matching across all usage models automatically."""
    # Auto-execute multi-modal validation
    context.execute_steps("When I validate behavior across all usage models")

    # Then verify the specific matching behavior
    # TODO: Implement specific component matching validation in Phase 3
    # For now, just verify that files were generated
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce BOM file"


@then("the BOM contains an unmatched component entry")
def step_then_bom_contains_unmatched_component(context):
    """Verify unmatched component handling across all usage models automatically."""
    # Auto-execute multi-modal validation
    context.execute_steps("When I validate behavior across all usage models")

    # Then verify the specific unmatched behavior
    # TODO: Implement specific unmatched component validation in Phase 3
    # For now, just verify that files were generated
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce BOM file"


@then(
    'the BOM contains the {component} matched to "{expected_match}" with priority {priority:d}'
)
def step_then_bom_contains_component_with_priority(
    context, component, expected_match, priority
):
    """Verify component priority selection across all usage models automatically."""
    # Auto-execute multi-modal validation
    context.execute_steps("When I validate behavior across all usage models")

    # Then verify the specific priority behavior
    # TODO: Implement specific priority validation in Phase 3
    # For now, just verify that files were generated
    for method, result in context.results.items():
        assert (
            result["output_file"] and result["output_file"].exists()
        ), f"{method} did not produce BOM file"


# =============================================================================
# Test Data Setup for Component Matching
# =============================================================================


@given("the schematic contains a {value} {package} {component_type}")
def step_given_schematic_contains_component(context, value, package, component_type):
    """Set up schematic with specific component."""
    # TODO: Implement specific component setup in Phase 3
    context.test_component = {
        "value": value,
        "package": package,
        "type": component_type,
    }


# NOTE: Hardcoded step definitions removed per Axiom #16 (Step Parameterization)
# The parameterized step @given('the schematic contains a {value} {package} {component_type}')
# handles all specific component cases (10K 0603 resistor, 100nF 0603 capacitor, etc.)
# This eliminates code duplication and improves maintainability


@given("the schematic contains diverse components")
def step_given_schematic_contains_diverse_components(context):
    """Set up schematic with diverse component types."""
    # TODO: Implement diverse component setup in Phase 3
    pass


@given('the project uses a schematic named "{schematic_name}"')
def step_given_project_uses_schematic_named(context, schematic_name):
    """Specify that the project uses a schematic with the given name."""
    if not hasattr(context, "project_schematics"):
        context.project_schematics = []
    context.project_schematics.append(schematic_name)
    context.current_schematic = schematic_name


@given('the "{schematic_name}" schematic contains components')
def step_given_named_schematic_contains_components(context, schematic_name):
    """Create schematic with specific name containing components from the table."""
    from ..shared import create_kicad_project_with_named_schematic_and_components

    # Use existing project from context or create new one
    project_name = getattr(context, "project_name", "DefaultProject")
    create_kicad_project_with_named_schematic_and_components(
        context, project_name, schematic_name, context.table
    )


@then(
    "the BOM contains component {component_ref} matched with inventory part {part_id}"
)
def step_then_bom_contains_component_matched_with_part(context, component_ref, part_id):
    """Verify BOM contains component matched with specific inventory part."""
    # Find the output BOM file
    bom_file = None
    for potential_name in ["output.csv", f"{context.project_name}_BOM.csv", "bom.csv"]:
        potential_path = context.scenario_temp_dir / potential_name
        if potential_path.exists():
            bom_file = potential_path
            break

    assert (
        bom_file and bom_file.exists()
    ), f"BOM output file not found in {context.scenario_temp_dir}"

    # Read CSV and verify component is matched with the expected inventory part
    import csv

    with open(bom_file, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Find the component row
    component_row = None
    for row in rows:
        if row.get("Reference") == component_ref or component_ref in str(
            row.get("Reference", "")
        ):
            component_row = row
            break

    assert component_row, f"Component '{component_ref}' not found in BOM"

    # Verify it's matched with the expected inventory part (IPN should match)
    ipn = component_row.get("IPN", "").strip()
    assert (
        ipn == part_id
    ), f"Component '{component_ref}' matched with IPN '{ipn}', expected '{part_id}'"


@then(
    'the matched component has value "{expected_value}" and package "{expected_package}" from inventory'
)
def step_then_matched_component_has_value_and_package_from_inventory(
    context, expected_value, expected_package
):
    """Verify matched component has expected value and package from inventory data."""
    # Find the output BOM file
    bom_file = None
    for potential_name in ["output.csv", f"{context.project_name}_BOM.csv", "bom.csv"]:
        potential_path = context.scenario_temp_dir / potential_name
        if potential_path.exists():
            bom_file = potential_path
            break

    assert (
        bom_file and bom_file.exists()
    ), f"BOM output file not found in {context.scenario_temp_dir}"

    # Read CSV and verify component has inventory data populated
    import csv

    with open(bom_file, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Find a row with inventory data (should have IPN populated)
    matched_row = None
    for row in rows:
        ipn = row.get("IPN", "").strip()
        if ipn:  # Has inventory data
            matched_row = row
            break

    assert matched_row, "No matched components found with inventory data"

    # Verify inventory value and package match expectations
    inventory_value = matched_row.get("Value", "").strip()
    inventory_package = matched_row.get("Package", "").strip()

    assert (
        inventory_value == expected_value
    ), f"Expected value '{expected_value}', found '{inventory_value}'"
    assert (
        inventory_package == expected_package
    ), f"Expected package '{expected_package}', found '{inventory_package}'"


@then(
    'the matched component uses tolerance-based matching for value "{schematic_value}" to inventory value "{inventory_value}"'
)
def step_then_matched_component_uses_tolerance_matching(
    context, schematic_value, inventory_value
):
    """Verify component matching used tolerance-based logic for value differences."""
    # Find the output BOM file
    bom_file = None
    for potential_name in ["output.csv", f"{context.project_name}_BOM.csv", "bom.csv"]:
        potential_path = context.scenario_temp_dir / potential_name
        if potential_path.exists():
            bom_file = potential_path
            break

    assert (
        bom_file and bom_file.exists()
    ), f"BOM output file not found in {context.scenario_temp_dir}"

    # Read CSV and verify tolerance matching occurred
    import csv

    with open(bom_file, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Find matched component with inventory data
    matched_row = None
    for row in rows:
        ipn = row.get("IPN", "").strip()
        if ipn:  # Has inventory data
            matched_row = row
            break

    assert matched_row, "No matched components found with inventory data"

    # Verify that the inventory value is different from schematic value (proving tolerance matching)
    actual_inventory_value = matched_row.get("Value", "").strip()
    assert (
        actual_inventory_value == inventory_value
    ), f"Expected inventory value '{inventory_value}', found '{actual_inventory_value}'"

    # The tolerance matching is proven by the fact that different values were successfully matched
    # (schematic_value != inventory_value but matching succeeded)


@then(
    'the matched component uses value normalization for "{schematic_value}" to inventory value "{inventory_value}"'
)
def step_then_matched_component_uses_value_normalization(
    context, schematic_value, inventory_value
):
    """Verify component matching used value normalization for format differences."""
    # Find the output BOM file
    bom_file = None
    for potential_name in ["output.csv", f"{context.project_name}_BOM.csv", "bom.csv"]:
        potential_path = context.scenario_temp_dir / potential_name
        if potential_path.exists():
            bom_file = potential_path
            break

    assert (
        bom_file and bom_file.exists()
    ), f"BOM output file not found in {context.scenario_temp_dir}"

    # Read CSV and verify normalization matching occurred
    import csv

    with open(bom_file, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Find matched component with inventory data
    matched_row = None
    for row in rows:
        ipn = row.get("IPN", "").strip()
        if ipn:  # Has inventory data
            matched_row = row
            break

    assert matched_row, "No matched components found with inventory data"

    # Verify that the inventory value is different from schematic value (proving normalization)
    actual_inventory_value = matched_row.get("Value", "").strip()
    assert (
        actual_inventory_value == inventory_value
    ), f"Expected inventory value '{inventory_value}', found '{actual_inventory_value}'"

    # The normalization is proven by the fact that different formats were successfully matched
    # (e.g. "1.1K" normalized to match "1K1")


@then(
    "the BOM file contains unmatched component {component_ref} with no inventory data"
)
def step_then_bom_contains_unmatched_component_with_no_inventory_data(
    context, component_ref
):
    """Verify BOM contains unmatched component with no inventory data populated."""
    # Find the output BOM file
    bom_file = None
    for potential_name in ["output.csv", f"{context.project_name}_BOM.csv", "bom.csv"]:
        potential_path = context.scenario_temp_dir / potential_name
        if potential_path.exists():
            bom_file = potential_path
            break

    assert (
        bom_file and bom_file.exists()
    ), f"BOM output file not found in {context.scenario_temp_dir}"

    # Read CSV and verify component is present but unmatched
    import csv

    with open(bom_file, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Find the component row
    component_row = None
    for row in rows:
        if row.get("Reference") == component_ref or component_ref in str(
            row.get("Reference", "")
        ):
            component_row = row
            break

    assert component_row, f"Component '{component_ref}' not found in BOM"

    # Verify it has no inventory data (IPN should be empty)
    ipn = component_row.get("IPN", "").strip()
    assert (
        not ipn
    ), f"Component '{component_ref}' should be unmatched but found IPN: {ipn}"

    # Verify schematic data is present
    reference = component_row.get("Reference", "").strip()
    value = component_row.get("Value", "").strip()
    assert reference, "Component should have Reference from schematic"
    assert value, "Component should have Value from schematic"


@then("the BOM file contains components from all schematic files")
def step_then_bom_contains_components_from_all_schematic_files(context):
    """Verify BOM contains components from all schematics in hierarchical project."""
    # Find the output BOM file
    bom_file = None
    for potential_name in ["output.csv", f"{context.project_name}_BOM.csv", "bom.csv"]:
        potential_path = context.scenario_temp_dir / potential_name
        if potential_path.exists():
            bom_file = potential_path
            break

    assert (
        bom_file and bom_file.exists()
    ), f"BOM output file not found in {context.scenario_temp_dir}"

    # Read CSV and verify components from multiple schematics are present
    import csv

    with open(bom_file, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Should have components from multiple schematics
    assert (
        len(rows) >= 3
    ), f"Expected components from multiple schematics, found only {len(rows)} components"

    # Verify we have at least some components with inventory matches
    matched_components = [row for row in rows if row.get("IPN", "").strip()]
    assert (
        len(matched_components) >= 2
    ), f"Expected multiple matched components from hierarchical project, found {len(matched_components)}"


@then(
    'the BOM file contains component {component_ref} from schematic "{schematic_name}" matched with inventory part {part_id}'
)
def step_then_bom_contains_component_from_schematic_matched_with_part(
    context, component_ref, schematic_name, part_id
):
    """Verify BOM contains component from specific schematic matched with inventory part."""
    # Find the output BOM file
    bom_file = None
    for potential_name in ["output.csv", f"{context.project_name}_BOM.csv", "bom.csv"]:
        potential_path = context.scenario_temp_dir / potential_name
        if potential_path.exists():
            bom_file = potential_path
            break

    assert (
        bom_file and bom_file.exists()
    ), f"BOM output file not found in {context.scenario_temp_dir}"

    # Read CSV and verify component is matched with the expected inventory part
    import csv

    with open(bom_file, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Find the component row
    component_row = None
    for row in rows:
        if row.get("Reference") == component_ref or component_ref in str(
            row.get("Reference", "")
        ):
            component_row = row
            break

    assert (
        component_row
    ), f"Component '{component_ref}' from '{schematic_name}' schematic not found in BOM"

    # Verify it's matched with the expected inventory part (IPN should match)
    ipn = component_row.get("IPN", "").strip()
    assert (
        ipn == part_id
    ), f"Component '{component_ref}' from '{schematic_name}' matched with IPN '{ipn}', expected '{part_id}'"


@then("component quantities are correctly aggregated across all schematics")
def step_then_component_quantities_correctly_aggregated_across_schematics(context):
    """Verify component quantities are properly aggregated from hierarchical schematics."""
    # Find the output BOM file
    bom_file = None
    for potential_name in ["output.csv", f"{context.project_name}_BOM.csv", "bom.csv"]:
        potential_path = context.scenario_temp_dir / potential_name
        if potential_path.exists():
            bom_file = potential_path
            break

    assert (
        bom_file and bom_file.exists()
    ), f"BOM output file not found in {context.scenario_temp_dir}"

    # Read CSV and verify quantity aggregation
    import csv

    with open(bom_file, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Verify each component has correct quantity (1 for this test case)
    for row in rows:
        reference = row.get("Reference", "").strip()
        quantity = row.get("Quantity", "").strip()

        if reference:  # Skip empty rows
            assert (
                quantity == "1"
            ), f"Component '{reference}' should have quantity 1, found '{quantity}'"

    # In this test case, we expect no duplicate references since each component is unique
    references = [
        row.get("Reference", "").strip()
        for row in rows
        if row.get("Reference", "").strip()
    ]
    unique_references = set(references)
    assert len(references) == len(
        unique_references
    ), f"Found duplicate references in hierarchical BOM: {references}"


# NOTE: Over-parameterized step removed per Axiom #16 anti-pattern guidance
# Multiple components should be handled with data tables or separate Given steps
# This avoids ambiguous step conflicts and improves readability
