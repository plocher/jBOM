@wip
Feature: Inventory Listing
  As a hardware developer
  I want to list and filter inventory items
  So that I can quickly find components

  Background:
    Given the generic fabricator is selected

  @wip
  Scenario: List all inventory items
    Given a schematic that contains:
      | Reference | Value | Footprint | IPN      | Category  |
      | R1        | 10K   | 0805      | RES_10K  | RESISTOR  |
      | C1        | 100nF | 0603      | CAP_100N | CAPACITOR |
      | U1        | LM358 | SOIC-8    | IC_LM358 | IC        |
    When I run jbom command "inventory list -o console"
    Then the command should succeed
    And the output should contain "Inventory: 3 items"

  @wip
  Scenario: Filter inventory by category
    Given a schematic that contains:
      | Reference | Value | Category  |
      | R1        | 10K   | RESISTOR  |
      | C1        | 100nF | CAPACITOR |
    When I run jbom command "inventory list --category resistor"
    Then the command should succeed
    And the output should contain "R1"
    And the output should not contain "C1"

  @wip
  Scenario: Empty inventory shows no items
    Given a schematic that contains:
      | Reference | Value | Footprint |
    When I run jbom command "inventory list -o console"
    Then the command should succeed
    And the output should contain "No items found"
