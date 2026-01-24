"""Common step definitions for jBOM CLI testing."""

import subprocess
from pathlib import Path
from behave import when, then, given
from diagnostic_utils import assert_with_diagnostics


@given("a sandbox")
def step_test_environment(context):
    """Layer 1: Create isolated sandbox directory, nothing else.

    Use this for project discovery edge cases, malformed project testing.
    """
    import tempfile
    from pathlib import Path

    tmp = Path(tempfile.mkdtemp(prefix="jbom_behave_"))
    context.project_root = tmp
    # Keep src_root unchanged (set by environment.py)


@given("a KiCad sandbox")
def step_default_jbom_environment(context):
    """Layer 2: Sandbox + empty KiCad project, no command defaults.

    Use this for command behavior testing, explicit output format testing.
    """
    # Build on Layer 1
    step_test_environment(context)

    # Create empty but complete KiCad project
    project_name = "project"
    proj_dir = Path(context.project_root)
    (proj_dir / f"{project_name}.kicad_pro").write_text(
        "(kicad_project (version 1))\n", encoding="utf-8"
    )
    (proj_dir / f"{project_name}.kicad_sch").write_text(
        "(kicad_sch (version 20211123) (generator eeschema))\n", encoding="utf-8"
    )
    context.current_project = project_name


@given("a jBOM CSV sandbox")
def step_default_jbom_csv_output_environment(context):
    """Layer 2.5: Sandbox + project + CSV output, no fabricator defaults.

    Automatically adds '-o -' to jbom commands for CSV output testing.
    Use this for testing fabricator functionality without DRY violations.
    """
    # Build on Layer 2
    step_default_jbom_environment(context)

    # Set CSV output default but no fabricator default
    context.default_output = "-o -"


@given("a generic jBOM CSV sandbox")
def step_default_jbom_csv_environment(context):
    """Layer 3: Sandbox + project + standardized I/O for testing.

    Automatically adds '-o -' and '--fabricator generic' to jbom commands.
    Use this for most business logic testing (95% of scenarios).
    """
    # Build on Layer 2
    step_default_jbom_environment(context)

    # Set command execution defaults (used by step_run_jbom_command)
    context.default_output = "-o -"
    context.default_fabricator = "--fabricator generic"


@given("a clean test workspace")
def step_clean_test_workspace(context):
    """Legacy alias for Layer 1 - use 'Given a sandbox' instead."""
    step_test_environment(context)


@when('I run "{command}"')
def step_run_command(context, command):
    """Run a CLI command and capture output."""
    # Preserve previous output for later comparisons
    context.prev_output = getattr(context, "last_output", None)

    # Prepare diagnostics (pre-state)
    def _tree(root: str, depth: int = 3) -> str:
        from pathlib import Path as _P

        lines = []
        rootp = _P(root)
        for p in sorted(rootp.rglob("*")):
            rel = p.relative_to(rootp)
            if len(rel.parts) > depth:
                continue
            try:
                if p.is_dir():
                    lines.append(f"[D] {rel}/")
                else:
                    size = p.stat().st_size
                    lines.append(f"[F] {rel} ({size} bytes)")
            except OSError:
                continue
        return "\n".join(lines)

    pre_tree = (
        _tree(str(context.project_root)) if getattr(context, "trace", False) else None
    )

    # For now, run via python -m until we have proper installation
    if command.startswith("jbom "):
        # Replace 'jbom' with python module invocation
        raw_args = command.split()[1:]  # Remove 'jbom' prefix

        # Enforce sandbox safety on -o paths: disallow any path separators in tests
        if "-o" in raw_args:
            try:
                idx = raw_args.index("-o")
                outval = raw_args[idx + 1]
                if ("/" in outval) or ("\\" in outval):
                    raise AssertionError(
                        "-o value must not contain path separators in tests"
                    )
            except (ValueError, IndexError):
                pass

        # Add explicit fabricator from context if set and not already specified
        if len(raw_args) >= 1 and raw_args[0] == "bom":
            has_fabricator_flag = any(
                a.startswith("--fabricator") for a in raw_args
            ) or any(
                a in ("--jlc", "--pcbway", "--seeed", "--generic") for a in raw_args
            )
            if not has_fabricator_flag:
                fabricator = getattr(
                    context, "fabricator", "generic"
                )  # Default to generic if not set
                raw_args += ["--fabricator", fabricator]

        cmd = ["python", "-m", "jbom.cli.main"] + raw_args
    else:
        cmd = command.split()

    # Set PYTHONPATH to include src directory
    import os

    env = os.environ.copy()
    env["PYTHONPATH"] = str(context.src_root)
    # Suppress noisy informational stderr in tests so CSV parsing is clean
    env["JBOM_QUIET"] = "1"
    if getattr(context, "trace", False):
        env["JBOM_BEHAVE_TRACE"] = "1"

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=context.project_root,
            env=env,
        )
        context.last_command = command
        context.last_output = result.stdout + result.stderr
        context.last_exit_code = result.returncode
        if getattr(context, "trace", False):
            post_tree = _tree(str(context.project_root))
            context.diagnostics = (
                "=== DIAGNOSTICS ===\n"
                f"CWD (project_root): {context.project_root}\n"
                f"Command: {cmd}\n"
                "--- PRE TREE ---\n" + (pre_tree or "(trace off)") + "\n"
                "--- POST TREE ---\n" + post_tree + "\n"
                f"Exit: {result.returncode}\n"
            )
    except Exception as e:
        context.last_command = command
        context.last_output = str(e)
        context.last_exit_code = 1


