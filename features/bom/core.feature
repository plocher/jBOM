Feature: BOM Generation (Core Functionality)
  As a hardware developer
  I want to generate a Bill of Materials from KiCad schematics
  So that I can order components and manufacture PCBs

  Background:
    Given the generic fabricator is selected
    And a schematic that contains:
      | Reference | Value | Footprint         |
      | R1        | 10K   | R_0805_2012       |
      | C1        | 100nF | C_0603_1608       |
      | U1        | LM358 | SOIC-8_3.9x4.9mm |

  Scenario: Generate basic BOM with console output (human-first)
    When I run jbom command "bom -o console"
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
    And a file named "custom_bom.csv" should exist

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

  Scenario: BOM list-fields reflects runtime source discovery and computed fields
    Given a schematic that contains:
      | Reference | Value | Footprint   | LCSC   |
      | R1        | 10K   | R_0805_2012 | C17414 |
    And a PCB that contains:
      | Reference | X | Y | Footprint   | Value |
      | R1        | 5 | 3 | R_0805_2012 | 9K99  |
    When I run jbom command "bom --list-fields"
    Then the command should succeed
    And the output should contain "Name"
    And the output should contain "s:"
    And the output should contain "p:"
    And the output should contain "i:"
    And the output should contain "s:value"
    And the output should contain "p:value"
    And the output should contain "s:lcsc"
    And the output should contain "quantity"
    And the output should not contain "a:"

  Scenario: BOM unqualified fields use PIS source priority
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
    And a PCB that contains:
      | Reference | X | Y | Footprint   | Value |
      | R1        | 5 | 3 | R_0805_2012 | 9K99  |
    When I run jbom command "bom -f reference,quantity,value,fabricator_part_number,s:value,p:value -o -"
    Then the command should succeed
    And the CSV output has rows where:
      | Reference | Value | S:Value | P:Value |
      | R1        | 9K99  | 10K     | 9K99    |
