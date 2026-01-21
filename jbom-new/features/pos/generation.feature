Feature: POS Generation
  As a hardware developer
  I want to generate component placement files from my KiCad PCB
  So that I can provide placement data to assembly services

  Background:
    Given the generic fabricator is selected

  Scenario: Generate basic POS from PCB
    Given a PCB that contains:
      | Reference | X | Y | Rotation | Side | Footprint         |
      | R1        | 10| 5 | 0        | TOP  | R_0805_2012       |
      | C1        | 15| 8 | 90       | TOP  | C_0603_1608       |
      | U1        | 25|12 | 180      | TOP  | SOIC-8_3.9x4.9mm |
    When I run jbom command "pos -o -"
    Then the command should succeed
    And the output should contain "R1,10.0000,5.0000,0.0,TOP"
    And the output should contain "C1,15.0000,8.0000,90.0,TOP"
    And the output should contain "U1,25.0000,12.0000,180.0,TOP"

  Scenario: Generate POS to specific output file
    Given a PCB that contains:
      | Reference | X | Y | Side | Footprint   |
      | R1        | 10| 5 | TOP  | R_0805_2012 |
      | C1        | 15| 8 | TOP  | C_0603_1608 |
    When I run jbom command "pos -o placement.csv"
    Then the command should succeed
    And a file named "placement.csv" should exist
    And the file "placement.csv" should contain "R1"
    And the file "placement.csv" should contain "C1"

  Scenario: Generate POS with console output
    Given a PCB that contains:
      | Reference | X | Y | Side | Footprint   |
      | R1        | 10| 5 | TOP  | R_0805_2012 |
      | C1        | 15| 8 | TOP  | C_0603_1608 |
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
    And the output should contain "No components found."
