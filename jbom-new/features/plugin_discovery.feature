Feature: Plugin Discovery
  As a jBOM developer
  I want jBOM to discover core plugins at startup
  So that workflows and services are available

  Scenario: Plugin discovery at startup
    Given core plugins exist in "src/jbom_new/plugins/"
    When jBOM starts
    Then it should discover all core plugins
    And it should build a service registry
    And it should build a workflow registry

  Scenario: List core plugins
    When I run "jbom plugins list"
    Then I should see "Core plugins:"
    And I should see the bom plugin listed
    And I should see plugin versions
    And the exit code should be 0
