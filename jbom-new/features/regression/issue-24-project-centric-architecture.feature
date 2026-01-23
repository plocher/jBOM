@regression
Feature: [Issue #24] Project-Centric Architecture - File-centric commands break KiCad workflows

  # Background: Describe the original issue
  # - What was happening?
  #   jBOM commands required explicit .kicad_sch/.kicad_pcb file paths
  #   Users couldn't run "jbom bom ." in project directories
  #   No cross-command intelligence (e.g., BOM given .kicad_pcb file would fail)
  #   Commands didn't understand KiCad project structure or relationships
  # - Under what conditions?
  #   When users tried natural KiCad workflows with project directories
  #   When users provided "wrong" file type to commands (PCB to BOM, schematic to POS)
  #   When working with hierarchical schematics across multiple files
  # - What was the expected behavior?
  #   Commands should discover project files automatically like KiCad does
  #   Should accept directories, base names, and provide cross-file intelligence

  Background:
    Given a clean test workspace
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

  Scenario: Reproduce the original issue - BOM command with current directory (now fixed)
    # Originally: jbom bom . would fail with "file not found" error
    # This should now pass because project discovery is implemented

    When I am in project directory "test_project"
    And I run jbom command "bom . -o console"
    Then the command should succeed
    And the BOM output should contain component "R1" with value "10k"
    And the BOM title should show project name "test_project"

  Scenario: Reproduce the original issue - BOM with project directory path (now fixed)
    # Originally: jbom bom /path/to/project would fail requiring explicit .kicad_sch
    # This should now pass because directory-based discovery is implemented

    When I run jbom command "bom test_project -o console"
    Then the command should succeed
    And the BOM output should contain component "R1" with value "10k"
    And the BOM title should show project name "test_project"

  Scenario: Reproduce the original issue - POS command with current directory (now fixed)
    # Originally: jbom pos . would fail with "file not found" error
    # This should now pass because project discovery is implemented

    When I am in project directory "test_project"
    And I run jbom command "pos . -o console"
    Then the command should succeed
    And the POS output should contain component "R1" at position "76.2" x "104.14" y

  Scenario: Reproduce the original issue - Cross-command intelligence BOM with PCB file (now fixed)
    # Originally: jbom bom project.kicad_pcb would fail "BOM requires schematic file"
    # This should now pass because cross-file resolution is implemented

    When I run jbom command "bom test_project/test_project.kicad_pcb -o console -v"
    Then the command should succeed
    And the error output should mention "found matching schematic test_project.kicad_sch"
    And the BOM output should contain component "R1" with value "10k"

  Scenario: Reproduce the original issue - Cross-command intelligence POS with schematic file (now fixed)
    # Originally: jbom pos project.kicad_sch would fail "POS requires PCB file"
    # This should now pass because cross-file resolution is implemented

    When I run jbom command "pos test_project/test_project.kicad_sch -o console -v"
    Then the command should succeed
    And the error output should mention "found matching PCB test_project.kicad_pcb"
    And the POS output should contain component "R1" at position "76.2" x "104.14" y

  Scenario: Edge case that could trigger regression - Empty directory provides helpful error
    # Edge case: Make sure error handling is still user-friendly
    # Regression risk: Project discovery might crash on empty directories

    Given an empty directory "empty_project"
    When I run jbom command "bom empty_project"
    Then the command should fail
    And the error output should contain "No project files found"

  Scenario: Edge case that could trigger regression - Base name resolution works consistently
    # Edge case: Base name resolution across all commands
    # Regression risk: Base name logic might not be applied to all commands

    When I run jbom command "inventory generate test_project -o test_inventory.csv"
    Then the command should succeed
    And the inventory file should contain component with value "10k"

  Scenario: Edge case that could trigger regression - Hierarchical schematic processing
    # Edge case: Complex project structures with hierarchical schematics
    # Regression risk: Might only process root file, missing components from sheets

    Given a hierarchical project "hierarchical_project"
    And the main schematic "main.kicad_sch" references sheet "power.kicad_sch"
    And "main.kicad_sch" contains component "R1" with value "1k"
    And "power.kicad_sch" contains component "C1" with value "100n"
    When I run jbom command "bom hierarchical_project -o console -v"
    Then the command should succeed
    And the error output should mention "Processing hierarchical design with 2 schematic files"
    And the BOM output should contain component "R1" with value "1k"
    And the BOM output should contain component "C1" with value "100n"

  Scenario: Edge case that could trigger regression - Backward compatibility maintained
    # Edge case: Existing explicit file path usage must continue working
    # Regression risk: New project logic might break existing workflows

    When I run jbom command "bom test_project/test_project.kicad_sch -o console"
    Then the command should succeed
    And the BOM output should contain component "R1" with value "10k"

  Scenario: Edge case that could trigger regression - Legacy .pro project file support
    # Edge case: Legacy KiCad project files should be discovered
    # Regression risk: Might only look for modern .kicad_pro files

    Given a project directory "legacy_project" with legacy ".pro" file
    And the project contains a schematic with component "R1" with value "22k"
    When I run jbom command "bom legacy_project -o console"
    Then the command should succeed
    And the BOM output should contain component "R1" with value "22k"
    And the BOM title should show project name "legacy_project"
