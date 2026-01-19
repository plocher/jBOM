Feature: BOM Generation and Output
  As a hardware developer
  I want to generate Bills of Materials from KiCad schematics
  So that I can source and manufacture PCBs reliably

  Background:
    Given a clean test workspace
    And a KiCad schematic file "project.kicad_sch" with components:
      | Reference | Value | Footprint         |
      | R1        | 10K   | R_0805_2012       |
      | C1        | 100nF | C_0603_1608       |
      | U1        | LM358 | SOIC-8_3.9x4.9mm |

  Scenario: CSV to stdout with default options
    When I run "jbom bom project.kicad_sch"
    Then the command exits with code 0
    And the output contains CSV headers "References,Value,Footprint,Quantity"
    And the output contains "R1,10K"
    And the output contains "C1,100nF"
    And the output contains "U1,LM358"

  Scenario: Aggregation by value and footprint
    Given a KiCad schematic file "aggregation.kicad_sch" with components:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | R2        | 10K   | R_0805_2012 |
      | R3        | 10K   | R_0603_1608 |
    When I run "jbom bom aggregation.kicad_sch --aggregation value_footprint"
    Then the command exits with code 0
    And the output contains "\"R1, R2\",10K,R_0805_2012,2"
    And the output contains "R3,10K,R_0603_1608,1"

  Scenario: Aggregation by value only
    Given a KiCad schematic file "value_only.kicad_sch" with components:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | R2        | 10K   | R_0603_1608 |
    When I run "jbom bom value_only.kicad_sch --aggregation value_only"
    Then the command exits with code 0
    And the output contains "\"R1, R2\",10K"
    And the line count is 2

  Scenario: Include DNP components when requested
    Given a KiCad schematic file "dnp_include.kicad_sch" with DNP components
    When I run "jbom bom dnp_include.kicad_sch --include-dnp"
    Then the command exits with code 0
    And the output contains "R2,22K"

  Scenario: Exclude DNP components by default
    Given a KiCad schematic file "dnp_exclude.kicad_sch" with DNP components
    When I run "jbom bom dnp_exclude.kicad_sch"
    Then the command exits with code 0
    And the output does not contain "R2"

  Scenario: Include components excluded from BOM when requested
    Given a KiCad schematic file "excluded.kicad_sch" with components excluded from BOM
    When I run "jbom bom excluded.kicad_sch --include-excluded"
    Then the command exits with code 0
    And the output contains excluded component references

  Scenario: Console output formatting
    Given a KiCad schematic file "console.kicad_sch" with basic components
    When I run "jbom bom console.kicad_sch -o console"
    Then the command exits with code 0
    And the output contains a formatted table header
    And the output contains component references and values

  Scenario: Help command
    When I run "jbom bom --help"
    Then the command exits with code 0
    And the output contains "--aggregation"
    And the output contains "--inventory"
    And the output contains "--include-dnp"

  Scenario: Error on missing schematic file
    When I run "jbom bom missing_file.kicad_sch"
    Then the command exits with code 1
    And the error output contains "Schematic file not found"
