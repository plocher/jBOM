@wip
Feature: Multi-Source Inventory
  As a sourcing engineer
  I want to combine multiple inventory sources
  So that the best available part data is used in the BOM

  Background:
    Given the generic fabricator is selected

  # Combine two inventory files and enhance BOM
  @wip
  Scenario: Merge two inventory files when enhancing BOM
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | C1        | 100nF | C_0603_1608 |
    When I run jbom command "bom --inventory inv_primary.csv --inventory inv_secondary.csv"
    Then the command should succeed
    And the output should contain "Inventory enhanced"

  # Precedence: primary overrides secondary when conflicting
  @wip
  Scenario: Primary inventory takes precedence on conflicts
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
    When I run jbom command "bom --inventory inv_primary.csv --inventory inv_secondary.csv"
    Then the command should succeed
    And the output should contain "Primary"
