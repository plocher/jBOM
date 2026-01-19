"""Step definitions for inventory plugin features."""

import os
import tempfile
import shutil
import csv
from pathlib import Path
from behave import given, when, then

from jbom.common.types import Component


@given("a clean test environment")
def step_clean_test_environment(context):
    """Set up a clean test environment."""
    # Create temporary directory for test
    if hasattr(context, "temp_dir") and context.temp_dir.exists():
        shutil.rmtree(context.temp_dir)

    context.temp_dir = Path(tempfile.mkdtemp())
    context.original_cwd = Path.cwd()
    os.chdir(context.temp_dir)


@given('a KiCad project named "{project_name}"')
def step_kicad_project(context, project_name):
    """Create a KiCad project with given name."""
    context.project_name = project_name
    context.project_dir = context.temp_dir / project_name
    context.project_dir.mkdir()

    # Create basic project files
    context.schematic_file = context.project_dir / f"{project_name}.kicad_sch"
    context.project_file = context.project_dir / f"{project_name}.kicad_pro"

    # Create minimal project file
    with open(context.project_file, "w") as f:
        f.write('{\n  "board": {\n    "design_settings": {}\n  }\n}')


@given("the schematic contains components:")
def step_schematic_components(context):
    """Define components in the schematic based on table data."""
    context.components = []

    for row in context.table:
        # Infer LibID from reference prefix if not provided
        lib_id = row.get("LibID")
        if not lib_id:
            ref = row["Reference"]
            ref_prefix = ref[0] if ref else "R"
            # Map common reference prefixes to LibID
            prefix_to_lib = {
                "R": "Device:R",
                "C": "Device:C",
                "L": "Device:L",
                "D": "Device:LED" if "LED" in row["Value"] else "Device:D",
                "U": "Timer:NE555P" if "555" in row["Value"] else "Device:U",
                "Q": "Device:Q",
                "J": "Device:J",
                "P": "Device:P",
            }
            lib_id = prefix_to_lib.get(ref_prefix, "Device:R")

        # Create Component object from table row
        component = Component(
            reference=row["Reference"],
            lib_id=lib_id,
            value=row["Value"],
            footprint=row["Footprint"],
            uuid=f"uuid-{row['Reference']}-test",
            properties={
                key: value
                for key, value in row.as_dict().items()
                if key not in ["Reference", "Value", "LibID", "Footprint", "Package"]
                and value
            },
            in_bom=True,
            exclude_from_sim=False,
            dnp=False,
        )
        context.components.append(component)

    # Create mock schematic content (simplified)
    _create_mock_schematic_file(context.schematic_file, context.components)


