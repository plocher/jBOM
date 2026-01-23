@wip
Feature: Inventory Management (Core Functionality)
  As a hardware developer
  I want to generate component inventory from project
  So that I can plan sourcing and stock management

  Background:
    Given the generic fabricator is selected

  Scenario: Generate inventory with default console output (human-first)
    Given a schematic that contains:
      | Reference | Value | Footprint         | LibID                        |
      | R1        | 10K   | R_0805_2012       | Device:R                     |
      | C1        | 100nF | C_0603_1608       | Device:C                     |
      | U1        | LM358 | SOIC-8_3.9x4.9mm | Amplifier_Operational:LM358 |
    When I run jbom command "inventory"
    Then the command should succeed
    And the output should contain "Generated inventory"
    And the output should contain "IPN"
    And the output should contain "Category"

  Scenario: Generate inventory to explicit file
    Given a schematic that contains:
      | Reference | Value | Footprint         | LibID                        |
      | R1        | 10K   | R_0805_2012       | Device:R                     |
      | C1        | 100nF | C_0603_1608       | Device:C                     |
    When I run jbom command "inventory -o project_inventory.csv"
    Then the command should succeed
    And a file named "project_inventory.csv" should exist
    And the file "project_inventory.csv" should contain "Category"

  Scenario: Group identical components into single inventory rows
    Given a schematic that contains:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10K   | R_0805_2012 | Device:R |
      | R2        | 10K   | R_0805_2012 | Device:R |
      | R3        | 22K   | R_0805_2012 | Device:R |
    When I run jbom command "inventory -o grouped_inventory.csv"
    Then the command should succeed
    And a file named "grouped_inventory.csv" should exist

  Scenario: Generate inventory with console output
    Given a schematic that contains:
      | Reference | Value | Footprint | IPN      | Category  |
      | R1        | 10K   | 0805      | RES_10K  | RESISTOR  |
      | C1        | 100nF | 0603      | CAP_100N | CAPACITOR |
      | U1        | LM358 | SOIC-8    | IC_LM358 | IC        |
    When I run jbom command "inventory -o console"
    Then the command should succeed
    And the output should contain "Generated inventory"
    And the output should contain "IPN"
    And the output should contain "Category"

  Scenario: Verbose generation shows processing details
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
    When I run jbom command "inventory -o verbose_inventory.csv -v"
    Then the command should succeed
    And the output should contain "Generated inventory"

  Scenario: Generate inventory to file
    Given a schematic that contains:
      | Reference | Part Number | Quantity |
      | R1        | RES-0805-10K| 1        |
      | C1        | CAP-0603-10U| 1        |
    When I run jbom command "inventory -o inventory.csv"
    Then the command should succeed
    And a file named "basic_inventory.csv" should exist

  Scenario: Handle empty schematic
    Given a schematic that contains:
      | Reference | Part Number | Quantity |
    When I run jbom command "inventory -o console"
    Then the command should fail
    And the output should contain "Error: No components found in project. Cannot create inventory from empty schematic."

  Scenario: Inventory help command
    When I run jbom command "inventory --help"
    Then the command should succeed
    And the output should contain "Generate component inventory from project"
