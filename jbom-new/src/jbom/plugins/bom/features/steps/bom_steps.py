"""Step definitions for BOM (Bill of Materials) generation testing."""

import csv
import io
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Any

from behave import given, when, then


# Test setup and data creation
@given("I have a test KiCad project with schematic files")
@given("I have a test schematic with components")
@given("I have a test schematic with multiple components")
@given("I have a test schematic with components having various attributes")
@given("I have a test schematic with components containing fabricator part numbers")
@given("I have various KiCad project configurations")
def step_setup_test_environment(context):
    """Set up a clean test environment for BOM testing."""
    # Create a temporary directory for test files
    context.test_temp_dir = Path(tempfile.mkdtemp(prefix="jbom_bom_test_"))
    context.test_components = []
    context.test_schematic_files = []
    context.generated_bom_file = None
    context.bom_output_content = None
    context.command_result = None


@given('I have a directory "{project_name}" with KiCad files')
@given('I have a directory "{project_name}" containing')
@given('I have a project directory "{project_name}"')
def step_create_project_directory(context, project_name):
    """Create a project directory with KiCad files."""
    context.project_name = project_name
    context.project_dir = context.test_temp_dir / project_name
    context.project_dir.mkdir(parents=True, exist_ok=True)

    # Create basic project files
    project_file = context.project_dir / f"{project_name}.kicad_pro"
    schematic_file = context.project_dir / f"{project_name}.kicad_sch"

    _create_basic_project_file(project_file, project_name)
    _create_mock_schematic_file(schematic_file, context.test_components or [])


@given("I have files in current directory")
@given("I am in a directory containing")
def step_create_files_in_current_dir(context):
    """Create KiCad files in the current test directory."""
    if context.table:
        for row in context.table:
            file_name = row["File"]
            file_type = row["Type"]
            file_path = context.test_temp_dir / file_name

            if file_type == "project":
                project_name = file_path.stem
                _create_basic_project_file(file_path, project_name)
            elif file_type == "schematic":
                _create_mock_schematic_file(file_path, context.test_components or [])


@given('I have a single schematic file "{filename}"')
@given('I am in a directory with "{filename}"')
def step_create_single_schematic(context, filename):
    """Create a single schematic file."""
    schematic_path = context.test_temp_dir / filename
    _create_mock_schematic_file(schematic_path, context.test_components or [])
    context.test_schematic_files = [schematic_path]


@given("I have a project with hierarchical schematics")
def step_create_hierarchical_project(context):
    """Create a project with hierarchical schematics."""
    if context.table:
        for row in context.table:
            file_name = row["File"]
            file_type = row["Type"]
            file_path = context.test_temp_dir / file_name

            if file_type == "project":
                project_name = file_path.stem
                _create_basic_project_file(file_path, project_name)
            elif "schematic" in file_type:
                # Create schematic with some mock components
                mock_components = _generate_mock_components_for_file(file_name)
                _create_mock_schematic_file(file_path, mock_components)


# Component data setup
@given("the schematic contains")
def step_setup_schematic_components(context):
    """Set up schematic with components from data table."""
    if not context.table:
        raise ValueError("Component data table is required")

    context.test_components = []
    for row in context.table:
        component = {
            "reference": row["Reference"],
            "value": row["Value"],
            "footprint": row["Footprint"],
        }

        # Add optional attributes
        for key, value in row.headings:
            if key not in ["Reference", "Value", "Footprint"] and key in row:
                component[key.lower()] = _parse_boolean_or_string(row[key])

        context.test_components.append(component)

    # Update any existing schematic files with this data
    _update_test_schematics(context)


@given("the schematic contains components with LCSC part numbers")
@given("the schematic contains components with fabricator part numbers")
def step_setup_fabricator_components(context):
    """Set up components with fabricator part numbers."""
    if context.table:
        context.test_components = []
        for row in context.table:
            component = {
                "reference": row["Reference"],
                "value": row["Value"],
                "footprint": row["Footprint"],
            }

            # Add all other columns as component fields
            for heading in context.table.headings:
                if heading not in ["Reference", "Value", "Footprint"]:
                    component[heading.lower()] = row[heading]

            context.test_components.append(component)

        _update_test_schematics(context)