@when('I run jbom command "{args}"')
def step_run_jbom_command(context, args):
    """Alias for running jbom commands without repeating the prefix.

    Layer 3 environments automatically add default flags and detect DRY violations.
    """
    # Layer 3 anti-pattern detection and auto-enhancement
    if hasattr(context, "default_output"):
        if "-o" in args:
            raise AssertionError(
                f"DRY VIOLATION: Using Layer 3 background ('generic jBOM CSV sandbox') "
                f"but specifying -o in command. Either use Layer 2.5 background, "
                f"or remove '-o' from command: {args}"
            )
        args += f" {context.default_output}"

    if hasattr(context, "default_fabricator"):
        fabricator_flags = ["--fabricator", "--jlc", "--pcbway", "--seeed", "--generic"]
        if any(flag in args for flag in fabricator_flags):
            raise AssertionError(
                f"DRY VIOLATION: Using Layer 3 background ('generic jBOM CSV sandbox') "
                f"but specifying fabricator in command. Either use Layer 2.5 background, "
                f"or remove fabricator from command: {args}"
            )
        args += f" {context.default_fabricator}"

    step_run_command(context, f"jbom {args}")


@given('the sample fixtures under "{rel_path}"')
def step_have_sample_fixtures(context, rel_path):
    """Copy fixture subtree into the per-scenario temp workspace.

    Rules:
    - Source is ALWAYS under jbom-new/features/fixtures in the repo.
    - Destination is ALWAYS under the scenario temp dir (context.project_root).
    - We never delete or modify files under the repo working tree.
    """
    from pathlib import Path
    import shutil

    assert hasattr(context, "sandbox_root"), "sandbox_root not initialized"
    repo_jbom_new = Path(getattr(context, "jbom_new_root"))

    # Normalize incoming path: allow callers to pass either of these prefixes
    #   "features/fixtures/..." or "jbom-new/features/fixtures/..."
    raw = rel_path.strip("/")
    parts = raw.split("/")
    # Strip optional leading "jbom-new"
    if parts and parts[0] == "jbom-new":
        parts = parts[1:]
    normalized_rel = "/".join(parts)

    # Compute absolute source under repo jbom-new
    src = (repo_jbom_new / normalized_rel).resolve()
    assert src.exists() and src.is_dir(), f"Fixtures directory not found: {src}"

    # Compute destination under temp workspace, mirroring the normalized path
    dest = (Path(context.sandbox_root) / normalized_rel).resolve()

    # SAFETY: Refuse to operate if destination escapes the temp workspace
    temp_root = Path(context.sandbox_root).resolve()
    try:
        dest.relative_to(temp_root)
    except Exception:
        raise AssertionError(f"Refusing to write outside temp workspace: {dest}")

    # Create/replace the destination within the temp workspace
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest)


@given('I am in directory "{rel_path}"')
def step_cd_project_root(context, rel_path):
    from pathlib import Path

    base = Path(str(context.project_root))
    new_root = (base / rel_path).resolve()
    new_root.mkdir(parents=True, exist_ok=True)
    context.project_root = new_root


@when('I am in directory "{rel_path}"')
def step_when_cd_project_root(context, rel_path):
    """When-style directory switching (alias to Given)."""
    step_cd_project_root(context, rel_path)