@given('an existing inventory file "{filename}" with components:')
def step_existing_inventory_file(context, filename):
    """Create an existing inventory file with given components."""
    inventory_path = context.project_dir / filename

    # Get field names from table headers
    fieldnames = context.table.headings

    # Write CSV file with components
    with open(inventory_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in context.table:
            writer.writerow(row.as_dict())


@given("the schematic contains no components")
def step_empty_schematic(context):
    """Create an empty schematic."""
    context.components = []
    _create_mock_schematic_file(context.schematic_file, context.components)


@when('I run "{command}" in the project directory')
def step_run_command(context, command):
    """Execute jbom command in the project directory."""
    import subprocess

    os.chdir(context.project_dir)

    # Execute the command directly - let it use the actual plugin code
    # Replace 'jbom' with 'python -m jbom.cli' to use local development version
    cmd_parts = command.split()
    if cmd_parts[0] == "jbom":
        cmd_parts[0:1] = ["python", "-m", "jbom.cli"]

    result = subprocess.run(
        cmd_parts,
        capture_output=True,
        text=True,
        cwd=context.project_dir,
        env={
            **os.environ,
            "PYTHONPATH": "/Users/jplocher/Dropbox/KiCad/jBOM/jbom-new/src",
        },
    )

    context.command_result = result
    context.stdout = result.stdout
    context.stderr = result.stderr
    context.exit_code = result.returncode


@then("the command exits with code {exit_code:d}")
def step_check_exit_code(context, exit_code):
    """Check command exit code."""
    assert (
        context.exit_code == exit_code
    ), f"Expected exit code {exit_code}, got {context.exit_code}. stderr: {context.stderr}"


@then('a file named "{filename}" exists in the project directory')
def step_file_exists(context, filename):
    """Check if file exists in project directory."""
    file_path = context.project_dir / filename
    assert (
        file_path.exists()
    ), f"File {filename} does not exist in {context.project_dir}"
    context.output_file = file_path


@then("the inventory file contains {count:d} unique items")
def step_inventory_item_count(context, count):
    """Check number of items in inventory file."""
    with open(context.output_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        items = list(reader)

    assert len(items) == count, f"Expected {count} items, found {len(items)}"
    context.inventory_items = items


@then("the inventory has standard columns: {column_list}")
def step_check_standard_columns(context, column_list):
    """Check that inventory has expected columns."""
    expected_columns = [col.strip() for col in column_list.split(",")]

    with open(context.output_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        actual_columns = reader.fieldnames

    for col in expected_columns:
        assert col in actual_columns, f"Column {col} not found in {actual_columns}"


@then("stdout contains CSV data with headers")
def step_stdout_has_csv_headers(context):
    """Check that stdout contains CSV headers."""
    lines = context.stdout.strip().split("\n")
    assert len(lines) > 0, "No output in stdout"

    # First line should contain headers
    headers = lines[0].split(",")
    assert "IPN" in headers, f"IPN not found in headers: {headers}"
    assert "Category" in headers, f"Category not found in headers: {headers}"


@then('stdout contains "{text}"')
def step_stdout_contains(context, text):
    """Check that stdout contains specific text."""
    assert text in context.stdout, f"'{text}' not found in stdout: {context.stdout}"


@then('the console output contains "{text}"')
def step_console_contains(context, text):
    """Check that console output contains specific text."""
    assert (
        text in context.stdout
    ), f"'{text}' not found in console output: {context.stdout}"


@then("the console output contains a formatted inventory table")
def step_console_has_table(context):
    """Check that console output has a formatted table."""
    # Look for table formatting indicators
    assert "|" in context.stdout, "No table formatting found in console output"
    assert "IPN" in context.stdout, "Table headers not found"


@then("the inventory contains exactly {count:d} unique items")
def step_exact_item_count(context, count):
    """Check exact number of items in stdout CSV."""
    lines = context.stdout.strip().split("\n")
    # Subtract 1 for header line
    actual_count = len(lines) - 1 if len(lines) > 1 else 0

    assert (
        actual_count == count
    ), f"Expected exactly {count} items, found {actual_count}"


@then(
    'stdout contains "{ipn}" for {tolerance} tolerance and "{ipn2}" for {tolerance2} tolerance'
)
def step_stdout_contains_tolerance_ipns(context, ipn, tolerance, ipn2, tolerance2):
    """Check that stdout contains specific IPNs for different tolerances."""
    assert ipn in context.stdout, f"'{ipn}' not found in stdout"
    assert ipn2 in context.stdout, f"'{ipn2}' not found in stdout"

    # Parse CSV to verify tolerance associations
    lines = context.stdout.strip().split("\n")
    if len(lines) > 1:
        headers = lines[0].split(",")
        tolerance_idx = next(
            (i for i, h in enumerate(headers) if "Tolerance" in h), None
        )
        ipn_idx = next((i for i, h in enumerate(headers) if "IPN" in h), None)

        if tolerance_idx is not None and ipn_idx is not None:
            found_ipn1 = False
            found_ipn2 = False

            for line in lines[1:]:
                fields = line.split(",")
                if len(fields) > max(ipn_idx, tolerance_idx):
                    line_ipn = fields[ipn_idx].strip('"')
                    line_tolerance = fields[tolerance_idx].strip('"')

                    if line_ipn == ipn and line_tolerance == tolerance:
                        found_ipn1 = True
                    if line_ipn == ipn2 and line_tolerance == tolerance2:
                        found_ipn2 = True

            assert found_ipn1, f"IPN '{ipn}' with {tolerance} tolerance not found"
            assert found_ipn2, f"IPN '{ipn2}' with {tolerance2} tolerance not found"


@then('stdout contains "{ipn}" with {tolerance} tolerance')
def step_stdout_contains_ipn_with_tolerance(context, ipn, tolerance):
    """Check that stdout contains specific IPN with tolerance."""
    assert ipn in context.stdout, f"'{ipn}' not found in stdout"

    # Parse CSV to verify tolerance
    lines = context.stdout.strip().split("\n")
    if len(lines) > 1:
        headers = lines[0].split(",")
        tolerance_idx = next(
            (i for i, h in enumerate(headers) if "Tolerance" in h), None
        )
        ipn_idx = next((i for i, h in enumerate(headers) if "IPN" in h), None)

        if tolerance_idx is not None and ipn_idx is not None:
            found = False
            for line in lines[1:]:
                fields = line.split(",")
                if len(fields) > max(ipn_idx, tolerance_idx):
                    line_ipn = fields[ipn_idx].strip('"')
                    line_tolerance = fields[tolerance_idx].strip('"')

                    if line_ipn == ipn and line_tolerance == tolerance:
                        found = True
                        break

            assert found, f"IPN '{ipn}' with {tolerance} tolerance not found"


@then("stdout contains property columns for {prop1} and {prop2}")
def step_stdout_has_property_columns(context, prop1, prop2):
    """Check that stdout has specific property columns."""
    lines = context.stdout.strip().split("\n")
    if len(lines) > 0:
        headers = lines[0].split(",")
        headers_str = ",".join(headers)

        assert prop1 in headers_str, f"Property column '{prop1}' not found in headers"
        assert prop2 in headers_str, f"Property column '{prop2}' not found in headers"


@then('stdout contains "{value1}" and "{value2}" in the data')
def step_stdout_contains_values_in_data(context, value1, value2):
    """Check that stdout contains specific values in the data rows."""
    lines = context.stdout.strip().split("\n")
    data_lines = lines[1:] if len(lines) > 1 else []

    data_str = "\n".join(data_lines)
    assert value1 in data_str, f"Value '{value1}' not found in CSV data"
    assert value2 in data_str, f"Value '{value2}' not found in CSV data"


def _create_mock_schematic_file(schematic_path: Path, components: list):
    """Create a proper KiCad schematic file for testing."""
    with open(schematic_path, "w") as f:
        f.write("(kicad_sch (version 20211123) (generator eeschema)\n")
        f.write("  (lib_symbols)\n")
        f.write('  (paper "A4")\n')

        for i, component in enumerate(components):
            # Create a proper symbol with instances and position
            f.write(
                f'  (symbol (lib_id "{component.lib_id}") (at 100 {50 + i*10}) (unit 1)\n'
            )
            f.write(
                f'    (in_bom yes) (on_board yes) (uuid "uuid-{component.reference}")\n'
            )
            f.write(
                f'    (property "Reference" "{component.reference}" '
                f"(id 0) (at 102 {48 + i*10}) (effects (font (size 1.27 1.27))))\n"
            )
            f.write(
                f'    (property "Value" "{component.value}" '
                f"(id 1) (at 102 {52 + i*10}) (effects (font (size 1.27 1.27))))\n"
            )
            f.write(
                f'    (property "Footprint" "{component.footprint}" '
                f"(id 2) (at 100 {50 + i*10}) (effects (font (size 1.27 1.27)) hide))\n"
            )

            # Add component properties
            prop_id = 3
            for key, value in component.properties.items():
                f.write(
                    f'    (property "{key}" "{value}" '
                    f"(id {prop_id}) (at 100 {50 + i*10}) "
                    f"(effects (font (size 1.27 1.27)) hide))\n"
                )
                prop_id += 1

            # Add instances block (required for KiCad 6+)
            f.write("    (instances\n")
            f.write(
                f'      (instance (reference "{component.reference}") '
                f'(unit 1) (value "{component.value}") '
                f'(footprint "{component.footprint}"))\n'
            )
            f.write("    )\n")
            f.write("  )\n")

        f.write(")")


def teardown_test_environment(context):
    """Clean up test environment."""
    if hasattr(context, "original_cwd"):
        os.chdir(context.original_cwd)

    if hasattr(context, "temp_dir") and context.temp_dir.exists():
        shutil.rmtree(context.temp_dir)
