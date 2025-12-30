"""
Common step definitions for jBOM functional tests.

These steps provide reusable building blocks that can be used across
different feature areas (BOM, POS, inventory, etc.).
"""

import csv
import subprocess
from behave import given, when, then
from jbom.api import generate_bom, generate_pos


# =============================================================================
# Test Data Setup Steps
# =============================================================================


@given('a KiCad project named "{project_name}"')
def step_given_kicad_project(context, project_name):
    """Set up a KiCad project for testing."""
    # Copy example project to scenario temp directory
    source_project = context.examples_dir / project_name
    if not source_project.exists():
        # Create a minimal test project if example doesn't exist
        context.project_dir = context.scenario_temp_dir / project_name
        context.project_dir.mkdir()
        context.project_name = project_name
        # Project setup will be completed by subsequent steps
    else:
        context.project_dir = context.scenario_temp_dir / project_name
        # Copy the example project
        import shutil

        shutil.copytree(source_project, context.project_dir)
        context.project_name = project_name


@given("an inventory file with components")
def step_given_inventory_file(context):
    """Create an inventory file with test components."""
    # Use table data if provided
    if context.table:
        inventory_data = []
        headers = context.table.headings
        for row in context.table:
            inventory_data.append(dict(zip(headers, row.cells)))
    else:
        # Create minimal test inventory
        inventory_data = [
            {
                "IPN": "R001",
                "Category": "RES",
                "Value": "10K",
                "Package": "0603",
                "Distributor": "JLC",
                "DPN": "C25804",
                "Priority": "1",
            },
            {
                "IPN": "C001",
                "Category": "CAP",
                "Value": "100nF",
                "Package": "0603",
                "Distributor": "JLC",
                "DPN": "C14663",
                "Priority": "1",
            },
        ]

    # Write inventory CSV
    context.inventory_file = context.scenario_temp_dir / "test_inventory.csv"
    with open(context.inventory_file, "w", newline="") as f:
        if inventory_data:
            writer = csv.DictWriter(f, fieldnames=inventory_data[0].keys())
            writer.writeheader()
            writer.writerows(inventory_data)


@given("multiple inventory sources")
def step_given_multiple_inventory_sources(context):
    """Create multiple inventory files for federated testing."""
    # Create local inventory
    local_inventory = [
        {
            "IPN": "LOCAL001",
            "Category": "RES",
            "Value": "1K",
            "Package": "0603",
            "Distributor": "Local",
            "DPN": "",
            "Priority": "1",
        },
        {
            "IPN": "LOCAL002",
            "Category": "CAP",
            "Value": "10uF",
            "Package": "0805",
            "Distributor": "Local",
            "DPN": "",
            "Priority": "1",
        },
    ]

    # Create supplier inventory
    supplier_inventory = [
        {
            "IPN": "SUP001",
            "Category": "RES",
            "Value": "10K",
            "Package": "0603",
            "Distributor": "JLC",
            "DPN": "C25804",
            "Priority": "2",
        },
        {
            "IPN": "SUP002",
            "Category": "CAP",
            "Value": "100nF",
            "Package": "0603",
            "Distributor": "JLC",
            "DPN": "C14663",
            "Priority": "2",
        },
    ]

    # Write files
    context.local_inventory = context.scenario_temp_dir / "local_inventory.csv"
    context.supplier_inventory = context.scenario_temp_dir / "supplier_inventory.csv"

    for inventory_data, filepath in [
        (local_inventory, context.local_inventory),
        (supplier_inventory, context.supplier_inventory),
    ]:
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=inventory_data[0].keys())
            writer.writeheader()
            writer.writerows(inventory_data)

    context.inventory_files = [context.local_inventory, context.supplier_inventory]


# =============================================================================
# CLI Execution Steps
# =============================================================================