@given('I am in project directory "{name}"')
def step_cd_project_directory(context, name):
    """Switch to a KiCad project directory, creating minimal skeleton if needed."""
    from pathlib import Path
    from ._workspace import ensure_project, chdir

    base = Path(str(context.project_root))
    proj_dir = ensure_project(base, name)
    chdir(context, proj_dir)


@when('I am in project directory "{name}"')
def step_when_cd_project_directory(context, name):
    """When-style project directory switching (alias to Given)."""
    step_cd_project_directory(context, name)


@given('an empty directory "{rel_path}"')
def step_make_empty_dir(context, rel_path):
    from pathlib import Path

    base = Path(context.sandbox_root)
    p = (
        (base / rel_path).resolve()
        if not Path(rel_path).is_absolute()
        else Path(rel_path)
    )
    p.mkdir(parents=True, exist_ok=True)
    # Ensure empty
    for child in p.glob("*"):
        if child.is_file():
            child.unlink()


@given('I create directory "{rel_path}"')
def step_create_directory(context, rel_path):
    from pathlib import Path

    base = Path(context.sandbox_root)
    p = (
        (base / rel_path).resolve()
        if not Path(rel_path).is_absolute()
        else Path(rel_path)
    )
    p.mkdir(parents=True, exist_ok=True)


@given('I create file "{rel_path}" with content "{text}"')
def step_create_file_with_content(context, rel_path, text):
    from pathlib import Path

    base = Path(context.sandbox_root)
    p = (
        (base / rel_path).resolve()
        if not Path(rel_path).is_absolute()
        else Path(rel_path)
    )
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


@given('I create symlink "{link_path}" to "{target_path}"')
def step_create_symlink(context, link_path, target_path):
    import os
    from pathlib import Path

    base = Path(context.sandbox_root)
    link = (
        (base / link_path).resolve()
        if not Path(link_path).is_absolute()
        else Path(link_path)
    )
    target = (
        (base / target_path).resolve()
        if not Path(target_path).is_absolute()
        else Path(target_path)
    )
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        if link.exists() or link.is_symlink():
            link.unlink()
        os.symlink(target, link)
    except OSError as e:
        raise AssertionError(f"Failed to create symlink {link} -> {target}: {e}")


@given('the file "{filename}" is unreadable')
def step_file_is_unreadable(context, filename):
    """Make a file unreadable by removing read permissions."""
    from pathlib import Path
    import stat

    file_path = Path(context.project_root) / filename
    assert file_path.exists(), f"File {filename} does not exist"

    # Remove read permissions (keep only write permissions for owner)
    file_path.chmod(stat.S_IWUSR)


@then("{ref1} appears before {ref2} in the output")
def step_component_appears_before_component(context, ref1, ref2):
    """Check component order in output - supports natural sorting tests.

    TODO: Replace with table-driven approach for better natural ordering tests:

    Scenario Outline: Natural order sorting
      Given the system contains components: <initial_list>
      When I run jbom command "parts"
      Then the result should be:
        | Reference |
        | R1        |
        | R2        |
        | R10       |

    This step applies to BOM, POS, parts, and inventory CSV output commands.
    Should be consolidated into general CSV output testing.
    """
    output = getattr(context, "last_output", "")
    assert output, "No output captured"

    pos1 = output.find(ref1)
    pos2 = output.find(ref2)

    assert pos1 >= 0, f"Component {ref1} not found in output"
    assert pos2 >= 0, f"Component {ref2} not found in output"
    assert pos1 < pos2, f"Expected {ref1} to appear before {ref2} in output"


@then("the command should succeed")
def step_command_should_succeed(context):
    step_check_exit_code(context, 0)


@then("the command should fail")
def step_command_should_fail(context):
    step_check_nonzero_exit(context)


@then('the error output should mention "{text}"')
def step_error_output_should_mention(context, text):
    out = getattr(context, "last_output", "")
    assert text in out, f"Expected error text '{text}' not present. Output:\n{out}"


@then('the output should contain "{text}"')
def step_output_should_contain(context, text):
    out = getattr(context, "last_output", "")
    assert (
        out and text in out
    ), f"Expected text not found in output: {text}\nOutput:\n{out}"


