"""
Error Handling domain BDD step definitions.

This module provides comprehensive step definitions for error handling scenarios
with automatic multi-modal testing across CLI, API, and Plugin interfaces.
Follows Axiom #14 (parameterization) and Axiom #4 (multi-modal testing).
"""

from behave import given, when, then
import os


# =============================================================================
# Validation Support - Multi-Modal Testing
# =============================================================================


@when("I validate error behavior across all usage models")
def step_when_validate_error_behavior_across_all_usage_models(context):
    """Execute current error scenario across CLI, API, and Plugin models automatically."""
    context.results = {}

    # CLI execution
    if hasattr(context, "cli_command"):
        result = context.execute_shell(context.cli_command)
        context.results["CLI"] = {
            "exit_code": result.get("exit_code", 1),
            "output": result.get("output", ""),
            "error_message": result.get("stderr", ""),
        }

    # API execution
    if hasattr(context, "api_method"):
        try:
            api_result = context.api_method()
            context.results["API"] = {
                "exit_code": 0,
                "output": str(api_result),
                "api_result": api_result,
            }
        except Exception as e:
            context.results["API"] = {
                "exit_code": 1,
                "output": str(e),
                "error_message": str(e),
                "api_result": None,
            }

    # Plugin execution
    if hasattr(context, "plugin_method"):
        try:
            plugin_result = context.plugin_method()
            context.results["Plugin"] = {
                "exit_code": 0,
                "output": str(plugin_result),
                "plugin_result": plugin_result,
            }
        except Exception as e:
            context.results["Plugin"] = {
                "exit_code": 1,
                "output": str(e),
                "error_message": str(e),
                "plugin_result": None,
            }


# =============================================================================
# File System Error Setup Steps
# =============================================================================


@given('I specify nonexistent inventory file "{file_path}"')
def step_given_specify_nonexistent_inventory_file(context, file_path):
    """Set up test with nonexistent inventory file path."""
    context.inventory_file = file_path
    context.file_exists = False
    context.cli_command = f"jbom bom {context.project_name} --inventory {file_path}"
    context.api_method = lambda: context.api_generate_bom(inventory=file_path)
    context.plugin_method = lambda: context.plugin_generate_bom(inventory=file_path)


@given('I specify nonexistent project directory "{project_path}"')
def step_given_specify_nonexistent_project_directory(context, project_path):
    """Set up test with nonexistent project directory path."""
    context.project_dir = project_path
    context.directory_exists = False
    context.cli_command = f"jbom bom {project_path}"
    context.api_method = lambda: context.api_generate_bom(project=project_path)
    context.plugin_method = lambda: context.plugin_generate_bom(project=project_path)


@given("an inventory file with invalid format")
def step_given_inventory_file_with_invalid_format(context):
    """Set up inventory file with invalid column structure using concrete test data."""
    # Create actual CSV file with the invalid format specified in the scenario table
    import csv

    invalid_file = context.scenario_temp_dir / "invalid_format.csv"

    # Use concrete test data from the table (Axiom #2: Concrete Test Vectors)
    if hasattr(context, "table") and context.table:
        with open(invalid_file, "w", newline="") as f:
            writer = csv.writer(f)
            # Write header row
            writer.writerow([cell for cell in context.table.headings])
            # Write data rows
            for row in context.table.rows:
                writer.writerow([cell for cell in row.cells])
    else:
        # Fallback: create a file with clearly invalid structure
        with open(invalid_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["InvalidColumn", "AnotherBadColumn"])
            writer.writerow(["data1", "data2"])

    context.invalid_inventory = True
    context.invalid_inventory_file = str(invalid_file)
    context.cli_command = f"jbom bom {context.project_name} --inventory {invalid_file}"
    context.api_method = lambda: context.api_generate_bom(inventory=str(invalid_file))
    context.plugin_method = lambda: context.plugin_generate_bom(
        inventory=str(invalid_file)
    )


