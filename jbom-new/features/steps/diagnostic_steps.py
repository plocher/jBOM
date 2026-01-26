"""Step definitions for testing diagnostic output quality.

These steps allow us to validate that when tests fail, they produce helpful
diagnostic information for debugging.
"""

from behave import when, then
from features.steps.diagnostic_utils import assert_with_diagnostics


@when("a test fails looking for missing content")
def step_test_fails_missing_content(context):
    """Simulate a test failure scenario by running a command and looking for content that won't be found.

    This step:
    1. Runs a test command (jbom --version)
    2. Attempts to find text that won't be there (simulating test failure)
    3. Captures the diagnostic output that would be provided to the developer
    4. Stores the diagnostic output for validation
    """
    # First run a command (reuse existing step)
    from features.steps.common_steps import step_run_command

    step_run_command(context, "jbom --version")

    # Now simulate looking for missing content and capture the diagnostic failure
    expected_text = "INTENTIONALLY_WRONG_TEXT"
    try:
        assert_with_diagnostics(
            expected_text in context.last_output,
            f"Expected text '{expected_text}' not found in output",
            context,
            expected=expected_text,
            actual=context.last_output,
        )
        # If we get here, the test didn't fail as expected
        raise AssertionError(
            f"Expected test to fail, but '{expected_text}' was found in output"
        )
    except AssertionError as e:
        # This is the expected failure - capture the diagnostic output
        context.captured_diagnostic = str(e)


@when("a plugin-related test fails")
def step_plugin_test_fails(context):
    """Simulate a plugin-related test failure scenario.

    This step:
    1. Runs a plugin-related command
    2. Attempts to find a plugin that won't be there (simulating test failure)
    3. Captures the diagnostic output that would be provided to the developer
    """
    # First run a command (reuse existing step)
    from features.steps.common_steps import step_run_command

    step_run_command(context, "jbom plugin --list")

    # Now simulate looking for missing plugin and capture the diagnostic failure
    expected_plugin = "WRONG_PLUGIN_NAME"
    try:
        assert_with_diagnostics(
            expected_plugin in context.last_output,
            f"Expected plugin '{expected_plugin}' not found in output",
            context,
            expected=expected_plugin,
            actual=context.last_output,
        )
        # If we get here, the test didn't fail as expected
        raise AssertionError(
            f"Expected plugin test to fail, but '{expected_plugin}' was found in output"
        )
    except AssertionError as e:
        # This is the expected failure - capture the diagnostic output
        context.captured_diagnostic = str(e)


@then("I should receive detailed diagnostic information")
def step_should_receive_diagnostic_info(context):
    """Verify that diagnostic information was captured when the test failed."""
    if not hasattr(context, "captured_diagnostic"):
        raise AssertionError(
            "No diagnostic output captured. The test failure simulation may not have worked."
        )

    diagnostic = context.captured_diagnostic
    if not diagnostic or len(diagnostic.strip()) == 0:
        raise AssertionError("Diagnostic output was captured but appears to be empty")


@then('the diagnostic should contain "{text}"')
def step_diagnostic_should_contain(context, text):
    """Verify that the diagnostic output contains specific text."""
    if not hasattr(context, "captured_diagnostic"):
        raise AssertionError(
            "No diagnostic output captured. The test failure simulation may not have worked."
        )

    diagnostic = context.captured_diagnostic
    if text not in diagnostic:
        raise AssertionError(
            f"Expected diagnostic text not found.\n"
            f"Expected: {text}\n"
            f"Diagnostic output:\n{diagnostic}"
        )


@then("the diagnostic should include the command that was executed")
def step_diagnostic_should_include_command(context):
    """Verify that the diagnostic output shows what command was executed."""
    step_diagnostic_should_contain(context, "Command:")


@then("the diagnostic should show the exit code")
def step_diagnostic_should_show_exit_code(context):
    """Verify that the diagnostic output shows the command exit code."""
    step_diagnostic_should_contain(context, "Exit Code:")


@then("the diagnostic should show the actual output")
def step_diagnostic_should_show_actual_output(context):
    """Verify that the diagnostic output includes the actual command output."""
    step_diagnostic_should_contain(context, "--- OUTPUT ---")


@then("the diagnostic should show expected vs actual comparison")
def step_diagnostic_should_show_comparison(context):
    """Verify that the diagnostic output shows expected vs actual comparison."""
    step_diagnostic_should_contain(context, "Expected:")
    step_diagnostic_should_contain(context, "Actual:")


@then("the diagnostic should include working directory context")
def step_diagnostic_should_include_working_directory(context):
    """Verify that the diagnostic output shows the working directory."""
    step_diagnostic_should_contain(context, "--- WORKING DIRECTORY ---")


@then("the diagnostic should be clearly labeled")
def step_diagnostic_should_be_labeled(context):
    """Verify that the diagnostic output is clearly labeled."""
    step_diagnostic_should_contain(context, "DIAGNOSTIC INFORMATION")


@then("the diagnostic should show the plugin directory state")
def step_diagnostic_should_show_plugin_directory(context):
    """Verify that the diagnostic output shows plugin directory information."""
    step_diagnostic_should_contain(context, "--- PLUGINS DIRECTORY ---")


@then("the diagnostic should show any test plugins that were created")
def step_diagnostic_should_show_created_plugins(context):
    """Verify that the diagnostic output shows any test plugins that were created."""
    step_diagnostic_should_contain(context, "CREATED TEST PLUGINS")
