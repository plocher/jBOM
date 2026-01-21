Feature: Inventory flows with project-centric inputs

  Background:
    Given the generic fabricator is selected

  Scenario: Inventory from project directory (flat)
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | C1        | 100nF | C_0603_1608 |
    When I run jbom command "inventory generate -o console"
    Then the command should succeed

  Scenario: Inventory from hierarchical design
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | U1        | LM358 | SOIC-8_3.9x4.9mm |
    When I run jbom command "inventory generate -o console -v"
    Then the command should succeed
    And the output should contain "Generated inventory"
