Feature: POS Generation (Core Functionality)
  As a hardware developer
  I want to generate component placement files from KiCad PCBs
  So that I can provide placement data to assembly services

  Background:
    Given the generic fabricator is selected

  Scenario: Default output writes a project-named CSV file
    Given a PCB that contains:
      | Reference | X | Y | Rotation | Side | Footprint         |
      | R1        | 10| 5 | 0        | TOP  | R_0805_2012       |
      | C1        | 15| 8 | 90       | TOP  | C_0603_1608       |
      | U1        | 25|12 | 180      | TOP  | SOIC-8_3.9x4.9mm |
    When I run jbom command "pos"
    Then the command should succeed
    And a file named "project.pos.csv" should exist
    And the file "project.pos.csv" should contain "R1"

  Scenario: Generate basic POS with console output (human-first)
    Given a PCB that contains:
      | Reference | X | Y | Rotation | Side | Footprint         |
      | R1        | 10| 5 | 0        | TOP  | R_0805_2012       |
      | C1        | 15| 8 | 90       | TOP  | C_0603_1608       |
      | U1        | 25|12 | 180      | TOP  | SOIC-8_3.9x4.9mm |
    When I run jbom command "pos -o console"
    Then the command should succeed
    And the output should contain "Component Placement Data"
    And the output should contain "R1"
    And the output should contain "C1"
    And the output should contain "U1"

  Scenario: Generate POS to CSV stdout with -o -
    Given a PCB that contains:
      | Reference | X | Y | Rotation | Side | Footprint         |
      | R1        | 10| 5 | 0        | TOP  | R_0805_2012       |
      | C1        | 15| 8 | 90       | TOP  | C_0603_1608       |
      | U1        | 25|12 | 180      | TOP  | SOIC-8_3.9x4.9mm |
    When I run jbom command "pos -o -"
    Then the command should succeed
    And the output should contain "R1"
    And the output should contain "10,5"
    And the output should contain "C1"
    And the output should contain "15,8"
    And the output should contain "U1"
    And the output should contain "25,12"

  Scenario: Generate POS to specific output file
    Given a PCB that contains:
      | Reference | X | Y | Side | Footprint   |
      | R1        | 5 | 3 | TOP  | R_0805_2012 |
      | C1        | 8 | 6 | TOP  | C_0603_1608 |
    When I run jbom command "pos -o placement.csv"
    Then the command should succeed
    And a file named "placement.csv" should exist

  Scenario: Generate POS with console table output
    Given a PCB that contains:
      | Reference | X | Y | Side | Footprint   |
      | R1        | 5 | 3 | TOP  | R_0805_2012 |
      | C1        | 8 | 6 | TOP  | C_0603_1608 |
    When I run jbom command "pos -o console"
    Then the command should succeed
    And the output should contain "Component Placement Data"
    And the output should contain "R1"
    And the output should contain "C1"

  Scenario: Handle empty PCB
    Given a PCB that contains:
      | Reference | X | Y | Side | Footprint |
    When I run jbom command "pos -o console"
    Then the command should succeed
    And the output should contain "No components found"

  Scenario: POS unqualified fields use PIS source priority
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
    And a PCB that contains:
      | Reference | X | Y | Side | Footprint   | Value |
      | R1        | 5 | 3 | TOP  | R_0805_2012 | 9K99  |
    When I run jbom command "pos -f reference,value,s:value,p:value -o -"
    Then the command should succeed
    And the CSV output has rows where:
      | Reference | Value | S:Value | P:Value |
      | R1        | 9K99  | 10K     | 9K99    |

  Scenario: POS list-fields excludes annotation namespace column
    When I run jbom command "pos --list-fields"
    Then the command should succeed
    And the output should contain "Known POS fields"
    And the output should contain "s:"
    And the output should contain "p:"
    And the output should contain "i:"
    And the output should not contain "a:"
