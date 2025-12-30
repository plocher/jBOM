Feature: Component Matching
  As a PCB designer
  I want jBOM to match schematic components against inventory items
  So that I can generate accurate BOMs with available parts

  Background:
    Given a KiCad project named "SimpleProject"
    And an inventory file with components
      | IPN   | Category | Value | Package | Distributor | DPN     | Priority |
      | R001  | RES      | 10K   | 0603    | JLC         | C25804  | 1        |
      | R002  | RES      | 1K    | 0603    | JLC         | C11702  | 1        |
      | C001  | CAP      | 100nF | 0603    | JLC         | C14663  | 1        |
      | C002  | CAP      | 10uF  | 0805    | JLC         | C15850  | 1        |

  Scenario: Match resistor by value and package
    Given the schematic contains a 10K 0603 resistor
    Then the BOM contains the 10K 0603 resistor matched to "R001"

  Scenario: Match capacitor by value and package
    Given the schematic contains a 100nF 0603 capacitor
    Then the BOM contains the 100nF 0603 capacitor matched to "C001"

  Scenario: No match for missing component
    Given the schematic contains a 47K 1206 resistor
    Then the BOM contains an unmatched component entry
