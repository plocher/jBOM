Feature: BOM Help
  As a developer
  I want clear CLI help for BOM
  So that I can discover options quickly

  Scenario: Help command shows major options
    When I run "jbom bom --help"
    Then the command exits with code 0
    And the output contains "--aggregation"
    And the output contains "--inventory"
    And the output contains "--include-dnp"
