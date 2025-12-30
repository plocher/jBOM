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

  Scenario Outline: Component matching across usage models
    Given the schematic contains a <component>
    When I generate BOM using <method>
    Then the command succeeds
    And a BOM file is generated
    And the BOM contains the <component> matched to "<expected_match>"

    Examples: Resistor matching
      | method     | component        | expected_match |
      | CLI        | 10K 0603 resistor| R001           |
      | Python API | 10K 0603 resistor| R001           |
      | KiCad plugin| 10K 0603 resistor| R001           |

    Examples: Capacitor matching
      | method     | component           | expected_match |
      | CLI        | 100nF 0603 capacitor| C001           |
      | Python API | 100nF 0603 capacitor| C001           |
      | KiCad plugin| 100nF 0603 capacitor| C001           |

  Scenario Outline: Unmatched components across usage models
    Given the schematic contains a <component>
    When I generate BOM using <method>
    Then the command succeeds
    And the BOM contains an unmatched component entry

    Examples:
      | method      | component        |
      | CLI         | 47K 1206 resistor|
      | Python API  | 47K 1206 resistor|
      | KiCad plugin| 47K 1206 resistor|

  Scenario: Comprehensive multi-modal validation
    Given the schematic contains standard components
    When I validate behavior across all usage models
    Then all usage models produce consistent results
    And each method successfully generates a BOM file
