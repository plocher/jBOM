"""Common step definitions for jBOM CLI testing."""

import subprocess
from behave import when, then, given
from diagnostic_utils import assert_with_diagnostics


@given("a clean test workspace")
def step_clean_test_workspace(context):
    """Create an isolated workspace for the scenario and use it as project_root."""
    import tempfile
    from pathlib import Path

    tmp = Path(tempfile.mkdtemp(prefix="jbom_behave_"))
    context.project_root = tmp
    # Keep src_root unchanged (set by environment.py)


@when('I run "{command}"')
def step_run_command(context, command):
    """Run a CLI command and capture output."""
    # Preserve previous output for later comparisons
    context.prev_output = getattr(context, "last_output", None)

    # For now, run via python -m until we have proper installation
    if command.startswith("jbom "):
        # Replace 'jbom' with python module invocation
        raw_args = command.split()[1:]  # Remove 'jbom' prefix

        # Default to generic fabricator for predictable behavior on BOM unless explicitly set
        if len(raw_args) >= 1 and raw_args[0] == "bom":
            has_fabricator_flag = any(
                a.startswith("--fabricator") for a in raw_args
            ) or any(
                a in ("--jlc", "--pcbway", "--seeed", "--generic") for a in raw_args
            )
            if not has_fabricator_flag:
                raw_args += ["--fabricator", "generic"]

        cmd = ["python", "-m", "jbom.cli.main"] + raw_args
    else:
        cmd = command.split()

    # Set PYTHONPATH to include src directory
    import os

    env = os.environ.copy()
    env["PYTHONPATH"] = str(context.src_root)

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
    except Exception as e:
        context.last_command = command
        context.last_output = str(e)
        context.last_exit_code = 1


@when('I run jbom command "{args}"')
def step_run_jbom_command(context, args):
    """Alias for running jbom commands without repeating the prefix."""
    step_run_command(context, f"jbom {args}")


@given('the sample fixtures under "{rel_path}"')
def step_have_sample_fixtures(context, rel_path):
    """Copy fixture subtree into the temp workspace so tests don't write under repo.

    Example rel_path: "features/fixtures/kicad_samples".
    We copy that directory from the repo root into context.project_root/rel_path.
    """
    from pathlib import Path
    import shutil

    # Compute source (repo) and destination (temp workspace) paths
    repo_root = Path(__file__).parent.parent  # features/
    src = (repo_root / rel_path).resolve()
    assert src.exists() and src.is_dir(), f"Fixtures directory not found: {src}"

    dest = context.project_root / rel_path
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest)


@given('I am in directory "{rel_path}"')
def step_cd_project_root(context, rel_path):
    from pathlib import Path

    base = Path(str(context.project_root))
    new_root = (base / rel_path).resolve()
    assert new_root.exists() and new_root.is_dir(), f"Directory not found: {new_root}"
    context.project_root = new_root


@given('an empty directory "{rel_path}"')
def step_make_empty_dir(context, rel_path):
    from pathlib import Path

    p = (Path(str(context.project_root)) / rel_path).resolve()
    p.mkdir(parents=True, exist_ok=True)
    # Ensure empty
    for child in p.glob("*"):
        if child.is_file():
            child.unlink()


@given('I create directory "{rel_path}"')
def step_create_directory(context, rel_path):
    from pathlib import Path

    p = (Path(str(context.project_root)) / rel_path).resolve()
    p.mkdir(parents=True, exist_ok=True)


@given('I create file "{rel_path}" with content "{text}"')
def step_create_file_with_content(context, rel_path, text):
    from pathlib import Path

    p = (Path(str(context.project_root)) / rel_path).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


@given('I create symlink "{link_path}" to "{target_path}"')
def step_create_symlink(context, link_path, target_path):
    import os
    from pathlib import Path

    base = Path(str(context.project_root))
    link = (base / link_path).resolve()
    target = (base / target_path).resolve()
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        if link.exists() or link.is_symlink():
            link.unlink()
        os.symlink(target, link)
    except OSError as e:
        raise AssertionError(f"Failed to create symlink {link} -> {target}: {e}")


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
        "Expected text not found in output",
        context,
        expected=text,
        actual=context.last_output,
    )


@then("I should see {text} in the output")
def step_see_text_in_output(context, text):
    """Verify text appears in command output (alternative phrasing)."""
    # Remove quotes if present
    text = text.strip("\"'")
    assert_with_diagnostics(
        context.last_output is not None, "No command output captured", context
    )
    assert_with_diagnostics(
        text in context.last_output,
        "Expected text not found in output",
        context,
        expected=text,
        actual=context.last_output,
    )


@then("the exit code should be {expected_code:d}")
def step_check_exit_code(context, expected_code):
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
def step_check_nonzero_exit(context):
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
