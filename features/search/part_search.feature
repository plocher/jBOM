Feature: Part Search
  As a PCB designer
  I want to search for electronic components from distributors
  So that I can find suitable parts for my inventory and design

  Background:
    Given the MOUSER_API_KEY environment variable is set

  Scenario: Basic part search
    Given I search for "10K 0603 resistor"
    When I execute the search with limit 5
    Then the search returns up to 5 matching resistor parts with part numbers, descriptions, and prices ranked by relevance

  Scenario: Search with specific provider
    Given I search for "100nF ceramic capacitor" on Mouser
    When I execute the provider-specific search
    Then the search uses Mouser API and returns capacitor results with manufacturer, part numbers, pricing, and stock availability

  Scenario: Search part number directly
    Given I search for manufacturer part number "RC0603FR-0710KL"
    When I execute the exact part number search
    Then the search finds the exact YAGEO 10K resistor with cross-references, pricing, and distributor availability

  Scenario: Search with parametric filtering
    Given I search for "10K resistor" with parameters:
      | Parameter | Value |
      | Tolerance | 1%    |
      | Package   | 0603  |
    When I execute the parametric search
    Then the search returns only 10K resistors with 1% tolerance in 0603 package excluding other tolerances and packages

  Scenario: Handle search failures gracefully
    Given I search for "nonexistent-part-xyz123"
    When I execute the search
    Then the search returns empty results with message "No parts found matching search criteria" and exit code 0

  Scenario: Search via API
    Given I use the search API to find "1uF ceramic capacitor"
    When I call the API search method
    Then the API returns SearchResult objects with part_number, manufacturer, description, price, and stock_quantity fields

  Scenario: Search with API key override
    Given I have custom API key "MY_TEST_KEY"
    When I search for "1uF capacitor" using the custom API key
    Then the search uses MY_TEST_KEY for authentication and returns capacitor results normally
