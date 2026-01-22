@wip
Feature: Inventory Console Output
  As a hardware developer
  I want to display inventory items in a formatted table
  So that I can quickly review components

  Background:
    Given the generic fabricator is selected

  @wip
  Scenario: Display all inventory items as console table
    Given a schematic that contains:
      | Reference | Value | Footprint | IPN      | Category  |
      | R1        | 10K   | 0805      | RES_10K  | RESISTOR  |
      | C1        | 100nF | 0603      | CAP_100N | CAPACITOR |
      | U1        | LM358 | SOIC-8    | IC_LM358 | IC        |
    When I run jbom command "inventory -o console"
    Then the command should succeed
    And the output should contain "Inventory: 3 items"

  @wip
  Scenario: Display inventory items from project
    Given a schematic that contains:
      | Reference | Value | Category  |
      | R1        | 10K   | RESISTOR  |
      | C1        | 100nF | CAPACITOR |
    When I run jbom command "inventory -o console"
    Then the command should succeed
    And the output should contain "R1"
    And the output should contain "C1"

  @wip
  Scenario: Empty project shows no items
    Given a schematic that contains:
      | Reference | Value | Footprint |
    When I run jbom command "inventory -o console"
    Then the command should fail
    And the output should contain "Error: No components found in project. Cannot create inventory from empty schematic."
