Feature: BOM Generation - Basic Command Execution
  As a hardware developer
  I want to generate a Bill of Materials from my KiCad schematic
  So that I can order components and manufacture my PCB

  Scenario: Generate BOM with default behavior
    Given a clean test environment
    And a KiCad project named "BasicProject"
    And the schematic is populated with basic components:
      | Reference | Value | Footprint |
      | R1        | 10K   | R_0805    |
      | C1        | 100nF | C_0603    |
    When I run "jbom bom --fabricator generic" in the project directory
    Then the command exits with code 0
    And a file named "BasicProject.bom.csv" exists in the project directory
    And the BOM contains the expected components

  Scenario: Generate BOM to specific output file
    Given a clean test environment
    And a KiCad project named "OutputProject"
    And the schematic is populated with basic components:
      | Reference | Value | Footprint |
      | R1        | 1K    | R_0805    |
    When I run "jbom bom --fabricator generic -o custom_bom.csv" in the project directory
    Then the command exits with code 0
    And a file named "custom_bom.csv" exists in the project directory

  Scenario: Generate BOM to stdout
    Given a clean test environment
    And a KiCad project named "StdoutProject"
    And the schematic is populated with basic components:
      | Reference | Value | Footprint |
      | R1        | 2K2   | R_0805    |
    When I run "jbom bom --fabricator generic --stdout" in the project directory
    Then the command exits with code 0
    And stdout contains CSV formatted BOM data
