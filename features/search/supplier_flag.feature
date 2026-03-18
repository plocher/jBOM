Feature: Search supplier flag
  As a jBOM user
  I want search to use the same supplier flag as audit and inventory
  So that the CLI is consistent across commands

  Scenario: Search accepts --supplier
    Given a generic supplier
    When I run "jbom search 10k --supplier generic --limit 1"
    Then the command should succeed
    And the output should contain "No results found."

  Scenario: Search accepts mixed-case --supplier
    Given a generic supplier
    When I run "jbom search 10k --supplier GENERIC --limit 1"
    Then the command should succeed
    And the output should contain "No results found."

  Scenario: Search accepts mixed-case --defaults profile
    Given a generic supplier
    When I run "jbom search 10k --supplier generic --defaults GENERIC --limit 1"
    Then the command should succeed
    And the output should contain "No results found."

  Scenario: Search rejects retired --provider flag
    Given a generic supplier
    When I run "jbom search 10k --provider generic --limit 1"
    Then the command should fail
    And the output should contain "--provider"