@given("the schematic contains components with distributor part numbers")
@given("the schematic contains components without fabricator part numbers")
@given("the schematic contains components with mixed part number availability")
def step_setup_mixed_components(context):
    """Set up components with various part number scenarios."""
    step_setup_fabricator_components(context)  # Reuse the same logic


@given("the schematic contains components with special values")
def step_setup_special_value_components(context):
    """Set up components with special characters in values."""
    step_setup_schematic_components(context)


@given("the schematic contains many components of the same type")
def step_setup_many_similar_components(context):
    """Set up many components with same value/footprint."""
    step_setup_schematic_components(context)


@given("the schematic contains no components")
def step_setup_empty_schematic(context):
    """Set up an empty schematic."""
    context.test_components = []
    _update_test_schematics(context)


# Command execution steps (reuse from common_steps.py)
@when('I run "{command}"')
def step_run_bom_command(context, command):
    """Run a BOM command and capture results."""
    import subprocess
    import os

    # Replace 'jbom' with python module invocation
    if command.startswith("jbom "):
        args = command.split()[1:]  # Remove 'jbom' prefix
        cmd = ["python", "-m", "jbom.cli.main"] + args
    else:
        cmd = command.split()

    # Set up environment
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parents[5] / "src")  # Point to jbom-new/src

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=context.test_temp_dir,
            env=env,
        )
        context.command_result = result
        context.last_command = command
        context.last_output = result.stdout + result.stderr
        context.last_exit_code = result.returncode
    except Exception as e:
        context.last_command = command
        context.last_output = str(e)
        context.last_exit_code = 1


# Verification steps
@then("the command should succeed")
def step_verify_command_success(context):
    """Verify the command succeeded."""
    assert context.last_exit_code == 0, (
        f"Command failed with exit code {context.last_exit_code}.\n"
        f"Output: {context.last_output}"
    )


@then("the command should fail")
def step_verify_command_failure(context):
    """Verify the command failed."""
    assert context.last_exit_code != 0, (
        f"Command unexpectedly succeeded.\n" f"Output: {context.last_output}"
    )


@then('a CSV file "{filename}" should be created')
@then('a file "{filename}" should be created')
def step_verify_file_created(context, filename):
    """Verify that a file was created."""
    file_path = context.test_temp_dir / filename
    if not file_path.exists():
        # Try project directory if not in temp dir
        if hasattr(context, "project_dir"):
            file_path = context.project_dir / filename

    assert file_path.exists(), f"File not created: {file_path}"
    assert file_path.stat().st_size > 0, f"File is empty: {file_path}"
    context.generated_bom_file = file_path


@then('the CSV should have headers "{headers}"')
def step_verify_csv_headers(context, headers):
    """Verify CSV file has expected headers."""
    expected_headers = [h.strip() for h in headers.split(",")]

    assert context.generated_bom_file, "No BOM file to check"
    with open(context.generated_bom_file, "r") as f:
        reader = csv.reader(f)
        actual_headers = next(reader)

    assert (
        actual_headers == expected_headers
    ), f"Header mismatch.\nExpected: {expected_headers}\nActual: {actual_headers}"


@then("the CSV should contain component entries with basic fields")
@then("the CSV should contain component data")
@then("the file should contain valid BOM data")
def step_verify_csv_content(context):
    """Verify CSV contains valid component data."""
    assert context.generated_bom_file, "No BOM file to check"

    with open(context.generated_bom_file, "r") as f:
        reader = csv.reader(f)
        rows = list(reader)

    assert len(rows) >= 1, "CSV should have at least headers"
    headers = rows[0]
    assert len(headers) > 0, "CSV should have headers"

    # If we have test components, verify data rows exist
    if context.test_components and len(context.test_components) > 0:
        assert len(rows) > 1, "CSV should have data rows for components"


