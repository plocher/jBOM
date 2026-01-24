Feature: BOM Fabricator Compatibility
  As a hardware developer
  I want BOMs to work with different PCB fabricators
  So that I can use the same design with multiple suppliers

  Background:
    Given the generic fabricator is selected
    And a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | C1        | 100nF | C_0603_1608 |

  Scenario: BOM generation works with all configured fabricators
    When I run jbom command "bom"
    Then the BOM works with all configured fabricators

  Scenario: All configured fabricators work without errors
    When I run jbom command "bom"
    Then the BOM works with all configured fabricators
