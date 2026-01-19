Feature: BOM Generation
  As a hardware developer
  I want to generate a BOM from KiCad schematics
  So that I can source and manufacture PCBs

  Background:
    Given a clean test workspace
    And a KiCad schematic file "project.kicad_sch" with components:
      | Reference | Value | Footprint         |
      | R1        | 10K   | R_0805_2012       |
      | C1        | 100nF | C_0603_1608       |
      | U1        | LM358 | SOIC-8_3.9x4.9mm |

  Scenario: CSV to stdout with default options
    When I run "jbom bom project.kicad_sch --generic"
    Then the command exits with code 0
    And the output contains CSV headers "References,Value,Footprint,Quantity"
    And the output contains "R1,10K"
    And the output contains "C1,100nF"
    And the output contains "U1,LM358"
