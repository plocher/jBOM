"""Step definitions for POS (Position/Placement) file generation testing."""

import csv
import io
import tempfile
from pathlib import Path

from behave import given, when, then


@given("a clean test environment")
def step_clean_test_environment(context):
    """Set up a clean test environment for POS testing."""
    # Create a temporary directory for test files
    context.test_temp_dir = Path(tempfile.mkdtemp(prefix="jbom_pos_test_"))
    context.test_pcb_file = None
    context.test_components = []
    context.generated_pos_file = None
    context.pos_output_content = None


@given('a KiCad project named "{project_name}"')
def step_create_kicad_project(context, project_name):
    """Create a basic KiCad project structure for testing."""
    context.project_name = project_name
    context.project_dir = context.test_temp_dir / project_name
    context.project_dir.mkdir(parents=True, exist_ok=True)

    # Create a basic PCB file path (will be populated in subsequent steps)
    context.test_pcb_file = context.project_dir / f"{project_name}.kicad_pcb"


@given("the PCB is populated with components:")
def step_populate_pcb_with_components(context):
    """Create a mock PCB file with components from the data table."""
    if not context.table:
        raise ValueError("Component data table is required")

    context.test_components = []
    for row in context.table:
        component = {
            "reference": row["Reference"],
            "value": row["Value"],
            "package": row["Package"],
            "rotation": float(row["Rotation"]),
            "x": float(row["X"]),
            "y": float(row["Y"]),
            "layer": row["Layer"],
            "footprint": row["Footprint"],
            "mount": row.get("Mount", "SMD"),
        }
        context.test_components.append(component)

    # Create a mock PCB file with the component data
    # This is just test setup - the actual plugin will read this file
    _create_mock_pcb_file(context)


def _create_mock_pcb_file(context, target_path: Path | None = None):
    """Create a mock KiCad PCB file with component data."""
    pcb_content = [
        "(kicad_pcb (version 20221018) (generator pcbnew)",
        "  (general",
        f'    (title "{context.project_name}")',
        "  )",
    ]

    # Add mock footprint entries for each component
    for comp in context.test_components:
        # Determine layer designation
        layer_prefix = "F" if comp["layer"].lower() == "top" else "B"

        attr = (
            "smd"
            if str(comp.get("mount", "SMD")).lower() in ("smd", "sm")
            else "through_hole"
        )
        footprint_entry = f"""  (footprint "{comp['footprint']}" (layer "{layer_prefix}.Cu")
    (at {comp['x']} {comp['y']} {comp['rotation']})
    (fp_text reference "{comp['reference']}" (at 0 0) (layer "{layer_prefix}.SilkS"))
    (fp_text value "{comp['value']}" (at 0 0) (layer "{layer_prefix}.Fab"))
    (property "Reference" "{comp['reference']}")
    (property "Value" "{comp['value']}")
    (property "Footprint" "{comp['footprint']}")
    (attr {attr})
  )"""
        pcb_content.append(footprint_entry)

    pcb_content.append(")")

    pcb_path = target_path or context.test_pcb_file
    with open(pcb_path, "w") as f:
        f.write("\n".join(pcb_content))


@when("I generate a POS file with no options")
def step_generate_pos_no_options(context):
    """Generate a POS file using default options."""
    from jbom.plugins.pos.services.pos_generator import create_pos_generator

    context.generated_pos_file = context.project_dir / f"{context.project_name}_pos.csv"

    # Call the actual POS plugin service
    pos_generator = create_pos_generator()
    pos_generator.generate_pos_file(
        pcb_file=context.test_pcb_file, output_file=context.generated_pos_file
    )


@when("I generate a POS file with output to stdout")
def step_generate_pos_to_stdout(context):
    """Generate POS data and capture stdout output."""
    from jbom.plugins.pos.services.pos_generator import create_pos_generator
    import io
    from contextlib import redirect_stdout

    # Call the actual POS plugin service with stdout output
    pos_generator = create_pos_generator()

    # Capture stdout output
    output_buffer = io.StringIO()
    with redirect_stdout(output_buffer):
        pos_generator.generate_pos_file(
            pcb_file=context.test_pcb_file,
            output_file=None,  # None indicates stdout output
        )

    context.pos_output_content = output_buffer.getvalue()


@when("I attempt to generate POS from nonexistent PCB")
def step_generate_pos_missing_pcb(context):
    """Attempt to generate POS from a nonexistent PCB file."""
    from jbom.plugins.pos.services.pos_generator import create_pos_generator

    context.test_pcb_file = context.test_temp_dir / "nonexistent.kicad_pcb"

    # Call the actual POS plugin service and expect it to handle the error
    try:
        pos_generator = create_pos_generator()
        pos_generator.generate_pos_file(
            pcb_file=context.test_pcb_file,
            output_file=context.project_dir / "output.csv",
        )
        context.error_occurred = False
    except Exception as e:
        context.error_occurred = True
        context.error_message = str(e)


