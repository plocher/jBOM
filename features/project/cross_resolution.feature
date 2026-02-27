Feature: Cross-Resolution Project References

  Background:
    Given a jBOM CSV sandbox

  # Test commands that resolve from "wrong" file type to needed file type

  Scenario: BOM command given .kicad_pcb file finds matching schematic
    Given a KiCad project
    And a schematic that contains:
      | Reference | Value | Footprint     |
      | R1        | 10K   | R_0805_2012   |
    And a PCB that contains:
      | reference | x | y | rotation | side | footprint     |
      | R1        | 5 | 10| 0        | TOP  | R_0805_2012   |
    When I run jbom command "bom project.kicad_pcb"
    Then the command should succeed

  Scenario: POS command given .kicad_sch file finds matching PCB
    Given a KiCad project
    And the schematic "project" contains:
      | Reference | Value | Footprint     |
      | R1        | 10K   | R_0805_2012   |
    And a PCB that contains:
      | reference | x | y | rotation | side | footprint     |
      | R1        | 5 | 10| 0        | TOP  | R_0805_2012   |
    When I run jbom command "pos project.kicad_sch"
    Then the command should succeed

  # Edge cases - missing target files

  Scenario: BOM command given .kicad_pcb file fails when no matching schematic exists
    Given a KiCad project
    And the schematic is deleted
    And a PCB that contains:
      | reference | x | y | rotation | side | footprint     |
      | R1        | 5 | 10| 0        | TOP  | R_0805_2012   |
    When I run jbom command "bom project.kicad_pcb"
    Then the command should fail

  Scenario: POS command given .kicad_sch file fails when no matching PCB exists
    Given a KiCad project
    And the PCB is deleted
    And the schematic "project" contains:
      | Reference | Value | Footprint     |
      | R1        | 10K   | R_0805_2012   |
    When I run jbom command "pos project.kicad_sch"
    Then the command should fail
