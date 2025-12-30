Feature: Multi-Source Inventory
  As a PCB designer
  I want to use multiple inventory files simultaneously
  So that I can combine different fabricator inventories or organize parts across multiple files

  Background:
    Given a KiCad project named "SimpleProject"

  Scenario: JLC fabricator filtering with multiple inventory files
    Given the "BasicComponents" schematic
    And the "JLC_Basic" inventory
    And the "LocalStock" inventory
    When I generate a JLC BOM with fields "Reference,Value,Package,Distributor,DPN" and both inventory files
    Then the BOM contains only parts where Distributor equals JLC from either inventory file

  Scenario: Priority selection within same fabricator across multiple files
    Given the "BasicComponents" schematic
    And the "PriorityTest" inventory
    When I generate a JLC BOM with fields "Reference,IPN,Priority,Distributor"
    Then the BOM selects the part with the lowest priority value among all matching candidates for same fabricator

  Scenario: Source tracking in verbose mode
    Given the "BasicComponents" schematic
    And the "MixedFabricators" inventory
    When I generate a verbose JLC BOM with fields "Reference,IPN,Distributor,Alternatives"
    Then the BOM shows JLC parts selected with LOCAL and SEEED parts listed as incompatible alternatives

  Scenario: Multi-source inventory via API
    Given the "BasicComponents" schematic
    And the "JLC_Basic" inventory
    And the "LocalStock" inventory
    When I use the API to generate JLC BOM with fields "Reference,IPN,Distributor,Source" and both inventory files
    Then the API returns BOM entries showing only JLC-compatible parts with source file tracking

  Scenario: Handle inventory source conflicts
    Given the "BasicComponents" schematic
    And the "ConflictingIPNs" inventory
    When I generate a BOM with fields "Reference,IPN,Conflicts" and conflicting inventory data
    Then the BOM uses first definition encountered and warns about conflicting specifications
