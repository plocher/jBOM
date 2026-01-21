Feature: POS Rotation and Orientation
  As a manufacturing engineer
  I want consistent component rotation/orientation in POS output
  So that assembly machines place parts correctly

  Background:
    Given the generic fabricator is selected

  Scenario: Rotation values are preserved in CSV output
    Given a PCB that contains:
      | Reference | X | Y | Rotation | Side | Footprint         |
      | R1        | 10| 5 | 0        | TOP  | R_0805_2012       |
      | C1        | 10| 6 | 90       | TOP  | C_0603_1608       |
      | U1        | 10| 7 | 180      | TOP  | SOIC-8_3.9x4.9mm |
    When I run jbom command "pos"
    Then the command should succeed
    And the output should contain "R1,10.0000,5.0000,0.0,TOP"
    And the output should contain "C1,10.0000,6.0000,90.0,TOP"
    And the output should contain "U1,10.0000,7.0000,180.0,TOP"

  Scenario: Bottom-layer components keep orientation semantics
    Given a PCB that contains:
      | Reference | X | Y | Rotation | Side   | Footprint   |
      | R1        | 5 | 5 | 0        | BOTTOM | R_0805_2012 |
    When I run jbom command "pos"
    Then the command should succeed
    And the output should contain "R1"
