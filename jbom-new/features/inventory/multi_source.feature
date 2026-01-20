Feature: Multi-Source Inventory
  As a sourcing engineer
  I want to combine multiple inventory sources
  So that the best available part data is used in the BOM

  Background:
    Given a clean test workspace

  # Combine two inventory files and enhance BOM
  @wip
  Scenario: Merge two inventory files when enhancing BOM
    Given a KiCad schematic file "merge_test.kicad_sch" with components:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | C1        | 100nF | C_0603_1608 |
    And an inventory file "inv_primary.csv" with data:
      | IPN      | Category  | Value | Description | Package | Manufacturer | MFGPN    |
      | RES_10K  | RESISTOR  | 10K   | 10K Res     | 0805    | Yageo        | RC0805-10K |
    And an inventory file "inv_secondary.csv" with data:
      | IPN       | Category  | Value  | Description     | Package | Manufacturer | MFGPN     |
      | CAP_100N  | CAPACITOR | 100nF  | 100nF Ceramic   | 0603    | Samsung      | CL10B104  |
    When I run "jbom bom merge_test.kicad_sch --inventory inv_primary.csv --inventory inv_secondary.csv"
    Then the command exits with code 0
    And the output contains "Inventory enhanced"  # informational summary

  # Precedence: primary overrides secondary when conflicting
  @wip
  Scenario: Primary inventory takes precedence on conflicts
    Given a KiCad schematic file "precedence.kicad_sch" with components:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
    And an inventory file "inv_primary.csv" with data:
      | IPN      | Category  | Value | Description | Package | Manufacturer | MFGPN     |
      | RES_10K  | RESISTOR  | 10K   | Primary     | 0805    | Yageo        | RC0805-10K |
    And an inventory file "inv_secondary.csv" with data:
      | IPN      | Category  | Value | Description | Package | Manufacturer | MFGPN     |
      | RES_10K  | RESISTOR  | 10K   | Secondary   | 0805    | Other        | RC0805-10K |
    When I run "jbom bom precedence.kicad_sch --inventory inv_primary.csv --inventory inv_secondary.csv"
    Then the command exits with code 0
    And the output contains "Primary"  # derived from primary inventory row
