Feature: Plugin Discovery
  As a jBOM developer
  I want jBOM to discover core plugins at startup
  So that workflows and services are available

  Scenario: List plugins when none exist
    Given no plugins have been installed
    When I run "jbom plugin list"
    Then I should see "No core plugins found"
    And the exit code should be 0

  Scenario: List core plugins with versions
    Given a core plugin "bom" exists with version "1.0.0"
    When I run "jbom plugin list"
    Then I should see "Core plugins:"
    And I should see "bom" in the output
    And I should see "1.0.0" in the output
    And the exit code should be 0
