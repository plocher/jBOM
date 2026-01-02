Feature: Search-Enhanced Inventory
  As a PCB designer
  I want to automatically enhance my inventory with distributor search results
  So that I can get part numbers, pricing, and availability without manual lookup

  Background:
    Given a KiCad project named "SimpleProject"

  Scenario: Basic search-enhanced inventory generation with Mouser API
    Given the "BasicComponents" schematic
    And the MOUSER_API_KEY environment variable is available for distributor search
    When I generate search-enhanced inventory with --generic fabricator
    Then the inventory includes Mouser part numbers, pricing, and stock quantities for each component

  Scenario: Multiple search results per component with priority ranking
    Given the "BasicComponents" schematic
    And the MOUSER_API_KEY environment variable is available for distributor search
    When I search with --generic fabricator and result limit of 3
    Then the inventory contains 3 candidate parts for the 10K resistor with priority ranking based on price and availability

  Scenario: Search enhancement with caching optimization
    Given the "BasicComponents" schematic
    And the MOUSER_API_KEY environment variable is available for distributor search
    When I generate search-enhanced inventory with --generic fabricator the first time
    And the MOUSER_API_KEY is set to NULL
    And I generate search-enhanced inventory with --generic fabricator a second time
    Then the second run uses cached results, does not generate API errors and completes successfully

  Scenario: Search enhancement with statistics reporting
    Given the "BasicComponents" schematic
    And the MOUSER_API_KEY environment variable is available for distributor search
    When I generate enhanced inventory with --generic fabricator
    Then the search returns statistics showing queries made and success rate

  Scenario: Handle search failures gracefully with edge cases
    Given a schematic with mixed searchable and exotic components:
      | Reference | Value    | Footprint   | Searchability |
      | R1        | 10K      | R_0603_1608 | Common        |
      | U1        | XYZ-9999 | QFN-64      | Exotic        |
    And the MOUSER_API_KEY environment variable is available for distributor search
    When I generate search-enhanced inventory with --generic fabricator
    Then the inventory includes Mouser data for R1 and reports "no results found" for exotic U1 component

  Scenario: Interactive search result selection workflow
    Given the "BasicComponents" schematic
    And the MOUSER_API_KEY environment variable is available for distributor search
    And search returns multiple good matches for components
    When I enable interactive selection mode with --generic fabricator
    Then the search presents multiple part options with prices for user selection per component
