Feature: UX messaging and verbosity controls

  Background:
    Given the sample fixtures under "features/project_centric/fixtures/kicad_samples"

  Scenario: Verbose mode reports action and success
    When I run jbom command "bom features/project_centric/fixtures/kicad_samples/flat_project -o console -v"
    Then the command should succeed
    And the error output should mention "found project flat_project"
    And the error output should mention "found schematic flat.kicad_sch"

  Scenario: Quiet mode suppresses remediation messages
    When I run jbom command "bom features/project_centric/fixtures/kicad_samples/flat_project -o console -q"
    Then the command should succeed
    And the error output should be empty

  Scenario: Helpful failure suggestions for empty directory
    Given an empty directory "features/project_centric/fixtures/empty_dir2"
    When I run jbom command "bom features/project_centric/fixtures/empty_dir2 -o console"
    Then the command should fail
    And the error output should contain "No project files found"
    And the error output should contain "Add <name>.kicad_pro or <name>.kicad_sch or <name>.kicad_pcb"
