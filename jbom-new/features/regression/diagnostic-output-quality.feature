@regression @diagnostic_test
Feature: Diagnostic Output Quality
  As a jBOM developer
  I want helpful diagnostic output when tests fail
  So that I can quickly debug issues

  # This feature intentionally contains failing tests to verify diagnostic output
  # Run with: behave --tags=diagnostic_test --no-capture
  # These tests SHOULD fail - that's the point!
  # We're verifying the failure output is helpful for debugging.

  Background:
    Given a sandbox

  Scenario: Diagnostic shows command and output on text mismatch
    When I expect text assertion "INTENTIONALLY_WRONG_TEXT" to fail for command "jbom --version"
    Then the diagnostic output should show command "jbom --version"
    And the diagnostic output should show exit code 0
    And the diagnostic output should show the actual output
    And the diagnostic output should show expected vs actual comparison
    And the diagnostic output should show working directory
    And the diagnostic output should contain "DIAGNOSTIC INFORMATION"

  Scenario: Diagnostic shows plugin state on plugin test failure
    Given a core plugin "test" exists with version "1.0.0"
    When I expect plugin assertion "WRONG_PLUGIN_NAME" to fail for command "jbom plugin --list"
    Then the diagnostic output should show command "jbom plugin --list"
    And the diagnostic output should show plugins directory
    And the diagnostic output should contain "CREATED TEST PLUGINS"
    And the diagnostic output should show expected vs actual comparison
    And the diagnostic output should contain "DIAGNOSTIC INFORMATION"
