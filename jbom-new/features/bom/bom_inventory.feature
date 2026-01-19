Feature: BOM Inventory Enhancement
  As a hardware developer
  I want to enhance my BOM with inventory information
  So that I can see part numbers, descriptions, and availability

  Background:
    Given a clean test workspace
    And a KiCad schematic file "project.kicad_sch" with components:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | C1        | 100nF | C_0603_1608 |

  Scenario: Enhance BOM with inventory data
    Given an inventory file "components.csv" with data:
      | IPN     | Category  | Value | Package | Manufacturer | MFGPN           | LCSC   |
      | RES_10K | RESISTOR  | 10K   | 0805    | Yageo        | RC0805FR-0710KL | C17414 |
      | CAP_100N| CAPACITOR | 100nF | 0603    | Samsung      | CL10B104KB8NNNC | C1591  |
    When I run "jbom bom project.kicad_sch --inventory components.csv --generic"
    Then the command exits with code 0
    And the output contains inventory enhancement columns
    And the output contains inventory data for matched components

  Scenario: Handle missing inventory file
    Given a KiCad schematic file "test.kicad_sch" with basic components
    When I run "jbom bom test.kicad_sch --inventory missing.csv --generic"
    Then the command exits with code 1
    And the error output contains "Inventory file not found"

  @wip
  Scenario: BOM with partial inventory matches
    Given a KiCad schematic file "partial_test.kicad_sch" with components:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | R2        | 22K   | R_0805_2012 |
    And an inventory file "partial.csv" with only R1 data
    When I run "jbom bom partial_test.kicad_sch --inventory partial.csv -o console --generic"
    Then the command exits with code 0
    And the output contains "Inventory enhanced: 1/2 items matched"

  Scenario: Enhanced BOM to file output
    Given a KiCad schematic file "file_test.kicad_sch" with basic components
    And an inventory file "inventory.csv" with matching data
    When I run "jbom bom file_test.kicad_sch --inventory inventory.csv -o enhanced_bom.csv --generic"
    Then the command exits with code 0
    And a file named "enhanced_bom.csv" exists
    And the file "enhanced_bom.csv" contains inventory columns
