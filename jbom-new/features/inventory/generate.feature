@wip
Feature: Inventory Generation
  As a hardware developer
  I want to generate inventory from project components
  So that I can plan sourcing and stock

  Background:
    Given the generic fabricator is selected

  Scenario: Generate inventory from schematic components
    Given a schematic that contains:
      | Reference | Value | Footprint         | LibID                        |
      | R1        | 10K   | R_0805_2012       | Device:R                     |
      | C1        | 100nF | C_0603_1608       | Device:C                     |
      | U1        | LM358 | SOIC-8_3.9x4.9mm | Amplifier_Operational:LM358 |
    When I run jbom command "inventory generate -o project_inventory.csv"
    Then the command should succeed
    And a file named "project_inventory.csv" should exist
    And the file "project_inventory.csv" should contain "Category"

  Scenario: Group identical components into single inventory rows
    Given a schematic that contains:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10K   | R_0805_2012 | Device:R |
      | R2        | 10K   | R_0805_2012 | Device:R |
      | R3        | 22K   | R_0805_2012 | Device:R |
    When I run jbom command "inventory generate -o grouped_inventory.csv"
    Then the command should succeed
    And a file named "grouped_inventory.csv" should exist

  Scenario: Verbose generation shows processing details
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
    When I run jbom command "inventory generate -o verbose_inventory.csv -v"
    Then the command should succeed
    And the output should contain "Generated inventory"

  Scenario: Handle empty schematic
    Given a schematic that contains:
      | Reference | Value | Footprint |
    When I run jbom command "inventory generate -o empty_inventory.csv"
    Then the command should succeed
    And the output should contain "Generated inventory with 0 items"
