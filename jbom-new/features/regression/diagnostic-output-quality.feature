@regression @diagnostic_test
Feature: Test Failure Diagnostic Quality
  As a jBOM developer
  I want comprehensive diagnostic information when tests fail
  So that I can quickly identify and fix the root cause

  # This feature validates that test failures provide helpful debugging context
  # Tests should PASS when diagnostic infrastructure works correctly
  # Tests should FAIL when diagnostic infrastructure is broken

  Background:
    Given a sandbox

  Scenario: Test failures provide comprehensive diagnostic context
    When a test fails looking for missing content
    Then I should receive detailed diagnostic information
    And the diagnostic should include the command that was executed
    And the diagnostic should show the exit code
    And the diagnostic should show the actual output
    And the diagnostic should show expected vs actual comparison
    And the diagnostic should include working directory context
    And the diagnostic should be clearly labeled

  Scenario: Command error test failures include comprehensive context
    When a test fails with an invalid command
    Then I should receive detailed diagnostic information
    And the diagnostic should include the command that was executed
    And the diagnostic should show the exit code
    And the diagnostic should show the actual error output
    And the diagnostic should show expected vs actual comparison
    And the diagnostic should include working directory context
    And the diagnostic should be clearly labeled
