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
    When I run jbom command "pos -o -"
    Then the command should succeed
    And the output should contain "R1,10,5,TOP,0,0805"
    And the output should contain "C1,10,6,TOP,90,0603"
    And the output should contain "U1,10,7,TOP,180,SOIC"

  Scenario: Bottom-layer components keep orientation semantics
    Given a PCB that contains:
      | Reference | X | Y | Rotation | Side   | Footprint   |
      | R1        | 5 | 5 | 0        | BOTTOM | R_0805_2012 |
    When I run jbom command "pos -o console"
    Then the command should succeed
    And the output should contain "R1"

  Scenario: JLC fabricator folds out-of-range rotation into [0, 360)
    Given a PCB that contains:
      | Reference | X | Y | Rotation | Side | Footprint   |
      | R1        | 10| 5 | -90      | TOP  | R_0805_2012 |
    When I run jbom command "pos --jlc -o -"
    Then the command should succeed
    # JLC cpl_rotation_range: [0, 360] -> (-90 - 0) % 360 + 0 = 270
    And the CSV output has rows where:
      | Designator | Rotation |
      | R1         | 270.0    |

  Scenario: Generic fabricator preserves raw negative rotation unchanged
    Given a PCB that contains:
      | Reference | X | Y | Rotation | Side | Footprint   |
      | R1        | 10| 5 | -90      | TOP  | R_0805_2012 |
    When I run jbom command "pos -o -"
    Then the command should succeed
    # Generic has no cpl_rotation_range -> rotation_raw passed through as-is
    And the CSV output has rows where:
      | Designator | Rotation |
      | R1         | -90      |

  Scenario: DB corrections and JLC range folding both apply in sequence
    Given a PCB that contains:
      | Reference | X | Y | Rotation | Side | Footprint          |
      | U1        | 10| 5 | 0        | TOP  | SOIC127P798X216-8N |
    When I run jbom command "pos --apply-corrections --jlc -o -"
    Then the command should succeed
    # Part 1 (DB): SOIC127P798X216-8N -> '^SOIC127P798X216-8N' -> -90 deg delta -> 0 + (-90) = -90
    # Part 2 (JLC fold): (-90 - 0) % 360 + 0 = 270
    And the CSV output has rows where:
      | Designator | Rotation |
      | U1         | 270.0    |
