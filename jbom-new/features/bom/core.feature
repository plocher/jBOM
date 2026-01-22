Feature: BOM Generation (Core Functionality)
  As a hardware developer
  I want to generate a Bill of Materials from KiCad schematics
  So that I can order components and manufacture PCBs

  Background:
    Given the generic fabricator is selected
    And a standard test schematic that contains:
      | Reference | Value | Footprint         |
      | R1        | 10K   | R_0805_2012       |
      | C1        | 100nF | C_0603_1608       |
      | U1        | LM358 | SOIC-8_3.9x4.9mm |

  Scenario: Generate basic BOM with default console output (human-first)
    When I run jbom command "bom"
    Then the command should succeed
    And the output should contain "R1"
    And the output should contain "10K"
    And the output should contain "C1"
    And the output should contain "100nF"
    And the output should contain "U1"
    And the output should contain "LM358"

  Scenario: Generate BOM to specific output file
    When I run jbom command "bom -o custom_bom.csv"
    Then the command should succeed
    And a file named "custom_bom.csv" exists

  Scenario: Generate BOM with explicit console table output
    When I run jbom command "bom -o console"
    Then the command should succeed
    And the output should contain "Bill of Materials"
    And the output should contain "R1"
    And the output should contain "C1"

  Scenario: Handle empty schematic
    Given a schematic that contains:
      | Reference | Value | Footprint |
    When I run jbom command "bom -o console"
    Then the command should succeed
    And the output should contain "No components found"
