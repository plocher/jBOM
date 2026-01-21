Feature: Cross-command intelligence between schematic and PCB

  # No external fixtures. We construct minimal inputs inline for clarity.

  Scenario: BOM given a PCB path resolves the matching schematic
    Given the schematic "beta" contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0603_1608 |
    And I create file "beta.kicad_pcb" with content "(kicad_pcb (version 20211014))"
    When I run jbom command "bom beta.kicad_pcb -o console -v"
    Then the command should succeed
    And the error output should mention "found matching schematic beta.kicad_sch"

  Scenario: POS given a schematic path in a hierarchical project resolves the PCB
    Given the project uses a root schematic "main" that contains:
      | Reference | Value | Footprint |
    And the root references child schematic "hier"
    And the child schematic "hier" contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0603_1608 |
    And I create file "hier.kicad_pcb" with content "(kicad_pcb (version 20211014))"
    When I run jbom command "pos main.kicad_sch -o console -v"
    Then the command should succeed
    And the error output should mention "found matching PCB hier.kicad_pcb"
