@wip
Feature: Inventory Management (Core Functionality)
  As a hardware developer
  I want to track component inventory and usage
  So that I can manage parts procurement and availability

  Background:
    Given the generic fabricator is selected

  Scenario: Generate basic inventory report
    Given a schematic that contains:
      | Reference | Part Number | Quantity |
      | R1,R2     | RES-0805-10K| 2        |
      | C1        | CAP-0603-10U| 1        |
      | U1        | IC-MCU-ATMEGA328P | 1  |
    When I run jbom command "inventory -o console"
    Then the command should succeed
    And the output should contain "Generated inventory"
    And the output should contain "IPN"
    And the output should contain "Category"

  Scenario: Generate inventory with console output
    Given a schematic that contains:
      | Reference | Part Number | Quantity |
      | R1,R2,R3  | RES-0805-10K| 3        |
      | C1,C2     | CAP-0603-10U| 2        |
    When I run jbom command "inventory -o console"
    Then the command should succeed
    And the output should contain "Generated inventory"
    And the output should contain "IPN"
    And the output should contain "Category"

  Scenario: Generate inventory to file
    Given a schematic that contains:
      | Reference | Part Number | Quantity |
      | R1        | RES-0805-10K| 1        |
      | C1        | CAP-0603-10U| 1        |
    When I run jbom command "inventory -o inventory.csv"
    Then the command should succeed
    And a file named "inventory.csv" exists

  Scenario: Handle empty schematic
    Given a schematic that contains:
      | Reference | Part Number | Quantity |
    When I run jbom command "inventory -o console"
    Then the command should succeed
    And the output should contain "Generated inventory with 0 items"

  Scenario: Inventory help command
    When I run jbom command "inventory --help"
    Then the command should succeed
    And the output should contain "Generate component inventory from project"
