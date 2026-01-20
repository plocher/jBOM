Feature: Project-Centric Architecture
  As a KiCad user
  I want jBOM commands to work with project directories and base names
  So that I can use natural KiCad workflows without specifying explicit file paths

  Background:
    Given a KiCad project directory "test_project"
    And the project contains a file "test_project.kicad_pro" with content:
      """
      (kicad_project (version 1))
      """
    And the project contains a file "test_project.kicad_sch" with content:
      """
      (kicad_sch (version 20211123) (generator eeschema)
        (symbol (lib_id "Device:R") (at 76.2 104.14 0) (unit 1)
          (property "Reference" "R1" (id 0) (at 78.74 104.14 0))
          (property "Value" "10k" (id 1) (at 78.74 106.68 0))
          (property "Footprint" "Resistor_SMD:R_0603_1608Metric" (id 2) (at 74.168 104.14 90))
        )
      )
      """
    And the project contains a file "test_project.kicad_pcb" with content:
      """
      (kicad_pcb (version 20211014) (generator pcbnew)
        (footprint "Resistor_SMD:R_0603_1608Metric" (at 76.2 104.14) (layer "F.Cu")
          (fp_text reference "R1" (at 0 0) (layer "F.SilkS"))
          (fp_text value "10k" (at 0 1.5) (layer "F.Fab"))
          (pad "1" smd roundrect (at -0.8 0) (size 0.9 0.95))
          (pad "2" smd roundrect (at 0.8 0) (size 0.9 0.95))
        )
      )
      """

  Scenario: BOM command with current directory
    When I run jbom command "bom ." in directory "test_project"
    Then the command should succeed
    And the BOM should contain component "R1" with value "10k"
    And the project name should be "test_project"

  Scenario: BOM command with project directory path
    When I run jbom command "bom test_project"
    Then the command should succeed
    And the BOM should contain component "R1" with value "10k"
    And the project name should be "test_project"

  Scenario: BOM command with project base name
    When I run jbom command "bom test_project" in directory "."
    Then the command should succeed
    And the BOM should contain component "R1" with value "10k"
    And the project name should be "test_project"

  Scenario: BOM command with explicit schematic file (backward compatibility)
    When I run jbom command "bom test_project/test_project.kicad_sch"
    Then the command should succeed
    And the BOM should contain component "R1" with value "10k"
    And the project name should be "test_project"

  Scenario: POS command with current directory
    When I run jbom command "pos ." in directory "test_project"
    Then the command should succeed
    And the POS should contain component "R1" at position "76.2,104.14"

  Scenario: POS command with project directory path
    When I run jbom command "pos test_project"
    Then the command should succeed
    And the POS should contain component "R1" at position "76.2,104.14"

  Scenario: POS command with explicit PCB file (backward compatibility)
    When I run jbom command "pos test_project/test_project.kicad_pcb"
    Then the command should succeed
    And the POS should contain component "R1" at position "76.2,104.14"

  Scenario: Inventory generate with current directory
    When I run jbom command "inventory generate . -o test_inventory.csv" in directory "test_project"
    Then the command should succeed
    And the inventory file should contain component with value "10k"

  Scenario: Inventory generate with project directory path
    When I run jbom command "inventory generate test_project -o test_inventory.csv"
    Then the command should succeed
    And the inventory file should contain component with value "10k"

  # Cross-command intelligence scenarios
  Scenario: BOM command with PCB file should find matching schematic
    When I run jbom command "bom test_project/test_project.kicad_pcb -v"
    Then the command should succeed
    And the output should contain "trying to find matching schematic"
    And the output should contain "Using schematic: test_project.kicad_sch"
    And the BOM should contain component "R1" with value "10k"

  Scenario: BOM command with project file should find matching schematic
    When I run jbom command "bom test_project/test_project.kicad_pro -v"
    Then the command should succeed
    And the output should contain "trying to find matching schematic"
    And the output should contain "Using schematic: test_project.kicad_sch"
    And the BOM should contain component "R1" with value "10k"

  Scenario: POS command with schematic file should find matching PCB
    When I run jbom command "pos test_project/test_project.kicad_sch -v"
    Then the command should succeed
    And the output should contain "trying to find matching PCB"
    And the output should contain "Using PCB: test_project.kicad_pcb"
    And the POS should contain component "R1" at position "76.2,104.14"

  Scenario: POS command with project file should find matching PCB
    When I run jbom command "pos test_project/test_project.kicad_pro -v"
    Then the command should succeed
    And the output should contain "trying to find matching PCB"
    And the output should contain "Using PCB: test_project.kicad_pcb"
    And the POS should contain component "R1" at position "76.2,104.14"

  # Different naming scenarios
  Scenario: Project with different file names
    Given a KiCad project directory "mixed_project"
    And the project contains a file "different_name.kicad_pro"
    And the project contains a file "different_name.kicad_sch" with basic schematic content
    And the project contains a file "different_name.kicad_pcb" with basic PCB content
    When I run jbom command "bom mixed_project"
    Then the command should succeed
    And the project name should be "different_name"

  Scenario: Multiple project files should use first one found
    Given a KiCad project directory "multi_project"
    And the project contains a file "first.kicad_pro"
    And the project contains a file "first.kicad_sch" with basic schematic content
    And the project contains a file "second.kicad_pro"
    And the project contains a file "second.kicad_sch" with basic schematic content
    When I run jbom command "bom multi_project"
    Then the command should succeed
    And the project name should be "first"

  # Error handling scenarios
  Scenario: Empty directory should provide helpful error
    Given a KiCad project directory "empty_project"
    When I run jbom command "bom empty_project"
    Then the command should fail
    And the error should contain "No project files found"

  Scenario: Missing schematic file should suggest alternatives
    Given a KiCad project directory "pcb_only_project"
    And the project contains a file "pcb_only.kicad_pcb" with basic PCB content
    When I run jbom command "bom pcb_only_project"
    Then the command should fail
    And the error should contain "No schematic file found"

  Scenario: Missing PCB file should suggest alternatives
    Given a KiCad project directory "sch_only_project"
    And the project contains a file "sch_only.kicad_sch" with basic schematic content
    When I run jbom command "pos sch_only_project"
    Then the command should fail
    And the error should contain "No PCB file found"

  # Hierarchical schematic scenarios
  Scenario: Hierarchical schematic processing
    Given a KiCad project directory "hierarchical_project"
    And the project contains a file "main.kicad_sch" with content:
      """
      (kicad_sch (version 20211123)
        (symbol (lib_id "Device:R") (at 50 50 0) (unit 1)
          (property "Reference" "R1" (id 0) (at 52 50 0))
          (property "Value" "1k" (id 1) (at 52 52 0))
        )
        (sheet (at 100 100) (size 30 20)
          (property "Sheetname" "Power Supply")
          (property "Sheetfile" "power.kicad_sch")
        )
      )
      """
    And the project contains a file "power.kicad_sch" with content:
      """
      (kicad_sch (version 20211123)
        (symbol (lib_id "Device:C") (at 76.2 104.14 0) (unit 1)
          (property "Reference" "C1" (id 0) (at 78.74 104.14 0))
          (property "Value" "100n" (id 1) (at 78.74 106.68 0))
        )
      )
      """
    When I run jbom command "bom hierarchical_project -v"
    Then the command should succeed
    And the output should contain "Processing hierarchical design with 2 schematic files"
    And the output should contain "Loading components from main.kicad_sch"
    And the output should contain "Loading components from power.kicad_sch"
    And the BOM should contain component "R1" with value "1k"
    And the BOM should contain component "C1" with value "100n"

  # Legacy project file support
  Scenario: Legacy .pro project file support
    Given a KiCad project directory "legacy_project"
    And the project contains a file "legacy.pro" with content:
      """
      legacy project file content
      """
    And the project contains a file "legacy.kicad_sch" with basic schematic content
    When I run jbom command "bom legacy_project"
    Then the command should succeed
    And the project name should be "legacy"
