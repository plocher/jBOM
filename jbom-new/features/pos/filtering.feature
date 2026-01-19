Feature: POS Filtering
  As a hardware developer
  I want to filter POS output by component properties
  So that I can generate exactly what my assembly needs

  Background:
    Given a clean test workspace

  Scenario: SMD-only filtering
    Given a KiCad PCB file "mixed.kicad_pcb" with components:
      | Reference | X(mm) | Y(mm) | Rotation | Side | Footprint        | Mount Type |
      | R1        | 10.0  | 5.0   | 0        | TOP  | R_0805_2012      | smd        |
      | R2        | 15.0  | 8.0   | 0        | TOP  | R_Axial_DIN0207  | through    |
      | C1        | 20.0  | 12.0  | 0        | TOP  | C_0603_1608      | smd        |
    When I run "jbom pos mixed.kicad_pcb --smd-only"
    Then the command exits with code 0
    And the output contains "R1"
    And the output contains "C1"
    And the output does not contain "R2"

  Scenario: Layer filter - TOP only
    Given a KiCad PCB file "dual_side.kicad_pcb" with components:
      | Reference | X(mm) | Y(mm) | Rotation | Side   | Footprint   |
      | R1        | 10.0  | 5.0   | 0        | TOP    | R_0805_2012 |
      | R2        | 15.0  | 8.0   | 0        | BOTTOM | R_0805_2012 |
      | C1        | 20.0  | 12.0  | 0        | TOP    | C_0603_1608 |
    When I run "jbom pos dual_side.kicad_pcb --layer TOP"
    Then the command exits with code 0
    And the output contains "R1"
    And the output contains "C1"
    And the output does not contain "R2"

  Scenario: Layer filter - BOTTOM only
    Given a KiCad PCB file "dual_side.kicad_pcb" with TOP and BOTTOM components
    When I run "jbom pos dual_side.kicad_pcb --layer BOTTOM"
    Then the command exits with code 0
    And the output contains only BOTTOM side components

  Scenario: Combined filters - SMD on TOP
    Given a KiCad PCB file "complex.kicad_pcb" with mixed components and sides
    When I run "jbom pos complex.kicad_pcb --smd-only --layer TOP"
    Then the command exits with code 0
    And the output contains only SMD components on TOP layer
