Feature: Component Matching (Axiom #17 Corrected)
  As a PCB designer
  I want jBOM to match schematic components against inventory items with explicit preconditions
  So that I can generate accurate BOMs with predictable, testable behavior

  Background:
    Given a KiCad project named "SimpleProject"
    And an inventory file with components
      | IPN   | Category | Value | Package | Distributor | DPN     | Priority |
      | R001  | RES      | 10K   | 0603    | Generic     | G25804  | 1        |
      | R002  | RES      | 1K1   | 0603    | Generic     | G11702  | 1        |
      | C001  | CAP      | 100nF | 0603    | Generic     | G14663  | 1        |
      | C002  | CAP      | 10uF  | 0805    | Generic     | G15850  | 1        |

  Scenario: Match resistor by exact value and package
    Given the schematic contains a 10K 0603 resistor
    And the generic inventory contains a 10K 0603 resistor
    When I generate a BOM with --generic fabricator
    Then the BOM contains a matched resistor with value "10K" and package "0603" from the inventory

  Scenario: Match component by approximate value within tolerance range (CORRECTED per Axiom #17)
    Given the schematic contains a 1K 0603 resistor
    And the generic inventory contains a 1k1 0603 resistor
    And the inventory does not contain a 1k 0603 resistor
    When I generate a BOM with --generic fabricator
    Then the BOM contains a matched resistor with inventory value "1K1" and package "0603"
    And the match uses component value tolerance

  Scenario: Match component by normalized value format (CORRECTED per Axiom #17)
    Given the schematic contains a 1.1K 0603 resistor
    And the generic inventory contains a 1k1 0603 resistor
    And the inventory does not contain a 1.1k 0603 resistor
    When I generate a BOM with --generic fabricator
    Then the BOM contains a matched resistor with inventory value "1K1" and package "0603"
    And the match uses value normalization

  Scenario: No match for missing component - explicit absence of all fields (CORRECTED per Axiom #17)
    Given the schematic contains a 47K 1206 resistor
    And the inventory does not contain any 47K resistors
    And the inventory does not contain any 1206 package components
    When I generate a BOM with --generic fabricator
    Then the BOM contains an unmatched component entry

  Scenario: No match for missing component - value matches, package explicitly absent (CORRECTED per Axiom #17)
    Given the schematic contains a 10K 1206 resistor
    And the generic inventory contains a 10K 0603 resistor
    And the inventory does not contain a 10K 1206 resistor
    When I generate a BOM with --generic fabricator
    Then the BOM contains an unmatched component entry

  Scenario: No match for missing component - package matches, value explicitly absent (CORRECTED per Axiom #17)
    Given the schematic contains a 100K 0603 resistor
    And the generic inventory contains a 10K 0603 resistor
    And the inventory does not contain any 100K resistors
    When I generate a BOM with --generic fabricator
    Then the BOM contains an unmatched component entry
