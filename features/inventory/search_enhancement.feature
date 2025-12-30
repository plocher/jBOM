Feature: Search-Enhanced Inventory
  As a PCB designer
  I want to automatically enhance my inventory with distributor search results
  So that I can get part numbers, pricing, and availability without manual lookup

  Background:
    Given a KiCad project named "SimpleProject"
    And the MOUSER_API_KEY environment variable is set

  Scenario: Basic search-enhanced inventory generation
    Given the schematic contains standard components
    When I run jbom command "inventory SimpleProject --search --provider mouser --limit 1 -o enhanced_inventory.csv"
    Then the command succeeds
    And file "enhanced_inventory.csv" is created
    And the inventory includes distributor part numbers
    And the inventory includes pricing information
    And the inventory includes stock quantities

  Scenario: Multiple search results per component
    Given the schematic contains a 10K 0603 resistor
    When I run jbom command "inventory SimpleProject --search --limit 3 -o multi_result_inventory.csv"
    Then the command succeeds
    And file "multi_result_inventory.csv" is created
    And the inventory contains 3 candidate parts for the resistor
    And each candidate has priority ranking (1=best, 2=second, 3=third)
    And all candidates match the component specifications

  Scenario: Search enhancement with caching
    Given the schematic contains standard components
    When I run jbom command "inventory SimpleProject --search --limit 1 -o cached_inventory.csv"
    Then the command succeeds
    And file "cached_inventory.csv" is created

    When I run the same command again
    Then the command completes faster using cached results
    And both inventory files contain identical search results

  Scenario: Search enhancement via Python API
    Given the schematic contains standard components
    When I generate enhanced inventory using Python API with search enabled
    Then the command succeeds
    And the API result includes search statistics
    And the API result contains distributor-enhanced components
    And the API result tracks successful and failed searches

  Scenario: Handle search failures gracefully
    Given the schematic contains an exotic component
    And the component is unlikely to be found in distributor search
    When I run jbom command "inventory SimpleProject --search --limit 1 -o partial_inventory.csv"
    Then the command succeeds
    And file "partial_inventory.csv" is created
    And found components include distributor data
    And unfound components have empty distributor fields
    And the output reports search success statistics

  Scenario: Interactive search result selection
    Given the schematic contains components with multiple good matches
    When I run jbom command "inventory SimpleProject --search --interactive --limit 5 -o interactive_inventory.csv"
    Then the search presents multiple options for each component
    And I can select preferred parts interactively
    And the final inventory reflects my selections
    And the command succeeds with customized inventory
