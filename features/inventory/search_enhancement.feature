Feature: Search-Enhanced Inventory
  As a PCB designer
  I want to automatically enhance my inventory with distributor search results
  So that I can get part numbers, pricing, and availability without manual lookup

  Background:
    Given a KiCad project named "SimpleProject"
    And the MOUSER_API_KEY environment variable is set

  Scenario: Basic search-enhanced inventory generation
    Given the schematic contains standard components
    Then the search-enhanced inventory includes part numbers, pricing, and stock quantities

  Scenario: Multiple search results per component
    Given the schematic contains a 10K 0603 resistor
    Then the inventory contains 3 candidate parts with priority ranking

  Scenario: Search enhancement with caching
    Given the schematic contains standard components
    Then the search results are cached for faster subsequent runs

  Scenario: Search enhancement via API
    Given the schematic contains standard components
    Then the API generates enhanced inventory with search statistics and tracking

  Scenario: Handle search failures gracefully
    Given the schematic contains exotic components unlikely to be found
    Then the inventory includes distributor data for found components and reports search statistics

  Scenario: Interactive search result selection
    Given the schematic contains components with multiple good matches
    Then the search presents interactive options for customized inventory selection
