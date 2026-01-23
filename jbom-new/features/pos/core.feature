Feature: POS Generation (Core Functionality)
  As a hardware developer
  I want to generate component placement files from KiCad PCBs
  So that I can provide placement data to assembly services

  Background:
    Given the generic fabricator is selected

  Scenario: Generate basic POS with default console output (human-first)
    Given a PCB that contains:
      | Reference | X | Y | Rotation | Side | Footprint         |
      | R1        | 10| 5 | 0        | TOP  | R_0805_2012       |
      | C1        | 15| 8 | 90       | TOP  | C_0603_1608       |
      | U1        | 25|12 | 180      | TOP  | SOIC-8_3.9x4.9mm |
    When I run jbom command "pos"
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
    And the output should contain "10.0000,5.0000"
    And the output should contain "C1"
    And the output should contain "15.0000,8.0000"
    And the output should contain "U1"
    And the output should contain "25.0000,12.0000"

  Scenario: Generate POS to specific output file
    Given a PCB that contains:
      | Reference | X | Y | Side | Footprint   |
      | R1        | 5 | 3 | TOP  | R_0805_2012 |
      | C1        | 8 | 6 | TOP  | C_0603_1608 |
    When I run jbom command "pos -o placement.csv"
    Then the command should succeed
    And a file named "custom_pos.csv" should exist

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
