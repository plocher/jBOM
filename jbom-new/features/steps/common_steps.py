"""Common step definitions for jBOM CLI testing."""

import subprocess
from behave import when, then
from diagnostic_utils import assert_with_diagnostics


@when('I run "{command}"')
def step_run_command(context, command):
    """Run a CLI command and capture output."""
    # For now, run via python -m until we have proper installation
    if command.startswith("jbom "):
        # Replace 'jbom' with python module invocation
        args = command.split()[1:]  # Remove 'jbom' prefix
        cmd = ["python", "-m", "jbom_new.cli.main"] + args
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
