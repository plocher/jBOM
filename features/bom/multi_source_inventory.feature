Feature: Multi-Source Inventory
  As a PCB designer
  I want to use multiple inventory sources simultaneously
  So that I can prefer local stock while falling back to supplier catalogs

  Background:
    Given a KiCad project named "SimpleProject"

  Scenario: Prefer local inventory over supplier inventory
    Given multiple inventory sources
    And the schematic contains a 1K 0603 resistor and a 10K 0603 resistor
    When I run jbom command "bom SimpleProject -i local_inventory.csv -i supplier_inventory.csv -o federated_bom.csv"
    Then the command succeeds
    And file "federated_bom.csv" is created
    And the 1K resistor matches from local inventory with priority 1
    And the 10K resistor matches from supplier inventory with priority 2

  Scenario: Load distributor export with local CSV
    Given a local inventory CSV file
    And a distributor export file (e.g., JLC "My Parts Lib")
    When I run jbom command "bom SimpleProject -i local_inventory.csv -i distributor_export.xlsx -o combined_bom.csv"
    Then the command succeeds
    And file "combined_bom.csv" is created
    And components match from both sources based on priority

  Scenario: Source tracking in verbose mode
    Given multiple inventory sources
    And the schematic contains a 10K 0603 resistor
    When I run jbom command "bom SimpleProject -i local_inventory.csv -i supplier_inventory.csv -o verbose_bom.csv -v"
    Then the command succeeds
    And the verbose output shows the selected part source
    And the verbose output shows available alternatives from other sources

  Scenario: Multi-source inventory via Python API
    Given multiple inventory sources
    And the schematic contains standard components
    When I generate BOM using Python API with multiple inventory files
    Then the command succeeds
    And the API result contains components from all sources
    And the API result tracks source information for each matched item

  Scenario: Handle inventory source conflicts
    Given conflicting inventory sources with same IPN but different specs
    When I run jbom command "bom SimpleProject -i source1.csv -i source2.csv -o conflict_bom.csv"
    Then the command succeeds
    And the BOM uses the first source's definition for conflicting IPNs
    And the output contains a warning about inventory conflicts
