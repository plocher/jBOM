@regression @diagnostic_test
Feature: Diagnostic Output Quality
  As a jBOM developer
  I want helpful diagnostic output when tests fail
  So that I can quickly debug issues

  # This feature intentionally contains failing tests to verify diagnostic output
  # Run with: behave --tags=diagnostic_test --no-capture
  # These tests SHOULD fail - that's the point!
  # We're verifying the failure output is helpful for debugging.

  Scenario: Diagnostic shows command and output on text mismatch
    When I run "jbom --version"
    Then I should see "INTENTIONALLY_WRONG_TEXT"
    # Expected diagnostic sections:
    # - COMMAND EXECUTED
    # - Exit Code
    # - OUTPUT
    # - Expected vs Actual

  Scenario: Diagnostic shows plugin state on plugin test failure
    Given a core plugin "test" exists with version "1.0.0"
    When I run "jbom plugin --list"
    Then I should see "WRONG_PLUGIN_NAME"
    # Expected diagnostic sections:
    # - PLUGINS DIRECTORY
    # - CREATED TEST PLUGINS
