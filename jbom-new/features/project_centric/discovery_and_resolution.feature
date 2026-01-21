Feature: Project-centric discovery and resolution

Scenario: Project base name in parent directory resolves correctly
    Given a project "flat" placed in "flat_project"
    And the schematic "flat" contains:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10K   | R_0603_1608 | Device:R |
    And print diagnostics
    When I run jbom command "bom flat_project -o console"
    And print diagnostics
    Then the command should succeed
    And the output should contain "R1"

Scenario: Project in target directory with dot path
    Given a project named "flat"
    And the schematic "flat" contains:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10K   | R_0603_1608 | Device:R |
    And print diagnostics
    When I run jbom command "bom . -o console"
    And print diagnostics
    Then the command should succeed
    And the output should contain "R1"

Scenario: Project and directory share the same name (pedantic)
    Given a project "flat_project" placed in "flat_project"
    And the schematic "flat_project" contains:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10K   | R_0603_1608 | Device:R |
    And print diagnostics
    When I run jbom command "bom flat_project -o console"
    And print diagnostics
    Then the command should succeed
    And the output should contain "R1"
    Given a directory "flat_project"
    And a project named "flat"
    And the project uses a root schematic "flat" that contains:
      | Reference | Value | Footprint             | LibID    |
      | R1        | 10K   | R_0603_1608           | Device:R |
    When I run jbom command "bom . -o console"
    Then the command should succeed
    And the output should contain "R1"

  Scenario: Directory with multiple schematics picks a deterministic file
    Given I create directory "mismatched_names"
    And I am in directory "mismatched_names"
    And the schematic "alpha" contains:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10K   | R_0603_1608 | Device:R |
    And the schematic "beta" contains:
      | Reference | Value | Footprint   | LibID    |
      | C1        | 100nF | C_0603_1608 | Device:C |
    When I run jbom command "bom . -o console -v"
    Then the command should succeed
    # Deterministic pick: sorted order selects alpha here
    And the output should contain "alpha - Bill of Materials"

  Scenario: Only PCB present suggests schematic when missing
    Given an empty directory "features/project_centric/fixtures/tmp_only_pcb"
    And I create file "features/project_centric/fixtures/tmp_only_pcb/board.kicad_pcb" with content "(kicad_pcb (version 20211014))"
    When I run jbom command "bom features/project_centric/fixtures/tmp_only_pcb -o console -v"
    Then the command should fail
    And the output should contain "No schematic file found"

  Scenario: Only schematic present suggests PCB when missing
    Given an empty directory "features/project_centric/fixtures/tmp_only_sch"
    And I create file "features/project_centric/fixtures/tmp_only_sch/board.kicad_sch" with content "(kicad_sch (version 20211123))"
    When I run jbom command "pos features/project_centric/fixtures/tmp_only_sch -o console -v"
    Then the command should fail
    And the output should contain "No PCB file found"