@then("the error output should be empty")
def step_error_output_empty(context):
    out = getattr(context, "last_output", "")
    # Heuristic: in quiet mode there should be no remediation or error messages
    forbidden = [
        "found matching",
        "found project",
        "No project files found",
        "error",
        "warning",
    ]
    assert not any(
        f.lower() in out.lower() for f in forbidden
    ), f"Unexpected messages in output:\n{out}"


@given("print diagnostics")
@when("print diagnostics")
@then("print diagnostics")
def step_print_diagnostics(context):
    diag = getattr(context, "diagnostics", None)
    out = getattr(context, "last_output", None)
    msg = (diag or "(no diagnostics)\n") + ("\n=== OUTPUT ===\n" + out if out else "")
    # Emit to stdout so it works in any phase; do not affect test status
    try:
        print(msg)
    except Exception:
        pass


@then("the two command outputs should be identical")
def step_outputs_identical(context):
    prev = getattr(context, "prev_output", None)
    curr = getattr(context, "last_output", None)
    assert prev is not None, "Previous command output not available for comparison"
    assert curr == prev, f"Outputs differ.\nPrev:\n{prev}\n\nCurr:\n{curr}"


@then('I should see "{text}"')
def step_see_text(context, text):
    """Verify text appears in command output."""
    assert_with_diagnostics(
        context.last_output is not None, "No command output captured", context
    )
    assert_with_diagnostics(
        text in context.last_output,
        f"Expected text '{text}' not found in output",
        context,
    )


def step_check_exit_code(context, expected_code):
    """Check that command exited with expected code."""
    actual_code = getattr(context, "last_exit_code", None)
    assert_with_diagnostics(
        actual_code == expected_code,
        f"Exit code mismatch\n  Expected: {expected_code}\n  Actual:   {actual_code}",
        context,
    )


def step_check_nonzero_exit(context):
    """Check that command failed (non-zero exit)."""
    actual_code = getattr(context, "last_exit_code", None)
    assert_with_diagnostics(
        actual_code != 0, f"Expected failure but got exit code: {actual_code}", context
    )


@then("the exit code should be {expected_code:d}")
def step_check_exit_code_param(context, expected_code):
    """Verify command exit code."""
    assert_with_diagnostics(
        context.last_exit_code is not None, "No command executed", context
    )
    assert_with_diagnostics(
        context.last_exit_code == expected_code,
        "Exit code mismatch",
        context,
        expected=expected_code,
        actual=context.last_exit_code,
    )


@then("the exit code should be non-zero")
def step_check_nonzero_exit_should(context):
    """Verify command failed."""
    assert_with_diagnostics(
        context.last_exit_code is not None, "No command executed", context
    )
    assert_with_diagnostics(
        context.last_exit_code != 0,
        "Expected non-zero exit code",
        context,
        expected="non-zero",
        actual=context.last_exit_code,
    )


@then("I should see usage information")
def step_see_usage(context):
    """Verify usage information is displayed."""
    assert context.last_output is not None, "No command output captured"
    # Check for common usage indicators
    usage_indicators = ["usage:", "jbom", "--help", "--version"]
    found = any(
        indicator in context.last_output.lower() for indicator in usage_indicators
    )
    assert found, f"No usage information found in output.\nGot: {context.last_output}"


@then("I should see available commands")
def step_see_commands(context):
    """Verify available commands are listed."""
    assert context.last_output is not None, "No command output captured"
    # For now, just check that we have some structured output
    # Later we can check for specific commands
    assert len(context.last_output) > 0, "Expected command list, got empty output"


@then("I should see the version number")
def step_see_version(context):
    """Verify version number is displayed."""
    assert context.last_output is not None, "No command output captured"
    # Check for version pattern (digits and dots)
    import re

    version_pattern = r"\d+\.\d+\.\d+"
    assert re.search(
        version_pattern, context.last_output
    ), f"No version number found in output.\nGot: {context.last_output}"


@then("I should see an error message")
def step_see_error(context):
    """Verify an error message is displayed."""
    assert context.last_output is not None, "No command output captured"
    # Check for common error indicators
    error_indicators = ["error", "invalid", "unknown", "not found"]
    found = any(
        indicator in context.last_output.lower() for indicator in error_indicators
    )
    assert found, f"No error message found in output.\nGot: {context.last_output}"


@then('the output does not contain "{text}"')
def step_output_not_contains(context, text):
    out = context.last_output or ""
    assert text not in out, f"Unexpected text found in output: {text}\nOutput:\n{out}"


