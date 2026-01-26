"""Step definitions for testing diagnostic output quality.

These steps allow us to validate that when tests fail, they produce helpful
diagnostic information for debugging.
"""

from behave import when, then
from features.steps.diagnostic_utils import assert_with_diagnostics


@when('I expect text assertion "{expected_text}" to fail for command "{command}"')
def step_expect_text_assertion_failure(context, expected_text, command):
    """Execute a command and expect a text assertion to fail, capturing diagnostics.

    This step:
    1. Runs the specified command
    2. Attempts to find the expected text (which should fail)
    3. Captures the AssertionError with diagnostic output
    4. Stores the diagnostic output for validation
    """
    # First run the command (reuse existing step)
    from features.steps.common_steps import step_run_command

    step_run_command(context, command)

    # Now attempt the text assertion and capture the failure
    try:
        assert_with_diagnostics(
            expected_text in context.last_output,
            f"Expected text '{expected_text}' not found in output",
            context,
            expected=expected_text,
            actual=context.last_output,
        )
        # If we get here, the assertion didn't fail as expected
        raise AssertionError(
            f"Expected text assertion to fail, but '{expected_text}' was found in output"
        )
    except AssertionError as e:
        # This is the expected failure - capture the diagnostic output
        context.captured_diagnostic = str(e)


@when('I expect plugin assertion "{expected_plugin}" to fail for command "{command}"')
def step_expect_plugin_assertion_failure(context, expected_plugin, command):
    """Execute a command and expect a plugin assertion to fail, capturing diagnostics."""
    # First run the command (reuse existing step)
    from features.steps.common_steps import step_run_command

    step_run_command(context, command)

    # Now attempt the plugin assertion and capture the failure
    try:
        assert_with_diagnostics(
            expected_plugin in context.last_output,
            f"Expected plugin '{expected_plugin}' not found in output",
            context,
            expected=expected_plugin,
            actual=context.last_output,
        )
        # If we get here, the assertion didn't fail as expected
        raise AssertionError(
            f"Expected plugin assertion to fail, but '{expected_plugin}' was found in output"
        )
    except AssertionError as e:
        # This is the expected failure - capture the diagnostic output
        context.captured_diagnostic = str(e)


@then('the diagnostic output should contain "{text}"')
def step_diagnostic_should_contain(context, text):
    """Verify that the captured diagnostic output contains specific text."""
    if not hasattr(context, "captured_diagnostic"):
        raise AssertionError(
            "No diagnostic output captured. Use a 'when I expect ... to fail' step first."
        )

    diagnostic = context.captured_diagnostic
    if text not in diagnostic:
        raise AssertionError(
            f"Expected diagnostic text not found.\n"
            f"Expected: {text}\n"
            f"Diagnostic output:\n{diagnostic}"
        )


@then('the diagnostic output should show command "{command}"')
def step_diagnostic_should_show_command(context, command):
    """Verify that the diagnostic output shows the executed command."""
    step_diagnostic_should_contain(context, f"Command: {command}")


@then("the diagnostic output should show exit code {exit_code:d}")
def step_diagnostic_should_show_exit_code(context, exit_code):
    """Verify that the diagnostic output shows the expected exit code."""
    step_diagnostic_should_contain(context, f"Exit Code: {exit_code}")


@then("the diagnostic output should show the actual output")
def step_diagnostic_should_show_actual_output(context):
    """Verify that the diagnostic output includes the actual command output."""
    if not hasattr(context, "last_output"):
        raise AssertionError("No command output available")

    # The diagnostic should contain the actual output
    step_diagnostic_should_contain(context, context.last_output.strip())


@then("the diagnostic output should show working directory")
def step_diagnostic_should_show_working_directory(context):
    """Verify that the diagnostic output shows the working directory."""
    step_diagnostic_should_contain(context, "--- WORKING DIRECTORY ---")


@then("the diagnostic output should show plugins directory")
def step_diagnostic_should_show_plugins_directory(context):
    """Verify that the diagnostic output shows plugin directory information."""
    step_diagnostic_should_contain(context, "--- PLUGINS DIRECTORY ---")


@then("the diagnostic output should show expected vs actual comparison")
def step_diagnostic_should_show_comparison(context):
    """Verify that the diagnostic output shows expected vs actual comparison."""
    step_diagnostic_should_contain(context, "Expected:")
    step_diagnostic_should_contain(context, "Actual:")