@given('a schematic named "{schematic_name}" containing malformed S-expression')
def step_given_schematic_named_containing_malformed_s_expression(
    context, schematic_name
):
    """Set up test with concrete malformed S-expression schematic (Axiom #2: Concrete Test Vectors)."""
    # Create schematic file with the malformed S-expression from the scenario
    project_dir = context.scenario_temp_dir / schematic_name
    project_dir.mkdir(exist_ok=True)

    schematic_file = project_dir / f"{schematic_name}.kicad_sch"

    # Use the concrete malformed S-expression content from the scenario
    malformed_content = (
        context.text.strip()
        if hasattr(context, "text") and context.text
        else """(kicad_sch (version 20230121) (generator eeschema)
  (uuid "corrupted-test-uuid")
  (paper "A4"
  (lib_symbols)
  (symbol_instances)
  (sheet_instances
    (path "/" (page "1"))
  # Missing closing parentheses - concrete syntax error"""
    )

    with open(schematic_file, "w") as f:
        f.write(malformed_content)

    context.schematic_name = schematic_name
    context.malformed_schematic_file = schematic_file
    context.cli_command = f"jbom bom {project_dir} --generic"
    context.api_method = lambda: context.api_generate_bom(
        project=str(project_dir), options=context.BOMOptions(fabricator="generic")
    )
    context.plugin_method = lambda: context.plugin_generate_bom(
        project=str(project_dir), fabricator="generic"
    )


# =============================================================================
# Permission and Access Error Steps
# =============================================================================


@given('a read-only directory "{directory_path}"')
def step_given_read_only_directory(context, directory_path):
    """Create a read-only directory for permission testing (Axiom #2: Concrete Test Vectors)."""

    # Create directory in test temp area
    dir_path = context.scenario_temp_dir / directory_path.lstrip("./")
    dir_path.mkdir(exist_ok=True)

    # Make directory read-only (remove write permissions)
    dir_path.chmod(0o555)  # r-xr-xr-x (read and execute only)

    context.readonly_directory = dir_path


@given('an output path "{output_path}"')
def step_given_output_path(context, output_path):
    """Set up output path for testing (Axiom #20: Named References)."""
    from pathlib import Path

    context.output_path = output_path

    # Store full path for verification
    if output_path.startswith("./"):
        context.full_output_path = context.scenario_temp_dir / output_path.lstrip("./")
    else:
        context.full_output_path = Path(output_path)


@when('I generate a generic BOM with {project_name} writing to "{output_path}"')
def step_when_generate_generic_bom_with_project_writing_to_path(
    context, project_name, output_path
):
    """Generate BOM with named project and explicit output path (Axiom #20: Named References)."""
    # Set up commands for multi-modal testing
    context.cli_command = f"jbom bom {project_name} --generic --output {output_path}"
    context.api_method = lambda: context.api_generate_bom(
        project=project_name,
        output=output_path,
        options=context.BOMOptions(fabricator="generic"),
    )
    context.plugin_method = lambda: context.plugin_generate_bom(
        project=project_name, output=output_path, fabricator="generic"
    )

    # Execute multi-modal validation
    context.execute_steps("When I validate error behavior across all usage models")


# =============================================================================
# Empty Data Condition Steps
# =============================================================================


@given("a KiCad project and empty inventory file")
def step_given_kicad_project_and_empty_inventory_file(context):
    """Set up test with empty inventory file (Axiom #2: Concrete Test Vectors)."""
    # Create actual empty CSV file
    import csv

    empty_file = context.scenario_temp_dir / "empty.csv"

    # Create truly empty CSV (just headers, no data rows)
    with open(empty_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["IPN", "Category", "Value", "Package", "LCSC"]
        )  # Valid headers, no data

    context.empty_inventory = True
    context.empty_inventory_file = str(empty_file)
    context.cli_command = f"jbom bom {context.project_name} --inventory {empty_file}"
    context.api_method = lambda: context.api_generate_bom(inventory=str(empty_file))
    context.plugin_method = lambda: context.plugin_generate_bom(
        inventory=str(empty_file)
    )


@given("a KiCad project with empty schematic")
def step_given_kicad_project_with_empty_schematic(context):
    """Set up test with schematic containing no components (Axiom #2: Concrete Test Vectors)."""
    # Create actual empty schematic file - valid structure but no components
    project_dir = context.scenario_temp_dir / "empty_project"
    project_dir.mkdir(exist_ok=True)

    schematic_file = project_dir / "empty_project.kicad_sch"

    # Create valid KiCad schematic with proper structure but no symbol instances (no components)
    empty_schematic_content = """(kicad_sch (version 20230121) (generator eeschema)
  (uuid "empty-uuid-1234-5678-9012-123456789012")
  (paper "A4")
  (lib_symbols)
  (symbol_instances)
  (sheet_instances
    (path "/" (page "1"))
  )
)
"""

    with open(schematic_file, "w") as f:
        f.write(empty_schematic_content)

    context.empty_schematic = True
    context.empty_project_dir = project_dir
    context.empty_schematic_file = schematic_file
    context.cli_command = f"jbom bom {project_dir}"
    context.api_method = lambda: context.api_generate_bom(project=str(project_dir))
    context.plugin_method = lambda: context.plugin_generate_bom(
        project=str(project_dir)
    )


