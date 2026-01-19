Feature: POS Filtering Options
  As a hardware developer
  I want to filter POS output by component properties
  So that I can generate placement files for specific assembly requirements

  Scenario: Filter SMD components only
    Given a KiCad PCB file "mixed_components.kicad_pcb" with components:
      | Reference | X(mm) | Y(mm) | Mount Type | Side | Footprint    |
      | R1        | 10.0  | 5.0   | smd        | TOP  | R_0805_2012  |
      | R2        | 15.0  | 8.0   | through    | TOP  | R_Axial_DIN0207 |
      | C1        | 20.0  | 12.0  | smd        | TOP  | C_0603_1608  |
    When I run "jbom pos mixed_components.kicad_pcb --smd-only"
    Then the command exits with code 0
    And the output contains "R1"
    And the output contains "C1"
    And the output does not contain "R2"

  Scenario: Filter by layer - TOP only
    Given a KiCad PCB file "dual_side.kicad_pcb" with components:
      | Reference | X(mm) | Y(mm) | Side   | Footprint   |
      | R1        | 10.0  | 5.0   | TOP    | R_0805_2012 |
      | R2        | 15.0  | 8.0   | BOTTOM | R_0805_2012 |
      | C1        | 20.0  | 12.0  | TOP    | C_0603_1608 |
    When I run "jbom pos dual_side.kicad_pcb --layer TOP"
    Then the command exits with code 0
    And the output contains "R1"
    And the output contains "C1"
    And the output does not contain "R2"

  Scenario: Filter by layer - BOTTOM only
    Given a KiCad PCB file "dual_side.kicad_pcb" with TOP and BOTTOM components
    When I run "jbom pos dual_side.kicad_pcb --layer BOTTOM"
    Then the command exits with code 0
    And the output contains only BOTTOM side components

  Scenario: Combined filtering - SMD and TOP layer
    Given a KiCad PCB file "complex.kicad_pcb" with mixed components and sides
    When I run "jbom pos complex.kicad_pcb --smd-only --layer TOP"
    Then the command exits with code 0
    And the output contains only SMD components on TOP layer

  Scenario: Output in inches
    Given a KiCad PCB file "units_test.kicad_pcb" with components
    When I run "jbom pos units_test.kicad_pcb --units inch"
    Then the command exits with code 0
    And the output contains CSV headers "Reference,X(in),Y(in),Rotation"
    And the coordinate values are in inches

  Scenario: Use auxiliary origin
    Given a KiCad PCB file "origin_test.kicad_pcb" with auxiliary origin set
    When I run "jbom pos origin_test.kicad_pcb --origin aux"
    Then the command exits with code 0
    And the coordinates are relative to auxiliary origin

  Scenario: Verbose output with filtering
    Given a KiCad PCB file "verbose_test.kicad_pcb" with mixed components
    When I run "jbom pos verbose_test.kicad_pcb --smd-only -v"
    Then the command exits with code 0
    And the output contains verbose filtering information
