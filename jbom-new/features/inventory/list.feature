Feature: Inventory Listing
  As a hardware developer
  I want to list and filter inventory items
  So that I can quickly find components

  Background:
    Given a clean test workspace

  Scenario: List all inventory items
    Given an inventory file "components.csv" with data:
      | IPN      | Category  | Value | Description        | Package |
      | RES_10K  | RESISTOR  | 10K   | 10K Ohm Resistor  | 0805    |
      | CAP_100N | CAPACITOR | 100nF | 100nF Ceramic Cap | 0603    |
      | IC_LM358 | IC        | LM358 | Dual Op-Amp       | SOIC-8  |
    When I run "jbom inventory list components.csv"
    Then the command exits with code 0
    And the output contains "Inventory: 3 items"

  Scenario: Filter inventory by category
    Given an inventory file "mixed.csv" with mixed component categories
    When I run "jbom inventory list mixed.csv --category resistor"
    Then the command exits with code 0
    And the output contains only resistor components
    And the output does not contain capacitor components

  Scenario: Empty inventory shows no items
    Given an empty inventory file "empty.csv"
    When I run "jbom inventory list empty.csv"
    Then the command exits with code 0
    And the output contains "No items found"

  Scenario: Help command
    When I run "jbom inventory list --help"
    Then the command exits with code 0
    And the output contains "List inventory items"
    And the output contains "--category"

  Scenario: Missing inventory file
    When I run "jbom inventory list nonexistent.csv"
    Then the command exits with code 1
    And the error output contains "Inventory file not found"

  Scenario: Invalid inventory file format
    Given a file "invalid.csv" with invalid CSV format
    When I run "jbom inventory list invalid.csv"
    Then the command exits with code 1
    And the error output contains error information
