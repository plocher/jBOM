Feature: Inventory Search (Dry Run)
  As a jBOM user
  I want to validate inventory-search inputs without hitting the network
  So that I can safely test workflows without API calls

  Scenario: Dry run with a simple inventory
    Given an inventory file "inventory.csv" that contains:
      | IPN     | Category | Value | Description   | Package |
      | RES_10K | RES      | 10K   | Resistor 10K  | 0603    |
      | CAP_1U  | CAP      | 1uF   | Capacitor 1uF | 0603    |
    When I run jbom command "inventory-search inventory.csv --dry-run"
    Then the command should succeed
    And the output should contain "DRY RUN"
    And the output should contain "Searchable items: 2"

  Scenario: Missing inventory file
    When I run jbom command "inventory-search missing.csv --dry-run"
    Then the command should fail
    And the output should contain "Inventory file not found"