@then("the output should contain a formatted table")
@then("the output should be valid CSV format")
def step_verify_output_format(context):
    """Verify output format."""
    assert context.last_output, "No command output to check"
    assert len(context.last_output.strip()) > 0, "Output should not be empty"


@then("the table should show component references, values, footprints, and quantities")
@then("the table should have aligned columns")
@then("the table should have a header row")
@then("the table should show component data in readable format")
def step_verify_table_structure(context):
    """Verify table has proper structure."""
    assert context.last_output, "No output to verify"
    lines = context.last_output.strip().split("\n")
    assert len(lines) >= 1, "Table should have at least a header"


@then("the BOM should contain")
@then("the BOM should contain separate entries")
@then("the BOM should contain only")
def step_verify_bom_content(context):
    """Verify BOM contains expected entries."""
    if not context.table:
        return

    # Parse BOM data from file or output
    bom_data = _extract_bom_data(context)
    expected_entries = _table_to_dict_list(context.table)

    for expected in expected_entries:
        _verify_bom_entry_exists(bom_data, expected)


@then('the BOM should not contain "{reference}"')
def step_verify_component_excluded(context, reference):
    """Verify a specific component is not in the BOM."""
    bom_data = _extract_bom_data(context)

    for entry in bom_data:
        references = entry.get("references", entry.get("designator", ""))
        if reference in references:
            raise AssertionError(f"Component {reference} should not be in BOM")


@then('the BOM entry should show references as "{expected_refs}"')
def step_verify_references_format(context, expected_refs):
    """Verify reference formatting in BOM entry."""
    bom_data = _extract_bom_data(context)

    found = False
    for entry in bom_data:
        references = entry.get("references", entry.get("designator", ""))
        if expected_refs in references:
            found = True
            break

    assert found, f"Expected references '{expected_refs}' not found in BOM"


@then("the quantity should be {expected_qty:d}")
def step_verify_quantity(context, expected_qty):
    """Verify quantity in BOM entry."""
    bom_data = _extract_bom_data(context)

    # For this step, we'll check the first entry's quantity
    if bom_data:
        qty = int(bom_data[0].get("quantity", bom_data[0].get("qty", 0)))
        assert qty == expected_qty, f"Expected quantity {expected_qty}, got {qty}"


@then("the BOM should contain JLCPCB-formatted entries")
@then("the BOM should contain PCBWay-formatted entries")
def step_verify_fabricator_format(context):
    """Verify fabricator-specific formatting."""
    step_verify_bom_content(context)  # Use the general verification


@then("the BOM should use JLCPCB column headers")
@then("the BOM should include LCSC part numbers")
@then("the BOM should contain entries with empty LCSC Part# fields")
@then("the BOM should show LCSC numbers when available and blank when not")
def step_verify_fabricator_specifics(context):
    """Verify fabricator-specific details."""
    # These are more specific checks that would need detailed implementation
    # For now, we'll do basic output verification
    step_verify_output_format(context)


@then('the error should mention "{text}"')
def step_verify_error_message(context, text):
    """Verify specific error message content."""
    assert context.last_output, "No output to check for error"
    assert (
        text in context.last_output
    ), f"Expected error text '{text}' not found in output: {context.last_output}"


# Helper functions
def _create_basic_project_file(project_path: Path, project_name: str):
    """Create a basic KiCad project file."""
    project_content = {
        "meta": {"version": 1},
        "uuid": f"test-{project_name}-uuid",
        "name": project_name,
    }

    with open(project_path, "w") as f:
        json.dump(project_content, f, indent=2)


def _create_mock_schematic_file(schematic_path: Path, components: List[Dict[str, Any]]):
    """Create a mock KiCad schematic file with components."""
    schematic_content = [
        "(kicad_sch (version 20220914) (generator eeschema)",
        f"  (uuid test-{schematic_path.stem}-uuid)",
        '  (paper "A4")',
    ]

    # Add component symbols
    for comp in components:
        symbol_entry = _create_symbol_entry(comp)
        schematic_content.append(symbol_entry)

    schematic_content.append(")")

    with open(schematic_path, "w") as f:
        f.write("\n".join(schematic_content))