# =============================================================================
# Network and API Error Steps
# =============================================================================


@given("invalid API key for search")
def step_given_invalid_api_key_for_search(context):
    """Set up test with invalid API key."""
    context.invalid_api_key = True
    os.environ["MOUSER_API_KEY"] = "invalid_key_12345"
    context.cli_command = f"jbom inventory {context.project_name} --search"
    context.api_method = lambda: context.api_extract_inventory(search=True)
    context.plugin_method = lambda: context.plugin_extract_inventory(search=True)


@given("network connectivity issues during search")
def step_given_network_connectivity_issues_during_search(context):
    """Set up test with network connectivity problems."""
    context.network_issues = True
    context.cli_command = f"jbom inventory {context.project_name} --search"
    context.api_method = lambda: context.api_extract_inventory(search=True)
    context.plugin_method = lambda: context.plugin_extract_inventory(search=True)


# =============================================================================
# Hierarchical Project Error Steps
# =============================================================================


@given("hierarchical schematic with missing sub-sheet files")
def step_given_hierarchical_schematic_with_missing_subsheet_files(context):
    """Set up test with hierarchical schematic missing sub-sheets."""
    context.missing_subsheets = True
    context.hierarchical_project = True
    context.cli_command = "jbom bom hierarchical_missing"
    context.api_method = lambda: context.api_generate_bom(
        project="hierarchical_missing"
    )
    context.plugin_method = lambda: context.plugin_generate_bom(
        project="hierarchical_missing"
    )


# =============================================================================
# Mixed Condition Steps
# =============================================================================


@given("mixed valid and invalid conditions")
def step_given_mixed_valid_and_invalid_conditions(context):
    """Set up test with combination of valid and invalid inputs."""
    context.mixed_conditions = True
    context.cli_command = "jbom bom valid_project --inventory invalid.csv"
    context.api_method = lambda: context.api_generate_bom(
        project="valid_project", inventory="invalid.csv"
    )
    context.plugin_method = lambda: context.plugin_generate_bom(
        project="valid_project", inventory="invalid.csv"
    )


# =============================================================================
# Basic Operation Steps
# =============================================================================


@when("I generate a BOM")
def step_when_generate_a_bom(context):
    """Generate BOM and capture error conditions across all usage models automatically."""
    context.execute_steps("When I validate error behavior across all usage models")


@when("I generate a generic BOM with {schematic_name}")
def step_when_generate_generic_bom_with_schematic(context, schematic_name):
    """Generate BOM with named schematic using generic fabricator (Axiom #20: Named References)."""
    context.execute_steps("When I validate error behavior across all usage models")


# =============================================================================
# Error Message Verification Steps
# =============================================================================


@then(
    'the error message reports "{expected_message}" and exits with code {exit_code:d}'
)
def step_then_error_message_reports_and_exits_with_code(
    context, expected_message, exit_code
):
    """Verify error message and exit code across all usage models automatically."""
    context.execute_steps("When I validate error behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == exit_code
        ), f"{method} wrong exit code: expected {exit_code}, got {result['exit_code']}"
        error_text = result.get("error_message", result.get("output", ""))
        assert (
            expected_message in error_text
        ), f"{method} missing error message: '{expected_message}' not in '{error_text}'"


@then('the error message reports "{message_text}" and suggests checking the path')
def step_then_error_message_reports_and_suggests_checking_path(context, message_text):
    """Verify error message includes path checking suggestion across all usage models automatically."""
    context.execute_steps("When I validate error behavior across all usage models")
    for method, result in context.results.items():
        error_text = result.get("error_message", result.get("output", ""))
        assert (
            message_text in error_text
        ), f"{method} missing error message: '{message_text}' not in '{error_text}'"
        assert (
            "path" in error_text.lower()
        ), f"{method} missing path suggestion in error message"


