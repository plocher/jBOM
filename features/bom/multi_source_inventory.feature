Feature: Multi-Source Inventory
  As a PCB designer
  I want to use multiple inventory sources simultaneously
  So that I can prefer local stock while falling back to supplier catalogs

  Background:
    Given a KiCad project named "SimpleProject"

  Scenario: Prefer local inventory over supplier inventory
    Given multiple inventory sources with priority differences
    Then the BOM prioritizes local inventory over supplier inventory

  Scenario: Load distributor export with local CSV
    Given a local inventory CSV and distributor export file
    Then the BOM combines components from both sources based on priority

  Scenario: Source tracking in verbose mode
    Given multiple inventory sources with 10K 0603 resistor
    Then the verbose BOM shows selected part source and available alternatives

  Scenario: Multi-source inventory via API
    Given multiple inventory sources with standard components
    Then the API generates BOM with source tracking for each matched item

  Scenario: Handle inventory source conflicts
    Given conflicting inventory sources with same IPN but different specs
    Then the BOM uses first source definition and warns about conflicts
