Feature: Part Search
  As a PCB designer
  I want to search for electronic components from distributors
  So that I can find suitable parts for my inventory and design

  Background:
    Given the MOUSER_API_KEY environment variable is set

  Scenario: Basic part search
    Given I need to find a 10K 0603 resistor
    When I run jbom command "search '10k 0603 resistor' --limit 5"
    Then the command succeeds
    And the search returns up to 5 matching parts
    And each result includes part number, manufacturer, and description
    And the results are ranked by relevance

  Scenario: Search with specific provider
    Given I want to search specifically on Mouser
    When I run jbom command "search '100nF ceramic capacitor' --provider mouser --limit 3"
    Then the command succeeds
    And the search uses Mouser's API
    And the results include Mouser part numbers and pricing
    And stock availability is included when available

  Scenario: Search part number directly
    Given I know a specific manufacturer part number
    When I run jbom command "search 'RC0603FR-0710KL' --limit 1"
    Then the command succeeds
    And the search finds the exact manufacturer part
    And the result includes cross-references and distributors
    And pricing and stock information is provided

  Scenario: Search with parametric filtering
    Given I need resistors with specific specifications
    When I run jbom command "search '10k resistor 1% 0603' --limit 10"
    Then the command succeeds
    And the results are filtered for 1% tolerance
    And the results are filtered for 0603 package size
    And the results exclude inappropriate matches (wrong tolerance/package)

  Scenario: Handle search failures gracefully
    Given I search for a non-existent part
    When I run jbom command "search 'nonexistent-part-xyz123' --limit 5"
    Then the command succeeds
    And the search returns no results
    And the output indicates no matches were found
    And the command does not fail with an error

  Scenario: Search via Python API
    Given I want to search programmatically
    When I perform part search using Python API
    Then the search succeeds
    And the API returns SearchResult objects
    And the results include all relevant part information
    And the results can be filtered and processed programmatically

  Scenario: Search with API key override
    Given I have a different API key for testing
    When I run jbom command "search '1uF capacitor' --api-key MY_TEST_KEY --limit 2"
    Then the command uses the specified API key
    And the search executes with the override key
    And the results are returned normally
