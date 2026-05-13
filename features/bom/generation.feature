Feature: BOM Generation
  As a hardware developer
  I want to generate a Bill of Materials from my KiCad schematic
  So that I can order components and manufacture my PCB

  Background:
    Given the generic fabricator is selected

  Scenario: Generate basic BOM to stdout (human-readable format)
    Given a PCB that contains:
      | Reference | Value | Footprint     |
      | R1        | 10K   | R_0805_2012   |
      | C1        | 100nF | C_0603_1608   |
      | U1        | LM358 | SOIC-8_3.9x4.9mm |
    When I run jbom command "bom -o console"
    Then the command should succeed
    And the output should contain "Bill of Materials"
    And the output should contain "R1"
    And the output should contain "10K"
    And the output should contain "C1"
    And the output should contain "100nF"
    And the output should contain "U1"
    And the output should contain "LM358"

  Scenario: Generate BOM to specific output file
    Given a PCB that contains:
      | Reference | Value | Footprint     |
      | R1        | 10K   | R_0805_2012   |
    When I run jbom command "bom -o custom_bom.csv"
    Then the command should succeed
    And a file named "custom_bom.csv" should exist

  Scenario: Generate BOM with console output
    Given a PCB that contains:
      | Reference | Value | Footprint     |
      | R1        | 10K   | R_0805_2012   |
    When I run jbom command "bom -o console"
    Then the command should succeed
    And the output should contain "Bill of Materials"
    And the output should contain "R1"

  Scenario: Handle missing project (no PCB file resolves)
    When I run jbom command "bom nonexistent.kicad_pcb"
    Then the command should fail
    And the error output should mention "No PCB file found"

  Scenario: Handle invalid input that resolves to no PCB
    Given I create file "invalid.txt" with content "This is not a KiCad file"
    When I run jbom command "bom invalid.txt"
    Then the command should fail
    And the error output should mention "No PCB file found"
