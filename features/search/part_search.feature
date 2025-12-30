Feature: Part Search
  As a PCB designer
  I want to search for electronic components from distributors
  So that I can find suitable parts for my inventory and design

  Background:
    Given the MOUSER_API_KEY environment variable is set

  Scenario: Basic part search
    Given I need to find a 10K 0603 resistor
    Then the search returns up to 5 matching parts ranked by relevance

  Scenario: Search with specific provider
    Given I want to search specifically on Mouser for 100nF ceramic capacitor
    Then the search uses Mouser API with part numbers, pricing, and stock availability

  Scenario: Search part number directly
    Given I know manufacturer part number "RC0603FR-0710KL"
    Then the search finds exact manufacturer part with cross-references and pricing

  Scenario: Search with parametric filtering
    Given I need 10K resistors with 1% tolerance in 0603 package
    Then the search filters results for 1% tolerance and 0603 package excluding inappropriate matches

  Scenario: Handle search failures gracefully
    Given I search for non-existent part "nonexistent-part-xyz123"
    Then the search returns no results with appropriate messaging without errors

  Scenario: Search via API
    Given I want to search programmatically
    Then the API returns SearchResult objects with filterable part information

  Scenario: Search with API key override
    Given I have different API key "MY_TEST_KEY" for 1uF capacitor search
    Then the search uses specified API key and returns results normally