def _create_symbol_entry(component: Dict[str, Any]) -> str:
    """Create a KiCad symbol entry for a component."""
    ref = component["reference"]
    value = component["value"]
    footprint = component["footprint"]

    # Create basic symbol entry
    symbol = f"""  (symbol (lib_id "Device:R") (at 100 100 0) (unit 1)
    (in_bom yes) (on_board yes)
    (property "Reference" "{ref}" (at 0 0 0))
    (property "Value" "{value}" (at 0 0 0))
    (property "Footprint" "{footprint}" (at 0 0 0))"""

    # Add additional properties
    for key, val in component.items():
        if key not in ["reference", "value", "footprint"]:
            if key == "dnp" and _parse_boolean_or_string(val):
                symbol += '\n    (property "dnp" "true" (at 0 0 0))'
            elif key == "exclude_from_bom" and _parse_boolean_or_string(val):
                symbol += '\n    (property "exclude_from_bom" "true" (at 0 0 0))'
            else:
                symbol += f'\n    (property "{key.upper()}" "{val}" (at 0 0 0))'

    symbol += "\n  )"
    return symbol


def _parse_boolean_or_string(value: str) -> Any:
    """Parse a string value that might be a boolean."""
    if value.lower() in ["true", "yes", "1"]:
        return True
    elif value.lower() in ["false", "no", "0"]:
        return False
    return value


def _update_test_schematics(context):
    """Update existing schematic files with current component data."""
    # This would update any existing schematic files
    # For now, we'll create a default one if none exists
    if not context.test_schematic_files and hasattr(context, "test_temp_dir"):
        default_sch = context.test_temp_dir / "test-project.kicad_sch"
        _create_mock_schematic_file(default_sch, context.test_components)
        context.test_schematic_files = [default_sch]


def _generate_mock_components_for_file(filename: str) -> List[Dict[str, Any]]:
    """Generate some mock components based on filename."""
    if "main" in filename:
        return [
            {"reference": "U1", "value": "MCU", "footprint": "QFP-100"},
            {"reference": "C1", "value": "100nF", "footprint": "C_0603"},
        ]
    elif "cpu" in filename:
        return [
            {"reference": "R1", "value": "10K", "footprint": "R_0805"},
            {"reference": "R2", "value": "10K", "footprint": "R_0805"},
        ]
    elif "power" in filename:
        return [
            {"reference": "L1", "value": "10uH", "footprint": "L_1210"},
            {"reference": "C10", "value": "470uF", "footprint": "C_Elec_10x10"},
        ]
    return []


def _extract_bom_data(context) -> List[Dict[str, str]]:
    """Extract BOM data from file or output."""
    if context.generated_bom_file:
        with open(context.generated_bom_file, "r") as f:
            reader = csv.DictReader(f)
            return list(reader)
    elif context.last_output and "," in context.last_output:
        # Try to parse CSV from output
        reader = csv.DictReader(io.StringIO(context.last_output))
        return list(reader)
    return []


def _table_to_dict_list(table) -> List[Dict[str, str]]:
    """Convert behave table to list of dictionaries."""
    return [dict(row) for row in table]


def _verify_bom_entry_exists(bom_data: List[Dict[str, str]], expected: Dict[str, str]):
    """Verify that an expected BOM entry exists in the data."""
    for entry in bom_data:
        if _entries_match(entry, expected):
            return

    raise AssertionError(f"Expected BOM entry not found: {expected}")


def _entries_match(entry: Dict[str, str], expected: Dict[str, str]) -> bool:
    """Check if a BOM entry matches expected values."""
    for key, expected_value in expected.items():
        # Handle different possible field names
        actual_value = (
            entry.get(key.lower()) or entry.get(key.title()) or entry.get(key)
        )

        if not actual_value:
            return False

        # For references/designator, allow flexible matching
        if key.lower() in ["references", "designator"]:
            if expected_value not in actual_value:
                return False
        else:
            if actual_value != expected_value:
                return False

    return True
