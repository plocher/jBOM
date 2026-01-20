Feature: Cross-command intelligence between schematic and PCB

  Background:
    Given the sample fixtures under "features/fixtures/kicad_samples"

  Scenario: BOM given PCB in mismatched_names resolves schematic and confirms
    When I run jbom command "bom features/fixtures/kicad_samples/mismatched_names/beta.kicad_pcb -o console -v"
    Then the command should succeed
    And the error output should mention "found matching schematic beta.kicad_sch"

  Scenario: POS given schematic in hier_project resolves PCB and confirms
    When I run jbom command "pos features/fixtures/kicad_samples/hier_project/main.kicad_sch -o console -v"
    Then the command should succeed
    And the error output should mention "found matching PCB hier.kicad_pcb"
    And the error output should mention "Processing hierarchical design"
