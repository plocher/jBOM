Feature: Output Format Consistency
  As a PCB designer
  I want console and CSV outputs to use the same field names for the same fabricator
  So that my workflow is consistent regardless of output format

  Background:
    Given a KiCad project named "OutputTest"
    And the project uses a schematic named "TestBoard"
    And the "TestBoard" schematic contains components:
      | Reference | Value | Footprint    | LibID     |
      | R1        | 10K   | R_0603_1608  | Device:R  |
      | R2        | 10K   | R_0603_1608  | Device:R  |
      | C1        | 100nF | C_0603_1608  | Device:C  |
    And an inventory file with components:
      | IPN   | Category | Value | Package | Distributor | DPN    | MPN            | Manufacturer | Description      | Footprint    | Priority |
      | R001  | RES      | 10K   | 0603    | LCSC        | C25804 | RC0603FR-0710K | YAGEO        | 10K 0603 Resistor| R_0603_1608  | 1        |
      | C001  | CAP      | 100nF | 0603    | LCSC        | C14663 | CC0603KRX7R9BB | YAGEO        | 100nF 0603 Cap   | C_0603_1608  | 1        |

  @wip
  Scenario: Console and CSV outputs use identical field names with JLC fabricator
    When I generate a BOM with --jlc fabricator to console output
    And I generate a BOM with --jlc fabricator to CSV output
    Then the console output contains column headers matching JLC configuration:
      | Designator | Quantity | Value | Comment | Footprint | LCSC | Surface Mount |
    And the CSV output contains column headers matching JLC configuration:
      | Designator | Quantity | Value | Comment | Footprint | LCSC | Surface Mount |
    And the console field names match the CSV field names exactly

  @wip
  Scenario: Console and CSV outputs use identical field names with default fabricator
    When I generate a BOM with --generic fabricator to console output
    And I generate a BOM with --generic fabricator to CSV output
    Then the console output contains column headers matching generic configuration
    And the CSV output contains column headers matching generic configuration
    And the console field names match the CSV field names exactly

  @wip
  Scenario: Console and CSV outputs use identical field names with PCBWay fabricator
    When I generate a BOM with --pcbway fabricator to console output
    And I generate a BOM with --pcbway fabricator to CSV output
    Then the console output contains column headers matching PCBWay configuration
    And the CSV output contains column headers matching PCBWay configuration
    And the console field names match the CSV field names exactly

  @wip
  Scenario: Console and CSV outputs use identical field names with Seeed fabricator
    When I generate a BOM with --seeed fabricator to console output
    And I generate a BOM with --seeed fabricator to CSV output
    Then the console output contains column headers matching Seeed configuration
    And the CSV output contains column headers matching Seeed configuration
    And the console field names match the CSV field names exactly

  @wip
  Scenario: Field name consistency with custom field selection
    When I generate a BOM with --generic fabricator and custom fields "reference,value,lcsc,manufacturer" to console output
    And I generate a BOM with --generic fabricator and custom fields "reference,value,lcsc,manufacturer" to CSV output
    Then the console output contains exactly 4 columns
    And the CSV output contains exactly 4 columns
    And the console field names match the CSV field names exactly

  @wip
  Scenario: Console output respects fabricator column mappings for JLC
    When I generate a BOM with --jlc fabricator to console output
    Then the console output uses "Designator" instead of "Reference"
    And the console output uses "Quantity" instead of "Qty"
    And the console output uses "Comment" for component description
    And the console output uses "Surface Mount" instead of "SMD"

  @wip
  Scenario: Legacy console behavior when no fabricator specified
    When I generate a BOM to console output without fabricator flag
    Then the console output uses standard field names
    And the console output includes "Reference" column
    And the console output includes "Quantity" column
    And the console output includes "Description" column

  @wip
  Scenario: Notes column appears consistently in console and CSV
    Given the "TestBoard" schematic contains a resistor with tolerance mismatch
    When I generate a BOM with --jlc fabricator to console output
    And I generate a BOM with --jlc fabricator to CSV output
    Then the console output contains "Notes" column
    And the CSV output contains "Notes" column
    And the Notes column contains warning messages in both outputs