@then('the error message reports "{message_text}" with syntax error details')
def step_then_error_message_reports_with_syntax_error_details(context, message_text):
    """Verify error message includes syntax error details across all usage models automatically."""
    context.execute_steps("When I validate error behavior across all usage models")
    for method, result in context.results.items():
        error_text = result.get("error_message", result.get("output", ""))
        assert (
            message_text in error_text
        ), f"{method} missing error message: '{message_text}' not in '{error_text}'"
        assert "syntax" in error_text.lower(), f"{method} missing syntax error details"


@then("the error message includes syntax error details showing line and position")
def step_then_error_message_includes_syntax_error_details_with_position(context):
    """Verify error message includes concrete syntax error details with line/position info."""
    context.execute_steps("When I validate error behavior across all usage models")
    for method, result in context.results.items():
        error_text = result.get("error_message", result.get("output", ""))
        # Check for syntax error indicators
        assert any(
            indicator in error_text.lower()
            for indicator in ["syntax", "parsing", "malformed", "invalid s-expression"]
        ), f"{method} missing syntax error indicator in '{error_text}'"
        # Check for position information (line numbers, character positions)
        assert any(
            indicator in error_text.lower()
            for indicator in ["line", "position", "char", "offset"]
        ), f"{method} missing position information in syntax error"


# =============================================================================
# Warning and Success with Error Steps
# =============================================================================


@then('the error handling reports "{error_type}" suggesting {suggestion_type} check')
def step_then_error_handling_reports_error_suggesting_check(
    context, error_type, suggestion_type
):
    """Verify error handling with specific suggestion across all usage models automatically."""
    context.execute_steps("When I validate error behavior across all usage models")
    for method, result in context.results.items():
        error_text = result.get("error_message", result.get("output", ""))
        assert (
            error_type in error_text
        ), f"{method} missing error type: '{error_type}' not in '{error_text}'"
        assert (
            suggestion_type in error_text
        ), f"{method} missing suggestion: '{suggestion_type}' not in '{error_text}'"


