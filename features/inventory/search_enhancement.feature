Feature: Search-Enhanced Inventory
  As a PCB designer
  I want to automatically enhance my inventory with distributor search results
  So that I can get part numbers, pricing, and availability without manual lookup

  Background:
    Given a KiCad project named "SimpleProject"
    And the MOUSER_API_KEY environment variable is set

  Scenario: Basic search-enhanced inventory generation
    Given the schematic contains components
      | Reference | Value | Footprint     |
      | R1        | 10K   | R_0603_1608   |
      | C1        | 100nF | C_0603_1608   |
    When I generate search-enhanced inventory
    Then the inventory includes Mouser part numbers, pricing, and stock quantities for each component

  Scenario: Multiple search results per component
    Given the schematic contains components
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0603_1608 |
    When I search with result limit of 3
    Then the inventory contains 3 candidate parts for the 10K resistor with priority ranking based on price and availability

  Scenario: Search enhancement with caching
    Given the schematic contains components
      | Reference | Value | Footprint     |
      | R1        | 10K   | R_0603_1608   |
      | C1        | 100nF | C_0603_1608   |
    When I generate search-enhanced inventory twice
    Then the second run uses cached results and completes faster than the first run

  Scenario: Search enhancement via API
    Given the schematic contains components
      | Reference | Value | Footprint     |
      | R1        | 10K   | R_0603_1608   |
      | C1        | 100nF | C_0603_1608   |
    When I use the API to generate enhanced inventory
    Then the API returns SearchEnhancedResult with search statistics showing queries made and success rate

  Scenario: Handle search failures gracefully
    Given the schematic contains components
      | Reference | Value    | Footprint   |
      | R1        | 10K      | R_0603_1608 |
      | U1        | XYZ-9999 | QFN-64      |
    When I generate search-enhanced inventory
    Then the inventory includes Mouser data for R1 and reports "no results found" for exotic U1 component

  Scenario: Interactive search result selection
    Given the schematic contains components
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0603_1608 |
    And search returns multiple good matches for the resistor
    When I enable interactive selection mode
    Then the search presents multiple part options with prices for user selection per component
