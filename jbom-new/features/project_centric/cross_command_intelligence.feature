Feature: Cross-command intelligence between schematic and PCB

  # No external fixtures. We construct minimal inputs inline for clarity.

  Scenario: BOM given a PCB path resolves the matching schematic
    Given the schematic "beta" contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0603_1608 |
    And I create file "beta.kicad_pcb" with content "(kicad_pcb (version 20211014))"
    When I run jbom command "bom beta.kicad_pcb -o console -v"
    Then the command should succeed
    And the output should contain "Loading components from beta.kicad_sch"

  Scenario: POS given a schematic path resolves to matching PCB
    Given a KiCad project directory "foo"
    And the project contains a file "foo.kicad_pro"
    And the project contains a file "foo.kicad_sch" with basic schematic content
    And a PCB that contains:
      | Reference | X | Y | Rotation |
      | R1        | 5 | 10| 0        |
    When I run jbom command "pos foo.kicad_sch -o -"
    Then the command should succeed
    And the output should contain "R1,5,10,TOP,0"