@when('I run jbom command "{command}"')
def step_when_run_jbom_command(context, command):
    """Execute a jBOM CLI command."""
    # Build full command
    full_command = f"python -m jbom {command}"

    try:
        result = subprocess.run(
            full_command,
            shell=True,
            cwd=context.project_root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        context.last_command_output = result.stdout
        context.last_command_error = result.stderr
        context.last_command_exit_code = result.returncode
    except subprocess.TimeoutExpired:
        context.last_command_error = "Command timed out"
        context.last_command_exit_code = -1


@when("I generate BOM using CLI")
def step_when_generate_bom_cli(context):
    """Generate BOM using CLI command."""
    command = f"bom {context.project_dir} -i {context.inventory_file} -o bom_output.csv"
    context.execute_steps(f'When I run jbom command "{command}"')
    context.bom_output_file = context.scenario_temp_dir / "bom_output.csv"


# =============================================================================
# API Execution Steps
# =============================================================================


@when("I generate BOM using Python API")
def step_when_generate_bom_api(context):
    """Generate BOM using Python API."""
    try:
        context.api_result = generate_bom(
            input=context.project_dir,
            inventory=context.inventory_file,
            output=context.scenario_temp_dir / "api_bom_output.csv",
        )
        context.last_command_exit_code = 0
        context.bom_output_file = context.scenario_temp_dir / "api_bom_output.csv"
    except Exception as e:
        context.last_command_error = str(e)
        context.last_command_exit_code = 1


@when("I generate POS using Python API")
def step_when_generate_pos_api(context):
    """Generate POS using Python API."""
    try:
        context.api_result = generate_pos(
            input=context.project_dir,
            output=context.scenario_temp_dir / "api_pos_output.csv",
        )
        context.last_command_exit_code = 0
        context.pos_output_file = context.scenario_temp_dir / "api_pos_output.csv"
    except Exception as e:
        context.last_command_error = str(e)
        context.last_command_exit_code = 1


# =============================================================================
# Result Validation Steps
# =============================================================================


@then("the command succeeds")
def step_then_command_succeeds(context):
    """Verify that the last command succeeded."""
    assert (
        context.last_command_exit_code == 0
    ), f"Command failed with exit code {context.last_command_exit_code}. Error: {context.last_command_error}"


@then("the command fails")
def step_then_command_fails(context):
    """Verify that the last command failed."""
    assert (
        context.last_command_exit_code != 0
    ), "Expected command to fail, but it succeeded"


@then("a BOM file is generated")
def step_then_bom_file_generated(context):
    """Verify that a BOM file was created."""
    assert hasattr(context, "bom_output_file"), "No BOM output file specified"
    assert (
        context.bom_output_file.exists()
    ), f"BOM file not found: {context.bom_output_file}"


@then("the BOM contains {count:d} entries")
def step_then_bom_contains_entries(context, count):
    """Verify BOM entry count."""
    assert hasattr(context, "bom_output_file"), "No BOM output file specified"

    with open(context.bom_output_file, "r") as f:
        reader = csv.reader(f)
        next(reader)  # Skip headers
        rows = list(reader)

    assert len(rows) == count, f"Expected {count} BOM entries, found {len(rows)}"


@then("the BOM includes columns")
def step_then_bom_includes_columns(context):
    """Verify BOM contains expected columns."""
    assert hasattr(context, "bom_output_file"), "No BOM output file specified"

    with open(context.bom_output_file, "r") as f:
        reader = csv.reader(f)
        headers = next(reader)

    expected_columns = [row["column"] for row in context.table]
    for column in expected_columns:
        assert (
            column in headers
        ), f"Expected column '{column}' not found in BOM headers: {headers}"


@then('the output contains "{text}"')
def step_then_output_contains_text(context, text):
    """Verify command output contains specific text."""
    output = context.last_command_output or ""
    error = context.last_command_error or ""
    full_output = output + error

    assert (
        text in full_output
    ), f"Expected text '{text}' not found in output: {full_output}"


# =============================================================================
# File Operation Steps
# =============================================================================


@then('file "{filename}" is created')
def step_then_file_created(context, filename):
    """Verify a file was created."""
    file_path = context.scenario_temp_dir / filename
    assert file_path.exists(), f"Expected file not found: {file_path}"


@then('file "{filename}" contains {count:d} rows')
def step_then_file_contains_rows(context, filename, count):
    """Verify CSV file row count."""
    file_path = context.scenario_temp_dir / filename
    assert file_path.exists(), f"File not found: {file_path}"

    with open(file_path, "r") as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        rows = list(reader)

    assert len(rows) == count, f"Expected {count} rows, found {len(rows)} in {filename}"