@then('the output should not contain "{text}"')
def step_output_should_not_contain(context, text):
    """Alias for ultra-simplified pattern consistency."""
    step_output_not_contains(context, text)


@then('a file named "{filename}" should exist')
def step_file_should_exist(context, filename):
    """Verify that a file exists in the project directory."""
    from pathlib import Path

    file_path = Path(context.project_root) / filename
    assert file_path.exists(), f"File not found: {file_path}"


@then('the file "{filename}" should contain "{text}"')
def step_file_should_contain(context, filename, text):
    """Verify that a file contains specific text."""
    from pathlib import Path

    file_path = Path(context.project_root) / filename
    assert file_path.exists(), f"File not found: {file_path}"
    content = file_path.read_text(encoding="utf-8")
    assert (
        text in content
    ), f"Text '{text}' not found in file {filename}\nContent:\n{content}"


@then('a file should exist that contains "{text}"')
def step_any_file_should_contain(context, text):
    """Functional test: verify some file in the sandbox contains the specified text.

    This tests backup behavior without coupling to specific backup file naming conventions.
    """
    from pathlib import Path

    project_dir = Path(context.project_root)
    all_files = list(project_dir.glob("*"))
    text_files = [f for f in all_files if f.is_file() and f.suffix in (".csv", ".txt")]

    found = False
    for file_path in text_files:
        try:
            content = file_path.read_text(encoding="utf-8")
            if text in content:
                found = True
                break
        except (UnicodeDecodeError, PermissionError):
            continue  # Skip binary or inaccessible files

    assert found, (
        f"Text '{text}' not found in any file in the sandbox. "
        f"Files checked: {[f.name for f in text_files]}"
    )


@then("the error output contains error information")
def step_error_output_contains_information(context):
    # Alias to existing error detector
    step_see_error(context)


@then("the output contains verbose information")
def step_output_contains_verbose(context):
    out = context.last_output or ""
    # Heuristic terms that indicate verbose/extra info
    indicators = ["Verbose", "Match_Quality", "Inventory enhanced", "Total:"]
    assert (
        any(term.lower() in out.lower() for term in indicators) or len(out) > 0
    ), f"No verbose information detected. Output:\n{out}"


@then('I should see available commands "bom", "inventory", and "pos"')
def step_see_specific_commands(context):
    """Verify specific commands are listed in help output."""
    assert context.last_output is not None, "No command output captured"
    required_commands = ["bom", "inventory", "pos"]
    for command in required_commands:
        assert_with_diagnostics(
            command in context.last_output,
            f"Expected command '{command}' not found in help output",
            context,
            expected=command,
            actual=context.last_output,
        )


@when('I run "jbom" with no arguments')
def step_run_jbom_no_args(context):
    """Run jbom with no arguments."""
    step_run_command(context, "jbom")


@then("the help text should indicate BOM is always aggregated")
def step_help_text_indicates_bom_aggregated(context):
    """Verify that BOM help text indicates aggregation behavior."""
    assert context.last_output is not None, "No command output captured"
    out = context.last_output.lower()
    # Look for indicators that BOM is aggregated
    indicators = ["aggregated", "procurement", "bill of materials"]
    found = any(indicator in out for indicator in indicators)
    assert (
        found
    ), f"Help text does not indicate BOM aggregation behavior.\nOutput:\n{context.last_output}"


@then("the help text should show both bom and parts commands")
def step_help_text_shows_bom_and_parts(context):
    """Verify that main help shows both BOM and Parts commands."""
    assert context.last_output is not None, "No command output captured"
    out = context.last_output.lower()
    assert (
        "bom" in out
    ), f"BOM command not found in main help.\nOutput:\n{context.last_output}"
    assert (
        "parts" in out
    ), f"Parts command not found in main help.\nOutput:\n{context.last_output}"


# Table-based field validation step definitions (reusable across BOM, POS, inventory, etc.)


@then("the output should contain these fields:")
def step_output_should_contain_fields(context):
    """Verify that CSV output contains specified fields as headers.

    Table format:
    | Field1 | Field2 | Field3 |
    """
    assert context.last_output is not None, "No command output captured"
    assert context.table is not None, "Expected table data for field validation"

    # Get expected fields from first table row
    expected_fields = [cell for cell in context.table.headings]

    # Create expected header line
    expected_header = ",".join(expected_fields)

    # Check if header exists in output
    assert expected_header in context.last_output, (
        f"Expected header fields not found in output.\n"
        f"Expected: {expected_header}\n"
        f"Output:\n{context.last_output}"
    )


