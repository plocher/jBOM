Feature: POS Rotation and Orientation
  As a manufacturing engineer
  I want consistent component rotation/orientation in POS output
  So that assembly machines place parts correctly

  Background:
    Given a clean test workspace

  Scenario: Rotation values are preserved in CSV output
    Given a KiCad PCB file "rotations.kicad_pcb" with components:
      | Reference | X(mm) | Y(mm) | Rotation | Side | Footprint   |
      | R1        | 10.0  | 5.0   | 0        | TOP  | R_0805_2012 |
      | C1        | 10.0  | 6.0   | 90       | TOP  | C_0603_1608 |
      | U1        | 10.0  | 7.0   | 180      | TOP  | SOIC-8_3.9x4.9mm |
    When I run "jbom pos rotations.kicad_pcb"
    Then the command exits with code 0
    And the output contains "R1,10.0000,5.0000,0.0,TOP"
    And the output contains "C1,10.0000,6.0000,90.0,TOP"
    And the output contains "U1,10.0000,7.0000,180.0,TOP"

  Scenario: Bottom-layer components keep orientation semantics
    Given a KiCad PCB file "bottom.kicad_pcb" with components:
      | Reference | X(mm) | Y(mm) | Rotation | Side   | Footprint   |
      | R1        | 5.0   | 5.0   | 0        | BOTTOM | R_0805_2012 |
    When I run "jbom pos bottom.kicad_pcb"
    Then the command exits with code 0
    And the output contains "R1"
