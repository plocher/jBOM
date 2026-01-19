Feature: BOM Generation
  As a hardware developer
  I want to generate a Bill of Materials from my KiCad schematic
  So that I can order components and manufacture my PCB

  Background:
    Given a clean test workspace

  Scenario: Generate basic BOM from schematic
    Given a KiCad schematic file "test_project.kicad_sch" with components:
      | Reference | Value | Footprint     |
      | R1        | 10K   | R_0805_2012   |
      | C1        | 100nF | C_0603_1608   |
      | U1        | LM358 | SOIC-8_3.9x4.9mm |
    When I run "jbom bom test_project.kicad_sch"
    Then the command exits with code 0
    And the output contains CSV headers "References,Value,Footprint,Quantity"
    And the output contains "R1,10K,R_0805_2012,1"
    And the output contains "C1,100nF,C_0603_1608,1"
    And the output contains "U1,LM358,SOIC-8_3.9x4.9mm,1"

  Scenario: Generate BOM to specific output file
    Given a KiCad schematic file "output_test.kicad_sch" with basic components
    When I run "jbom bom output_test.kicad_sch -o custom_bom.csv"
    Then the command exits with code 0
    And a file named "custom_bom.csv" exists
    And the file "custom_bom.csv" contains valid CSV data

  Scenario: Generate BOM with console output
    Given a KiCad schematic file "console_test.kicad_sch" with basic components
    When I run "jbom bom console_test.kicad_sch -o console"
    Then the command exits with code 0
    And the output contains a formatted table header
    And the output contains component references and values

  Scenario: Handle missing schematic file
    When I run "jbom bom nonexistent.kicad_sch"
    Then the command exits with code 1
    And the error output contains "Schematic file not found"

  Scenario: Handle invalid schematic file
    Given a file "invalid.txt" with content "This is not a schematic"
    When I run "jbom bom invalid.txt"
    Then the command exits with code 1
    And the error output contains "Expected .kicad_sch file"
