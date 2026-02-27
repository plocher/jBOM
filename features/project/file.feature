Feature: File-based Project References

  Background:
    Given a jBOM CSV sandbox

  # Systematic combinatorics: Test all valid KiCad project combinations
  # (.kicad_pro always present, .kicad_sch and .kicad_pcb optional)

  # BOM command with different file types

  Scenario: BOM command given .kicad_pro file with schematic present
    Given a schematic that contains:
      | Reference | Value | Footprint     |
      | R1        | 10K   | R_0805_2012   |
    When I run jbom command "bom project.kicad_pro"
    Then the command should succeed

  Scenario: BOM command given .kicad_sch file
    Given a schematic that contains:
      | Reference | Value | Footprint     |
      | R1        | 10K   | R_0805_2012   |
    When I run jbom command "bom project.kicad_sch"
    Then the command should succeed

  Scenario: BOM command given .kicad_pro file with no schematic fails
    Given a KiCad project
    And the schematic is deleted
    When I run jbom command "bom project.kicad_pro"
    Then the command should fail

  Scenario: BOM command given .kicad_pro file with PCB-only project fails
    Given a KiCad project
    And the schematic is deleted
    When I run jbom command "bom project.kicad_pro"
    Then the command should fail

  # POS command with different file types

  Scenario: POS command given .kicad_pro file with PCB present
    Given a PCB that contains:
      | reference | x | y | rotation | side | footprint     |
      | R1        | 5 | 10| 0        | TOP  | R_0805_2012   |
    When I run jbom command "pos project.kicad_pro"
    Then the command should succeed

  Scenario: POS command given .kicad_pcb file
    Given a PCB that contains:
      | reference | x | y | rotation | side | footprint     |
      | R1        | 5 | 10| 0        | TOP  | R_0805_2012   |
    When I run jbom command "pos project.kicad_pcb"
    Then the command should succeed

  Scenario: POS command given .kicad_pro file with no PCB fails
    Given a KiCad project
    And the PCB is deleted
    When I run jbom command "pos project.kicad_pro"
    Then the command should fail

  Scenario: POS command given .kicad_pro file with schematic-only project fails
    Given a KiCad project
    And the PCB is deleted
    When I run jbom command "pos project.kicad_pro"
    Then the command should fail

  # Inventory command with different file types

  Scenario: Inventory command given .kicad_pro file with schematic present
    Given a schematic that contains:
      | Reference | Value | Footprint     |
      | R1        | 10K   | R_0805_2012   |
    When I run jbom command "inventory project.kicad_pro"
    Then the command should succeed

  Scenario: Inventory command given .kicad_sch file
    Given a schematic that contains:
      | Reference | Value | Footprint     |
      | R1        | 10K   | R_0805_2012   |
    When I run jbom command "inventory project.kicad_sch"
    Then the command should succeed

  Scenario: Inventory command given .kicad_pro file with no schematic fails
    Given a KiCad project
    And the schematic is deleted
    When I run jbom command "inventory project.kicad_pro"
    Then the command should fail

  Scenario: Inventory command given .kicad_pro file with PCB-only project fails
    Given a KiCad project
    And the PCB is deleted
    When I run jbom command "inventory project.kicad_pro"
    Then the command should fail

  # Edge case

  Scenario: Command given nonexistent file fails
    When I run jbom command "bom nonexistent_file.kicad_sch"
    Then the command should fail