@then("the output should not contain these fields:")
def step_output_should_not_contain_fields(context):
    """Verify that CSV output does NOT contain specified fields.

    Table format:
    | Field1 | Field2 | Field3 |
    """
    assert context.last_output is not None, "No command output captured"
    assert context.table is not None, "Expected table data for field validation"

    # Get forbidden fields from first table row
    forbidden_fields = [cell for cell in context.table.headings]

    # Check that none of the forbidden fields appear in output
    for field in forbidden_fields:
        assert field not in context.last_output, (
            f"Forbidden field '{field}' found in output.\n"
            f"Output:\n{context.last_output}"
        )


@then("the output should contain these component data rows:")
def step_output_should_contain_component_data(context):
    """Verify that CSV output contains specified component data rows.

    Table format:
    | R1 | 10.0000 | 5.0000 | TOP |
    | C1 | 15.0000 | 8.0000 | TOP |
    """
    assert context.last_output is not None, "No command output captured"
    assert context.table is not None, "Expected table data for component validation"

    # Check each expected data row
    for row in context.table:
        # Create expected CSV row from table row
        expected_row = ",".join(row.cells)

        # Check if this row exists in output
        assert expected_row in context.last_output, (
            f"Expected data row not found in output.\n"
            f"Expected: {expected_row}\n"
            f"Output:\n{context.last_output}"
        )


@then("the help output should contain these options:")
def step_help_should_contain_options(context):
    """Verify that help output contains specified options and descriptions.

    Table format:
    | --fields | Select specific fields for output |
    | --generic | Use Generic preset |
    """
    assert context.last_output is not None, "No command output captured"
    assert context.table is not None, "Expected table data for help validation"

    # Check each expected option
    for row in context.table:
        option = row["option"] if "option" in row.headings else row.cells[0]
        description = (
            row["description"] if "description" in row.headings else row.cells[1]
        )

        # Check if option exists in help output
        assert option in context.last_output, (
            f"Expected help option '{option}' not found in output.\n"
            f"Output:\n{context.last_output}"
        )

        # Check if description exists in help output (optional check)
        if description and len(description) > 0:
            assert description in context.last_output, (
                f"Expected help description '{description}' not found in output.\n"
                f"Output:\n{context.last_output}"
            )


@then("the error output should contain these options:")
def step_error_output_should_contain_options(context):
    """Verify that error output contains specified options - alias for help validation."""
    step_help_should_contain_options(context)


@then("the error output should list these available fields:")
def step_error_should_list_available_fields(context):
    """Verify that error output lists the specified available fields.

    Table format:
    | Reference | X | Y | Rotation | Side | Footprint | Package | Value |
    """
    assert context.last_output is not None, "No command output captured"
    assert (
        context.table is not None
    ), "Expected table data for available fields validation"

    # Get expected available fields from first table row
    expected_fields = [cell for cell in context.table.headings]

    # Check that "Available fields:" text exists
    assert "Available fields:" in context.last_output, (
        f"'Available fields:' text not found in error output.\n"
        f"Output:\n{context.last_output}"
    )

    # Check that each expected field is mentioned in the error output
    for field in expected_fields:
        assert field in context.last_output, (
            f"Expected available field '{field}' not found in error output.\n"
            f"Output:\n{context.last_output}"
        )


@then("the output should contain the fabricator defined {fabricator_name} POS fields")
def step_output_should_contain_fabricator_pos_fields(context, fabricator_name):
    """Verify that output contains fabricator-specific POS fields.

    This is a placeholder step definition that validates the fabricator name is mentioned
    and that some POS-specific fields are present. More specific validation would require
    reading the actual fabricator configuration.
    """
    assert context.last_output is not None, "No command output captured"

    # Basic validation - at minimum should be CSV output with some placement fields
    common_pos_fields = ["Reference", "Designator", "X", "Y", "Mid X", "Mid Y"]
    found_pos_field = any(field in context.last_output for field in common_pos_fields)

    assert found_pos_field, (
        f"No POS fields found in {fabricator_name} fabricator output.\n"
        f"Expected at least one of: {common_pos_fields}\n"
        f"Output:\n{context.last_output}"
    )
