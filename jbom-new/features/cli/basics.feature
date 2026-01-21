Feature: CLI Basics
  As a jBOM user
  I want basic CLI functionality
  So that I can interact with jBOM

  Background:
    Given the generic fabricator is selected

  Scenario: Show help
    When I run jbom command "--help"
    Then the command should succeed
    And the output should contain "usage:"
    And the output should contain "bom"
    And the output should contain "pos"
    And the output should contain "inventory"

  Scenario: Show version
    When I run jbom command "--version"
    Then the command should succeed
    And the output should contain "jbom"

  Scenario: Handle unknown command
    When I run jbom command "unknown-command"
    Then the command should fail
    And the output should contain "unrecognized arguments"

  Scenario: No command specified
    When I run "jbom" with no arguments
    Then the command should fail
    And the output should contain "usage:"