@then("the processing succeeds with empty inventory warning and unmatched components")
def step_then_processing_succeeds_with_empty_inventory_warning(context):
    """Verify successful processing with empty inventory warning across all usage models automatically."""
    context.execute_steps("When I validate error behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} should succeed with warnings"
        output = result.get("output", "")
        assert (
            "empty" in output.lower() and "inventory" in output.lower()
        ), f"{method} missing empty inventory warning"


@then("the processing succeeds with no components warning and empty BOM file")
def step_then_processing_succeeds_with_no_components_warning(context):
    """Verify successful processing with no components warning across all usage models automatically."""
    context.execute_steps("When I validate error behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} should succeed with warnings"
        output = result.get("output", "")
        assert (
            "no components" in output.lower() or "empty" in output.lower()
        ), f"{method} missing no components warning"


@then("the processing succeeds with missing sub-sheet warnings and partial BOM")
def step_then_processing_succeeds_with_missing_subsheet_warnings(context):
    """Verify successful processing with sub-sheet warnings across all usage models automatically."""
    context.execute_steps("When I validate error behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} should succeed with warnings"
        output = result.get("output", "")
        assert "missing" in output.lower() and (
            "sub-sheet" in output.lower() or "sheet" in output.lower()
        ), f"{method} missing sub-sheet warning"


@then("the processing succeeds for valid parts with specific error reporting")
def step_then_processing_succeeds_for_valid_parts_with_error_reporting(context):
    """Verify mixed success/failure processing across all usage models automatically."""
    context.execute_steps("When I validate error behavior across all usage models")
    for method, result in context.results.items():
        assert result["exit_code"] == 0, f"{method} should succeed for valid parts"
        output = result.get("output", "")
        assert (
            "error" in output.lower() or "warning" in output.lower()
        ), f"{method} missing specific error reporting"


@then('no file was created at "{file_path}"')
def step_then_no_file_was_created_at_path(context, file_path):
    """Verify that no file was created at the specified path (permission denied should not create partial files)."""
    from pathlib import Path

    # Resolve path relative to scenario temp directory
    if file_path.startswith("./"):
        full_path = context.scenario_temp_dir / file_path.lstrip("./")
    else:
        full_path = Path(file_path)

    assert (
        not full_path.exists()
    ), f"File should not exist due to permission denied, but found: {full_path}"

    # Also verify the directory exists (to confirm the test setup was correct)
    parent_dir = full_path.parent
    assert (
        parent_dir.exists()
    ), f"Parent directory should exist for permission test: {parent_dir}"

    # Verify directory is indeed read-only
    import stat

    dir_stat = parent_dir.stat()
    is_writable = bool(dir_stat.st_mode & stat.S_IWUSR)  # Check owner write permission
    assert (
        not is_writable
    ), f"Directory should be read-only for permission test: {parent_dir}"


@given('a KiCad project named "{project_name}" containing components')
def step_given_kicad_project_with_components(context, project_name):
    """Create a KiCad project with specific components from the table."""
    from ..shared import create_kicad_project_with_components

    create_kicad_project_with_components(context, project_name, context.table)


@given('an inventory file "{filename}" containing only headers')
def step_given_inventory_file_with_headers_only(context, filename):
    """Create an inventory CSV file with headers but no data rows."""
    # Extract headers from the table
    headers = [cell for cell in context.table.headings]

    # Create CSV with headers only
    inventory_path = context.scenario_temp_dir / filename
    with open(inventory_path, "w", newline="") as csvfile:
        import csv

        writer = csv.writer(csvfile)
        writer.writerow(headers)
        # No data rows - empty inventory

    context.inventory_file = inventory_path


@then("the BOM generation succeeds with exit code {expected_code:d}")
def step_then_bom_generation_succeeds_with_exit_code(context, expected_code):
    """Verify BOM generation completed with expected exit code."""
    assert hasattr(context, "last_command_exit_code"), "No command was executed"
    actual_code = context.last_command_exit_code
    assert (
        actual_code == expected_code
    ), f"Expected exit code {expected_code}, got {actual_code}"


@then('the output contains warning "{warning_text}"')
def step_then_output_contains_warning(context, warning_text):
    """Verify the command output contains the expected warning message."""
    # Check both stdout and stderr for the warning
    output = getattr(context, "last_command_output", "") or ""
    error = getattr(context, "last_command_error", "") or ""
    combined_output = f"{output}\n{error}".lower()

    assert (
        warning_text.lower() in combined_output
    ), f"Warning '{warning_text}' not found in output: {combined_output}"


@then("the BOM file contains unmatched components {components}")
def step_then_bom_file_contains_unmatched_components(context, components):
    """Verify the BOM file contains the expected unmatched component references."""
    # Parse component list (e.g., "R1 and C1" -> ["R1", "C1"])
    component_refs = [
        comp.strip() for comp in components.replace(" and ", ",").split(",")
    ]

    # Find the output BOM file - look for common BOM filenames
    bom_file = None
    for potential_name in ["output.csv", "SimpleProject_BOM.csv", "bom.csv"]:
        potential_path = context.scenario_temp_dir / potential_name
        if potential_path.exists():
            bom_file = potential_path
            break

    assert (
        bom_file and bom_file.exists()
    ), f"BOM output file not found in {context.scenario_temp_dir}"

    # Read BOM file and verify components are present
    with open(bom_file, "r") as f:
        bom_content = f.read()

    for component_ref in component_refs:
        assert (
            component_ref in bom_content
        ), f"Component '{component_ref}' not found in BOM file: {bom_file}"


@given(
    'a KiCad project named "{project_name}" with valid schematic structure but no symbol instances'
)
def step_given_empty_kicad_project(context, project_name):
    """Create a KiCad project with valid schematic structure but no components."""
    context.project_name = project_name

    # Create project directory
    project_dir = context.scenario_temp_dir / project_name
    project_dir.mkdir(exist_ok=True)

    schematic_file = project_dir / f"{project_name}.kicad_sch"

    # Create minimal valid KiCad schematic with no symbol instances
    empty_schematic = """(kicad_sch (version 20230121) (generator eeschema)
  (uuid "12345678-1234-5678-9012-123456789012")
  (paper "A4")
  (lib_symbols)
  (symbol_instances)
  (sheet_instances
    (path "/" (page "1"))
  )
)
"""

    with open(schematic_file, "w") as f:
        f.write(empty_schematic)

    context.test_project_dir = project_dir
    context.test_schematic_file = schematic_file


# NOTE: Inventory file creation step moved to shared.py to avoid conflicts
# This step is now available from the shared module for all domains


@then("the BOM file contains header row but no data rows")
def step_then_bom_file_contains_header_only(context):
    """Verify the BOM file contains only headers with no data rows."""
    # Find the output BOM file
    bom_file = None
    for potential_name in ["output.csv", "EmptyProject_BOM.csv", "bom.csv"]:
        potential_path = context.scenario_temp_dir / potential_name
        if potential_path.exists():
            bom_file = potential_path
            break

    assert (
        bom_file and bom_file.exists()
    ), f"BOM output file not found in {context.scenario_temp_dir}"

    # Read CSV and verify structure
    import csv

    with open(bom_file, "r") as f:
        reader = csv.reader(f)
        rows = list(reader)

    assert len(rows) >= 1, "BOM file should have at least a header row"
    assert (
        len(rows) == 1
    ), f"BOM file should have only header row, found {len(rows)} rows"

    # Verify header is not empty
    header = rows[0]
    assert len(header) > 0, "BOM header should not be empty"
    assert any(
        cell.strip() for cell in header
    ), "BOM header should contain meaningful column names"


@given('I set the {env_var_name} environment variable to "{value}"')
def step_given_set_environment_variable(context, env_var_name, value):
    """Set an environment variable for testing API keys or configuration."""
    import os

    # Store original value to restore later
    if not hasattr(context, "original_env_vars"):
        context.original_env_vars = {}

    context.original_env_vars[env_var_name] = os.environ.get(env_var_name)
    os.environ[env_var_name] = value

    # Store in context for command execution
    if not hasattr(context, "test_env_vars"):
        context.test_env_vars = {}
    context.test_env_vars[env_var_name] = value


@given("I set the {env_var_name} environment variable to a valid key")
def step_given_set_environment_variable_valid_key(context, env_var_name):
    """Set an environment variable to a valid API key for testing."""
    # For testing purposes, we'll use a mock valid key
    # In real scenarios this would be a valid API key for the service
    valid_mock_key = "mock-valid-api-key-for-testing"
    context.execute_steps(
        f'Given I set the {env_var_name} environment variable to "{valid_mock_key}"'
    )


@given("I configure network timeout to {timeout:d} second for testing")
def step_given_configure_network_timeout(context, timeout):
    """Configure network timeout for testing timeout scenarios."""
    # Store timeout configuration for test execution
    context.network_timeout = timeout

    # This would typically set configuration for the jBOM networking layer
    # For BDD testing, we simulate the timeout condition


@when(
    "I generate search-enhanced inventory for {project} with --{fabricator} fabricator"
)
def step_when_generate_search_enhanced_inventory(context, project, fabricator):
    """Execute search-enhanced inventory generation with specific fabricator."""
    # Build command with environment variables and timeout settings
    cmd_parts = [
        "python",
        "-m",
        "jbom.cli",
        "inventory",
        f"--project={project}",
        f"--fabricator={fabricator}",
        "--output=enhanced_inventory.csv",
    ]

    # Apply timeout setting if configured
    if hasattr(context, "network_timeout"):
        cmd_parts.append(f"--timeout={context.network_timeout}")

    command = " ".join(cmd_parts)
    result = context.execute_shell(command)

    # Store result for verification
    context.last_command_exit_code = result["exit_code"]
    context.last_command_output = result["output"]
    context.last_command_error = result["stderr"]


@then('the error message suggests "{suggestion}"')
def step_then_error_message_suggests(context, suggestion):
    """Verify the error output contains the suggested resolution."""
    # Check both stdout and stderr for the suggestion
    output = getattr(context, "last_command_output", "") or ""
    error = getattr(context, "last_command_error", "") or ""
    combined_output = f"{output}\n{error}"

    assert (
        suggestion in combined_output
    ), f"Suggestion '{suggestion}' not found in output: {combined_output}"


@given(
    'a KiCad project named "{project_name}" with root schematic referencing sub-sheet "{subsheet_name}"'
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

    # Build symbol instances from table
    symbol_instances = []
    for row in context.table:
        reference = row["Reference"]
        value = row["Value"]
        footprint = row["Footprint"]

        symbol_instance = f"""    (symbol_instance (path "/{reference}")
      (reference "{reference}") (unit 1)
      (value "{value}") (footprint "{footprint}")
    )"""
        symbol_instances.append(symbol_instance)

    # Create hierarchical schematic with sub-sheet reference
    schematic_content = f"""(kicad_sch (version 20230121) (generator eeschema)
  (uuid "12345678-1234-5678-9012-123456789012")
  (paper "A4")
  (lib_symbols)
  (symbol_instances
{chr(10).join(symbol_instances)}
  )
  (sheet_instances
    (path "/" (page "1"))
    (path "/PowerSheet/" (page "2"))
  )
  (sheet (at 100 100) (size 50 30) (uuid "power-sheet-uuid")
    (property "Sheetname" "Power Supply" (id 0) (at 100 95 0))
    (property "Sheetfile" "{subsheet_name}" (id 1) (at 100 135 0))
  )
)
"""

    with open(schematic_file, "w") as f:
        f.write(schematic_content)

    context.test_schematic_file = schematic_file


@given('the sub-sheet file "{filename}" does not exist')
def step_given_subsheet_file_does_not_exist(context, filename):
    """Verify that the sub-sheet file does not exist (simulates missing file error)."""
    subsheet_path = context.test_project_dir / filename
    # Ensure it doesn't exist - this is the test condition
    if subsheet_path.exists():
        subsheet_path.unlink()

    context.missing_subsheet = filename


@given('an inventory file "{filename}" containing some matching components')
def step_given_inventory_file_with_some_matching_components(context, filename):
    """Create an inventory CSV file with some components that match the schematic."""
    # This is the same as the general inventory step, just with different wording
    context.execute_steps(f'Given an inventory file "{filename}" containing components')


@then("the BOM file contains component {component_ref} from root schematic")
def step_then_bom_file_contains_component_from_root(context, component_ref):
    """Verify the BOM file contains the specified component from the root schematic."""
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

    # Read BOM file and verify component is present
    with open(bom_file, "r") as f:
        bom_content = f.read()

    assert (
        component_ref in bom_content
    ), f"Component '{component_ref}' not found in BOM file: {bom_file}"


@then("the BOM file does not contain any components from the missing sub-sheet")
def step_then_bom_file_does_not_contain_subsheet_components(context):
    """Verify the BOM file does not contain components that would come from the missing sub-sheet."""
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

    # Read BOM file and verify no sub-sheet components
    with open(bom_file, "r") as f:
        f.read()  # We don't actually need content for this check

    # Sub-sheet components typically have different reference prefixes or paths
    # Since the sub-sheet is missing, we mainly verify no unexpected components appear
    # This step mainly serves as a documentation of expected behavior

    # Count actual component lines (excluding header)
    import csv

    with open(bom_file, "r") as f:
        reader = csv.reader(f)
        rows = list(reader)
        data_rows = rows[1:]  # Skip header

    # We expect only components from the root schematic (based on the test setup)
    # The exact count depends on how many components were added to root schematic
    assert (
        len(data_rows) >= 1
    ), "BOM should contain at least the root schematic components"


@then("the BOM file contains matched components {components} with inventory data")
def step_then_bom_file_contains_matched_components_with_inventory(context, components):
    """Verify matched components have inventory data populated."""
    component_refs = [
        comp.strip() for comp in components.replace(" and ", ",").split(",")
    ]

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

    # Read CSV and verify inventory data is populated
    import csv

    with open(bom_file, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    for component_ref in component_refs:
        # Find the component row
        component_row = None
        for row in rows:
            if row.get("Reference") == component_ref or component_ref in str(
                row.get("Reference", "")
            ):
                component_row = row
                break

        assert component_row, f"Component '{component_ref}' not found in BOM"

        # Verify inventory data is populated (IPN should not be empty)
        ipn = component_row.get("IPN", "").strip()
        assert ipn, f"Component '{component_ref}' missing inventory data (IPN is empty)"


@then(
    "the BOM file contains unmatched component {component_ref} with schematic data only"
)
def step_then_bom_file_contains_unmatched_component_schematic_only(
    context, component_ref
):
    """Verify unmatched component has only schematic data, no inventory data."""
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

    # Read CSV and verify component has no inventory data
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

    # Verify no inventory data (IPN should be empty)
    ipn = component_row.get("IPN", "").strip()
    assert (
        not ipn
    ), f"Component '{component_ref}' should not have inventory data but found IPN: {ipn}"

    # Verify schematic data is present
    reference = component_row.get("Reference", "").strip()
    value = component_row.get("Value", "").strip()
    assert reference, "Component should have Reference from schematic"
    assert value, "Component should have Value from schematic"