@then("the POS file is created successfully")
def step_verify_pos_file_created(context):
    """Verify that the POS file was created."""
    assert context.generated_pos_file is not None, "No POS file path set"
    assert (
        context.generated_pos_file.exists()
    ), f"POS file not created: {context.generated_pos_file}"
    assert context.generated_pos_file.stat().st_size > 0, "POS file is empty"


@then("the POS contains {expected_count:d} components")
def step_verify_component_count(context, expected_count):
    """Verify the number of components in the generated POS file."""
    if context.generated_pos_file:
        with open(context.generated_pos_file, "r") as f:
            reader = csv.reader(f)
            rows = list(reader)
            # Subtract 1 for header row
            actual_count = len(rows) - 1
    elif context.pos_output_content:
        reader = csv.reader(io.StringIO(context.pos_output_content))
        rows = list(reader)
        actual_count = len(rows) - 1
    else:
        raise AssertionError("No POS data available to verify")

    assert (
        actual_count == expected_count
    ), f"Expected {expected_count} components, got {actual_count}"


@then("the POS has columns: {column_list}")
def step_verify_pos_columns(context, column_list):
    """Verify the POS file has the expected column headers."""
    expected_columns = [col.strip() for col in column_list.split(",")]

    if context.generated_pos_file:
        with open(context.generated_pos_file, "r") as f:
            reader = csv.reader(f)
            actual_columns = next(reader)
    elif context.pos_output_content:
        reader = csv.reader(io.StringIO(context.pos_output_content))
        actual_columns = next(reader)
    else:
        raise AssertionError("No POS data available to verify")

    assert (
        actual_columns == expected_columns
    ), f"Expected columns {expected_columns}, got {actual_columns}"


@when("I generate a POS file with output to console")
def step_generate_pos_to_console(context):
    """Generate POS data in human-readable console mode and capture output."""
    from jbom.plugins.pos.services.pos_generator import create_pos_generator
    from contextlib import redirect_stdout

    pos_generator = create_pos_generator()

    buf = io.StringIO()
    with redirect_stdout(buf):
        pos_generator.generate_pos_file(
            pcb_file=context.test_pcb_file,
            output_file="console",
        )
    context.console_output = buf.getvalue()


@then("the output contains CSV data")
def step_verify_csv_output(context):
    """Verify that the output contains valid CSV data."""
    assert context.pos_output_content is not None, "No output content captured"

    # Try to parse as CSV
    try:
        reader = csv.reader(io.StringIO(context.pos_output_content))
        rows = list(reader)
        assert len(rows) > 0, "No CSV rows found"
        # Should have at least a header row
        assert len(rows[0]) > 0, "Empty CSV header row"
    except Exception as e:
        raise AssertionError(f"Invalid CSV format: {e}")


@then('the output contains component "{component_ref}"')
def step_output_contains_component_csv(context, component_ref):
    assert context.pos_output_content is not None, "No CSV output captured"
    assert component_ref in context.pos_output_content


@then("the console output contains a placement table")
def step_console_contains_table(context):
    assert (
        hasattr(context, "console_output") and context.console_output
    ), "No console output captured"
    assert "Placement Table:" in context.console_output


@then('the console output mentions component "{component_ref}"')
def step_verify_component_in_output(context, component_ref):
    """Verify that a specific component appears in the output."""
    # Support both CSV stdout capture and console capture
    output = None
    if hasattr(context, "console_output") and context.console_output:
        output = context.console_output
    elif hasattr(context, "pos_output_content") and context.pos_output_content:
        output = context.pos_output_content
    assert output is not None, "No output content captured"
    assert (
        component_ref in output
    ), f"Component {component_ref} not found in console output"


@then("an error is reported")
def step_verify_error_reported(context):
    """Verify that an error was reported."""
    assert (
        hasattr(context, "error_occurred") and context.error_occurred
    ), "No error was reported"


@when("I run the POS tool with defaults")
def step_run_pos_with_defaults(context):
    """Simulate CLI default behavior: discover PCB and write default-named file, not stdout."""
    from jbom.plugins.pos.services.pos_generator import create_pos_generator
    from contextlib import redirect_stdout

    # Default output filename: <project>.pos.csv (per requirement)
    default_path = context.project_dir / f"{context.project_name}.pos.csv"

    # Run while capturing stdout to ensure nothing is printed
    buf = io.StringIO()
    with redirect_stdout(buf):
        pos_generator = create_pos_generator()
        pos_generator.generate_pos_file(
            pcb_file=context.test_pcb_file, output_file=default_path
        )
    context.default_output_path = default_path
    context.captured_stdout = buf.getvalue()


@then("a default POS file is created in the project directory")
def step_default_file_created(context):
    assert (
        context.default_output_path.exists()
    ), f"Default POS file not created: {context.default_output_path}"


@then("no CSV was printed to stdout")
def step_no_csv_on_stdout(context):
    assert (
        context.captured_stdout == ""
    ), "CSV should not be printed to stdout when using defaults"


@then("the error mentions the missing file")
def step_verify_error_mentions_file(context):
    """Verify that the error message mentions the missing file."""
    assert hasattr(context, "error_message"), "No error message captured"
    assert (
        str(context.test_pcb_file) in context.error_message
    ), f"Error message should mention missing file: {context.error_message}"
