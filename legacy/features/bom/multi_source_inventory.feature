Feature: Multi-Source Inventory
  As a PCB designer
  I want to use multiple inventory files simultaneously
  So that I can combine different fabricator inventories or organize parts across multiple files

  Background:
    Given a KiCad project named "SimpleProject"

  Scenario: Combine multiple inventory files
    Given the "BasicComponents" schematic
    And the "PrimaryStock" inventory
    And the "SecondaryStock" inventory
    When I generate a BOM with --generic fabricator and both inventory files
    Then the BOM combines parts from both inventory sources
    And component matches use parts from either inventory file

  Scenario: Priority-based part selection across inventory files
    Given the "BasicComponents" schematic
    And the "PriorityTest" inventory
    When I generate a BOM with --generic fabricator
    Then the BOM selects parts with the lowest priority value among all matching candidates
    And part selection considers priority across all inventory sources

  Scenario: Track inventory source in BOM output
    Given the "BasicComponents" schematic
    And the "MultipleSuppliers" inventory
    When I generate a BOM with --generic fabricator and source tracking enabled
    Then the BOM shows selected parts with their inventory source file
    And alternative parts from other sources are listed as options

  Scenario: Handle multi-source inventory through different interfaces
    Given the "BasicComponents" schematic
    And the "PrimaryStock" inventory
    And the "SecondaryStock" inventory
    When I validate behavior across all usage models
    Then all usage models produce consistent BOM results with multi-source inventory

  Scenario: Handle conflicting inventory data gracefully
    Given the "BasicComponents" schematic
    And the "ConflictingData" inventory
    When I generate a BOM with --generic fabricator
    Then the BOM uses the first valid part definition encountered
    And the BOM generation warns about any conflicting part specifications
