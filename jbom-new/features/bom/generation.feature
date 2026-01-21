Feature: BOM Generation
  As a hardware developer
  I want to generate a Bill of Materials from my KiCad schematic
  So that I can order components and manufacture my PCB

  Background:
    Given the generic fabricator is selected

  Scenario: Generate basic BOM to stdout
    Given a schematic that contains:
      | Reference | Value | Footprint     |
      | R1        | 10K   | R_0805_2012   |
      | C1        | 100nF | C_0603_1608   |
      | U1        | LM358 | SOIC-8_3.9x4.9mm |
    When I run jbom command "bom"
    Then the command should succeed
    And the output should contain "References,Value,Footprint,Quantity"
    And the output should contain "R1,10K,R_0805_2012,1"
    And the output should contain "C1,100nF,C_0603_1608,1"
    And the output should contain "U1,LM358,SOIC-8_3.9x4.9mm,1"

  Scenario: Generate BOM to specific output file
    Given a schematic that contains:
      | Reference | Value | Footprint     |
      | R1        | 10K   | R_0805_2012   |
    When I run jbom command "bom -o custom_bom.csv"
    Then the command should succeed
    And a file named "custom_bom.csv" exists

  Scenario: Generate BOM with console output
    Given a schematic that contains:
      | Reference | Value | Footprint     |
      | R1        | 10K   | R_0805_2012   |
    When I run jbom command "bom -o console"
    Then the command should succeed
    And the output should contain "Bill of Materials"
    And the output should contain "R1"

  Scenario: Handle missing schematic file
    When I run jbom command "bom nonexistent.kicad_sch"
    Then the command should fail
    And the error output should mention "Schematic file not found"

  Scenario: Handle invalid schematic file
    Given a file "invalid.txt" with content "This is not a schematic"
    When I run jbom command "bom invalid.txt"
    Then the command should fail
    And the error output should mention "Expected .kicad_sch file"
