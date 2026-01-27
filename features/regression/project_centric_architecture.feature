Feature: TDD Regression - Project-Centric Architecture (Issue #24)
  As a developer implementing Issue #24
  I want to define the expected project-centric behavior
  So that I can follow proper TDD methodology (RED → GREEN → REFACTOR)

  # These scenarios would FAIL with the original file-centric implementation
  # but PASS when the project-centric architecture is properly implemented.

  # ORIGINAL BEHAVIOR: Commands required explicit file paths
  # NEW BEHAVIOR: Commands accept project directories and base names

  Background:
    Given a test workspace
    And a KiCad project directory "test_project"
    And the project contains a file "test_project.kicad_pro" with content:
      """
      (kicad_project (version 1))
      """
    And the project contains a schematic "test_project.kicad_sch" with components:
      | reference | value | footprint                       |
      | R1        | 10k   | Resistor_SMD:R_0603_1608Metric |
    And the project contains a PCB "test_project.kicad_pcb" with footprints:
      | reference | x     | y      | footprint                       |
      | R1        | 76.2  | 104.14 | Resistor_SMD:R_0603_1608Metric |

  @regression @project-centric @bom
  Scenario: BOM command should work with current directory
    # ORIGINAL: jbom bom . → ERROR (requires explicit .kicad_sch path)
    # EXPECTED: jbom bom . → SUCCESS (discovers schematic automatically)

    When I am in project directory "test_project"
    And I run jbom command "bom . -o console"
    Then the command should succeed
    And the BOM output should contain component "R1" with value "10k"
    And the BOM title should show project name "test_project"

  @regression @project-centric @bom
  Scenario: BOM command should work with project directory path
    # ORIGINAL: jbom bom /path/to/project → ERROR (requires explicit .kicad_sch path)
    # EXPECTED: jbom bom /path/to/project → SUCCESS (discovers schematic in directory)

    When I run jbom command "bom test_project -o console"
    Then the command should succeed
    And the BOM output should contain component "R1" with value "10k"
    And the BOM title should show project name "test_project"

  @regression @project-centric @bom
  Scenario: BOM command should work with base name resolution
    # ORIGINAL: jbom bom project_name → ERROR (no base name resolution)
    # EXPECTED: jbom bom project_name → SUCCESS (resolves to project_name.kicad_sch)

    When I run jbom command "bom test_project -o console"
    Then the command should succeed
    And the BOM output should contain component "R1" with value "10k"

  @regression @project-centric @pos
  Scenario: POS command should work with current directory
    # ORIGINAL: jbom pos . → ERROR (requires explicit .kicad_pcb path)
    # EXPECTED: jbom pos . → SUCCESS (discovers PCB automatically)

    When I am in project directory "test_project"
    And I run jbom command "pos . -o console"
    Then the command should succeed
    And the POS output should contain component "R1" at position "76.2" x "104.14" y

  @regression @project-centric @pos
  Scenario: POS command should work with project directory path
    # ORIGINAL: jbom pos /path/to/project → ERROR (requires explicit .kicad_pcb path)
    # EXPECTED: jbom pos /path/to/project → SUCCESS (discovers PCB in directory)

    When I run jbom command "pos test_project -o console"
    Then the command should succeed
    And the POS output should contain component "R1" at position "76.2" x "104.14" y

  @regression @project-centric @inventory
  Scenario: Inventory generate should work with current directory
    # ORIGINAL: jbom inventory generate . → ERROR (requires explicit .kicad_sch path)
    # EXPECTED: jbom inventory generate . → SUCCESS (discovers schematic automatically)

    When I am in project directory "test_project"
    And I run jbom command "inventory generate . -o test_inventory.csv"
    Then the command should succeed
    And the inventory file should contain component with value "10k"

  @regression @cross-command @bom
  Scenario: BOM command should handle PCB file input intelligently
    # ORIGINAL: jbom bom project.kicad_pcb → ERROR (BOM expects .kicad_sch, fails on .kicad_pcb)
    # EXPECTED: jbom bom project.kicad_pcb → SUCCESS (finds matching .kicad_sch automatically)

    When I run jbom command "bom test_project/test_project.kicad_pcb -o console -v"
    Then the command should succeed
    And the error output should mention "trying to find matching schematic"
    And the error output should mention "Using schematic: test_project.kicad_sch"
    And the BOM output should contain component "R1" with value "10k"

  @regression @cross-command @bom
  Scenario: BOM command should handle project file input intelligently
    # ORIGINAL: jbom bom project.kicad_pro → ERROR (BOM expects .kicad_sch, fails on .kicad_pro)
    # EXPECTED: jbom bom project.kicad_pro → SUCCESS (finds project's main schematic)

    When I run jbom command "bom test_project/test_project.kicad_pro -o console -v"
    Then the command should succeed
    And the error output should mention "trying to find matching schematic"
    And the BOM output should contain component "R1" with value "10k"

  @regression @cross-command @pos
  Scenario: POS command should handle schematic file input intelligently
    # ORIGINAL: jbom pos project.kicad_sch → ERROR (POS expects .kicad_pcb, fails on .kicad_sch)
    # EXPECTED: jbom pos project.kicad_sch → SUCCESS (finds matching .kicad_pcb automatically)

    When I run jbom command "pos test_project/test_project.kicad_sch -o console -v"
    Then the command should succeed
    And the error output should mention "trying to find matching PCB"
    And the error output should mention "Using PCB: test_project.kicad_pcb"
    And the POS output should contain component "R1" at position "76.2" x "104.14" y

  @regression @cross-command @pos
  Scenario: POS command should handle project file input intelligently
    # ORIGINAL: jbom pos project.kicad_pro → ERROR (POS expects .kicad_pcb, fails on .kicad_pro)
    # EXPECTED: jbom pos project.kicad_pro → SUCCESS (finds project's PCB file)

    When I run jbom command "pos test_project/test_project.kicad_pro -o console -v"
    Then the command should succeed
    And the error output should mention "trying to find matching PCB"
    And the POS output should contain component "R1" at position "76.2" x "104.14" y

  @regression @error-handling
  Scenario: Empty directory should provide helpful error
    # ORIGINAL: jbom bom empty_dir → Generic "file not found" error
    # EXPECTED: jbom bom empty_dir → Specific "No project files found" error

    Given an empty directory "empty_project"
    When I run jbom command "bom empty_project"
    Then the command should fail
    And the error output should contain "No project files found"

  @regression @error-handling
  Scenario: Missing target file should suggest alternatives
    # ORIGINAL: jbom bom pcb_only_dir → Generic error
    # EXPECTED: jbom bom pcb_only_dir → Helpful suggestion about missing schematic
    # NOTE: Using real KiCad project structure (.kicad_pro + .kicad_pcb, no .kicad_sch)

    Given a KiCad project fixture "pcb_only" named "test_pcb_only"
    When I run jbom command "bom test_pcb_only"
    Then the command should fail
    And the error output should contain "schematic file found"

  @regression @backward-compatibility @bom
  Scenario: Explicit file paths should still work unchanged
    # ORIGINAL: jbom bom explicit.kicad_sch → SUCCESS (this worked)
    # EXPECTED: jbom bom explicit.kicad_sch → SUCCESS (backward compatibility preserved)

    When I run jbom command "bom test_project/test_project.kicad_sch -o console"
    Then the command should succeed
    And the BOM output should contain component "R1" with value "10k"

  @regression @hierarchical @bom
  Scenario: Hierarchical schematics should be processed completely
    # ORIGINAL: Only processes root schematic file (misses components from sheets)
    # EXPECTED: Discovers and processes all hierarchical sheets automatically

    Given a hierarchical project "hierarchical_project"
    And the main schematic "main.kicad_sch" references sheet "power.kicad_sch"
    And "main.kicad_sch" contains component "R1" with value "1k"
    And "power.kicad_sch" contains component "C1" with value "100n"
    When I run jbom command "bom hierarchical_project -o console -v"
    Then the command should succeed
    And the error output should mention "Processing hierarchical design with 2 schematic files"
    And the BOM output should contain component "R1" with value "1k"
    And the BOM output should contain component "C1" with value "100n"

  @regression @legacy-support
  Scenario: Legacy .pro project files should be supported
    # ORIGINAL: No .pro file support (only looks for .kicad_pro)
    # EXPECTED: Should discover and use legacy .pro files when .kicad_pro not available

    Given a project directory "legacy_project" with legacy ".pro" file
    And the project contains a schematic with component "R1" with value "22k"
    When I run jbom command "bom legacy_project -o console"
    Then the command should succeed
    And the BOM output should contain component "R1" with value "22k"
    And the BOM title should show project name "legacy_project"
