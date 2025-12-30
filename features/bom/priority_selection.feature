Feature: Priority Selection
  As a PCB designer
  I want jBOM to select the lowest priority part when multiple inventory items match
  So that I get preferred parts (local stock, cost-effective options) in my BOM

  Background:
    Given a KiCad project named "SimpleProject"

  Scenario: Priority zero wins over all other priority values
    Given a schematic with components
      | Reference | Value | Package |
      | R1        | 10K   | 0603    |
    And an inventory with parts
      | IPN   | Category | Value | Package | Distributor | Priority |
      | R001  | RES      | 10K   | 0603    | JLC         | 0        |
      | R002  | RES      | 10K   | 0603    | JLC         | 1        |
      | R003  | RES      | 10K   | 0603    | JLC         | 5        |
    When I generate a BOM with fields "Reference,IPN,Priority" for priority validation
    Then the BOM contains R1 matched to R001 with priority 0
    And the BOM excludes R002 and R003 due to higher priority values

  Scenario: Priority handles 32-bit integer boundaries
    Given a schematic with components
      | Reference | Value | Package |
      | R1        | 10K   | 0603    |
    And an inventory with parts
      | IPN   | Category | Value | Package | Priority    |
      | R001  | RES      | 10K   | 0603    | 1           |
      | R002  | RES      | 10K   | 0603    | 2147483647  |
      | R003  | RES      | 10K   | 0603    | 4294967295  |
    When I generate a BOM with fields "Reference,IPN,Priority" for priority validation
    Then the BOM contains R1 matched to R001 with priority 1
    And the BOM excludes R002 and R003 due to higher priority values

  Scenario: Priority selection with non-sequential values
    Given a schematic with components
      | Reference | Value | Package |
      | R1        | 10K   | 0603    |
      | C1        | 100nF | 0603    |
    And an inventory with parts
      | IPN   | Category | Value | Package | Priority |
      | R001  | RES      | 10K   | 0603    | 50       |
      | R002  | RES      | 10K   | 0603    | 1        |
      | R003  | RES      | 10K   | 0603    | 100      |
      | C001  | CAP      | 100nF | 0603    | 2        |
      | C002  | CAP      | 100nF | 0603    | 0        |
    When I generate a BOM with fields "Reference,IPN,Priority" for priority validation
    Then the BOM contains R1 matched to R002 with priority 1
    And the BOM excludes R001 and R003 due to higher priority values
    And the BOM contains C1 matched to C002 with priority 0
    And the BOM excludes C001 due to higher priority value

  Scenario: Priority rejects malformed spreadsheet data
    Given a schematic with components
      | Reference | Value | Package |
      | R1        | 10K   | 0603    |
    And an inventory with invalid priority data
      | IPN   | Category | Value | Package | Priority |
      | R001  | RES      | 10K   | 0603    | "high"   |
      | R002  | RES      | 10K   | 0603    | ""       |
      | R003  | RES      | 10K   | 0603    | "#DIV/0!" |
    When I generate a BOM with fields "Reference,IPN,Priority" for priority validation
    Then the error reports invalid priority values for R001, R002, R003
    And the BOM generation fails with priority validation error
