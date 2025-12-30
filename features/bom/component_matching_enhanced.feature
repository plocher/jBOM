Feature: Component Matching (Axiom #18 Enhanced)
  As a PCB designer
  I want jBOM to match schematic components against inventory items
  So that I can generate accurate BOMs with predictable, testable behavior

  Background: Base Test Data Foundation
    Given a clean test environment
    And a KiCad project named "SimpleProject"
    And a base inventory with standard components:
      | IPN   | Category | Value | Package | Distributor | DPN     | Priority |
      | R001  | RES      | 10K   | 0603    | Generic     | G25804  | 1        |
      | R002  | RES      | 1K1   | 0603    | Generic     | G11702  | 1        |
      | C001  | CAP      | 100nF | 0603    | Generic     | G14663  | 1        |
      | C002  | CAP      | 10uF  | 0805    | Generic     | G15850  | 1        |

  Scenario: Match resistor by exact value and package
    Given the schematic is extended with component:
      | Reference | Value | Package |
      | R1        | 10K   | 0603    |
    When I generate a BOM with --generic fabricator
    Then the BOM contains a matched resistor with value "10K" and package "0603" from the inventory

  Scenario: Match by tolerance with explicit inventory state (Axiom #17 + #18)
    Given the schematic is extended with component:
      | Reference | Value | Package |
      | R1        | 1K    | 0603    |
    And the inventory excludes exact match for "1K 0603 resistor"
    And the inventory includes tolerance match "1K1 0603 resistor"
    When I generate a BOM with --generic fabricator
    Then the BOM contains a matched resistor with inventory value "1K1" and package "0603"
    And the match is based on component value tolerance

  Scenario: No match with dynamic negative inventory
    Given the schematic is extended with component:
      | Reference | Value | Package |
      | R1        | 47K   | 1206    |
    And the inventory excludes all components matching:
      | Exclusion Type | Pattern    |
      | Value          | 47K        |
      | Package        | 1206       |
    When I generate a BOM with --generic fabricator
    Then the BOM contains an unmatched component entry

  Scenario: Complex tolerance scenario with builder pattern
    Given the schematic is extended with components:
      | Reference | Value | Package |
      | R1        | 1K    | 0603    |
      | R2        | 1.1K  | 0603    |
      | R3        | 1000  | 0603    |
    And the inventory is modified to include tolerance variants:
      | IPN   | Category | Value | Package | Tolerance | Priority |
      | R003  | RES      | 1K1   | 0603    | 5%        | 1        |
      | R004  | RES      | 1K0   | 0603    | 1%        | 2        |
    And the inventory excludes exact matches for "1K, 1.1K, 1000 ohm 0603 resistors"
    When I generate a BOM with --generic fabricator
    Then all 3 resistors match to available tolerance variants
    And R1, R2, R3 all use the lowest priority tolerance match
