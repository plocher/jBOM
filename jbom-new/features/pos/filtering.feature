Feature: POS Filtering
  As a hardware developer
  I want to filter POS output by component properties
  So that I can generate exactly what my assembly needs

  Background:
    Given the generic fabricator is selected

  Scenario: SMD-only filtering
    Given a PCB that contains:
      | Reference | X | Y | Rotation | Side | Footprint        |
      | R1        | 10| 5 | 0        | TOP  | R_0805_2012      |
      | R2        | 15| 8 | 0        | TOP  | R_Axial_DIN0207  |
      | C1        | 20|12 | 0        | TOP  | C_0603_1608      |
    When I run jbom command "pos --smd-only -o -"
    Then the command should succeed
    And the output should contain "R1"
    And the output should contain "C1"
    And the output should not contain "R2"

  Scenario: Layer filter - TOP only
    Given a PCB that contains:
      | Reference | X | Y | Rotation | Side   | Footprint   |
      | R1        | 10| 5 | 0        | TOP    | R_0805_2012 |
      | R2        | 15| 8 | 0        | BOTTOM | R_0805_2012 |
      | C1        | 20|12 | 0        | TOP    | C_0603_1608 |
    When I run jbom command "pos --layer TOP -o -"
    Then the command should succeed
    And the output should contain "R1"
    And the output should contain "C1"
    And the output should not contain "R2"

  Scenario: Layer filter - BOTTOM only
    Given a PCB that contains:
      | Reference | X | Y | Side   | Footprint   |
      | R1        | 10| 5 | TOP    | R_0805_2012 |
      | R2        | 15| 8 | BOTTOM | R_0805_2012 |
      | C1        | 20|12 | TOP    | C_0603_1608 |
    When I run jbom command "pos --layer BOTTOM -o -"
    Then the command should succeed
    And the output should contain "R2"
    And the output should not contain "R1"
    And the output should not contain "C1"

  Scenario: Combined filters - SMD on TOP
    Given a PCB that contains:
      | Reference | X | Y | Side   | Footprint        |
      | R1        | 10| 5 | TOP    | R_0805_2012      |
      | R2        | 15| 8 | BOTTOM | R_0805_2012      |
      | R3        | 20|12 | TOP    | R_Axial_DIN0207  |
      | C1        | 25|15 | TOP    | C_0603_1608      |
    When I run jbom command "pos --smd-only --layer TOP -o -"
    Then the command should succeed
    And the output should contain "R1"
    And the output should contain "C1"
    And the output should not contain "R2"
    And the output should not contain "R3"

  # TODO: Should use --generic flag when Issue #26 (POS field selection) is implemented
  Scenario: Output in inches
    Given a PCB that contains:
      | Reference | X | Y | Side | Footprint   |
      | R1        | 10| 5 | TOP  | R_0805_2012 |
      | C1        | 15| 8 | TOP  | C_0603_1608 |
    When I run jbom command "pos --units inch -o -"
    Then the command should succeed
    And the output should contain "R1"
    And the output should contain "C1"

  Scenario: Use auxiliary origin
    Given a PCB that contains:
      | Reference | X | Y | Side | Footprint   |
      | R1        | 10| 5 | TOP  | R_0805_2012 |
      | C1        | 15| 8 | TOP  | C_0603_1608 |
    When I run jbom command "pos --origin aux -o -"
    Then the command should succeed
    And the output should contain "R1"
    And the output should contain "C1"
