Feature: Project-centric discovery and resolution

  Background:
    Given the sample fixtures under "features/fixtures/kicad_samples"

  Scenario: Project base name in parent directory resolves correctly
    Given I am in directory "features/fixtures/kicad_samples"
    When I run jbom command "bom flat_project -o console -v"
    Then the command should succeed
    And the error output should mention "found project flat_project"
    And the error output should mention "found schematic flat.kicad_sch"

  Scenario: Directory with multiple schematics prefers the one matching project base
    When I run jbom command "bom features/fixtures/kicad_samples/mismatched_names -o console -v"
    Then the command should succeed
    And the error output should mention "found project alpha"
    And the error output should mention "found matching schematic beta.kicad_sch"

  Scenario: Only PCB present suggests schematic when missing
    Given an empty directory "features/fixtures/tmp_only_pcb"
    And I create file "features/fixtures/tmp_only_pcb/board.kicad_pcb" with content "(kicad_pcb (version 20211014))"
    When I run jbom command "bom features/fixtures/tmp_only_pcb -o console -v"
    Then the command should fail
    And the error output should contain "No project files found"
    And the error output should contain "Add <name>.kicad_sch"

  Scenario: Only schematic present suggests PCB when missing
    Given an empty directory "features/fixtures/tmp_only_sch"
    And I create file "features/fixtures/tmp_only_sch/board.kicad_sch" with content "(kicad_sch (version 20211123))"
    When I run jbom command "pos features/fixtures/tmp_only_sch -o console -v"
    Then the command should fail
    And the error output should contain "Add <name>.kicad_pcb"
