Feature: CLI Basics
  As a jBOM user
  I want basic CLI functionality
  So that I can interact with jBOM

  Scenario: Show help
    When I run "jbom --help"
    Then I should see usage information
    And I should see available commands "bom", "inventory", and "pos"
    And the exit code should be 0

  Scenario: Show version
    When I run "jbom --version"
    Then I should see the version number
    And the exit code should be 0

  Scenario: Handle unknown command
    When I run "jbom unknown-command"
    Then I should see an error message
    And the exit code should be non-zero

  Scenario: No command specified
    When I run "jbom" with no arguments
    Then I should see usage information
    And the exit code should be non-zero
