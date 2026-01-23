Feature: Project-Centric Architecture
  As a KiCad user
  I want jBOM commands to work with project directories and base names
  So that I can use natural KiCad workflows without specifying explicit file paths

  Background:
    Given the generic fabricator is selected

  Scenario: BOM command discovers project files from directory (current directory path)
    Given a KiCad project directory "test_project"
    And the project contains a file "test_project.kicad_pro"
    And the project contains a file "test_project.kicad_sch" with basic schematic content
    And I am in directory "test_project"
    When I run jbom command "bom . -v"
    Then the command should succeed
    And the output should contain "Using schematic: test_project.kicad_sch"

  Scenario: BOM command discovers project files from project name
    Given a KiCad project directory "test_project"
    And the project contains a file "test_project.kicad_pro"
    And the project contains a file "test_project.kicad_sch" with basic schematic content
    When I run jbom command "bom test_project -v"
    Then the command should succeed
    And the output should contain "Using schematic: test_project.kicad_sch"

  Scenario: BOM command discovers project from explicit schematic file path
    Given a KiCad project directory "test_project"
    And the project contains a file "test_project.kicad_pro"
    And the project contains a file "test_project.kicad_sch" with basic schematic content
    When I run jbom command "bom test_project/test_project.kicad_sch -v"
    Then the command should succeed
    And the output should contain "Using schematic: test_project.kicad_sch"

  Scenario: POS command discovers project files from directory (current directory path)
    Given a KiCad project directory "test_project"
    And the project contains a file "test_project.kicad_pro"
    And the project contains a file "test_project.kicad_pcb" with basic PCB content
    And I am in directory "test_project"
    When I run jbom command "pos . -v"
    Then the command should succeed
    And the output should contain "Using PCB: test_project.kicad_pcb"

  Scenario: POS command discovers project files from project name
    Given a KiCad project directory "test_project"
    And the project contains a file "test_project.kicad_pro"
    And the project contains a file "test_project.kicad_pcb" with basic PCB content
    When I run jbom command "pos test_project -v"
    Then the command should succeed
    And the output should contain "Using PCB: test_project.kicad_pcb"

  Scenario: POS command discovers project from explicit PCB file path
    Given a KiCad project directory "test_project"
    And the project contains a file "test_project.kicad_pro"
    And the project contains a file "test_project.kicad_pcb" with basic PCB content
    When I run jbom command "pos test_project/test_project.kicad_pcb -v"
    Then the command should succeed
    And the output should contain "Using PCB: test_project.kicad_pcb"

  Scenario: Inventory command discovers project files from directory (current directory path)
    Given a KiCad project directory "test_project"
    And the project contains a file "test_project.kicad_pro"
    And the project contains a file "test_project.kicad_sch" with basic schematic content
    And I am in directory "test_project"
    When I run jbom command "inventory generate . -o test_inventory.csv -v"
    Then the command should succeed
    And the output should contain "Using schematic: test_project.kicad_sch"

  Scenario: Inventory command discovers project files from project name
    Given a KiCad project directory "test_project"
    And the project contains a file "test_project.kicad_pro"
    And the project contains a file "test_project.kicad_sch" with basic schematic content
    When I run jbom command "inventory generate test_project -o test_inventory.csv -v"
    Then the command should succeed
    And the output should contain "Using schematic: test_project.kicad_sch"

  # Cross-file intelligence scenarios
  Scenario Outline: Cross-file intelligence discovers matching files
    Given a KiCad project directory "cross_test"
    And the project contains a file "cross_test.kicad_sch" with basic schematic content
    And the project contains a file "cross_test.kicad_pcb" with basic PCB content
    When I run jbom command "<command> cross_test/<input_file> -v"
    Then the command should succeed
    And the output should contain "trying to find matching <target_type>"
    And the output should contain "Using <target_type>: cross_test.<target_ext>"
    Examples:
      | command | input_file           | target_type | target_ext |
      | bom     | cross_test.kicad_pcb | schematic   | kicad_sch  |
      | bom     | cross_test.kicad_pro | schematic   | kicad_sch  |
      | pos     | cross_test.kicad_sch | PCB         | kicad_pcb  |
      | pos     | cross_test.kicad_pro | PCB         | kicad_pcb  |

  # Different naming scenarios
  Scenario: Project with different file names
    Given a KiCad project directory "mixed_project"
    And the project contains a file "different_name.kicad_pro"
    And the project contains a file "different_name.kicad_sch" with basic schematic content
    When I run jbom command "bom mixed_project -v"
    Then the command should succeed
    And the output should contain "Using schematic: different_name.kicad_sch"

  Scenario: Multiple project files should use first one found
    Given a KiCad project directory "multi_project"
    And the project contains a file "first.kicad_pro"
    And the project contains a file "first.kicad_sch" with basic schematic content
    And the project contains a file "second.kicad_pro"
    And the project contains a file "second.kicad_sch" with basic schematic content
    When I run jbom command "bom multi_project -v"
    Then the command should succeed
    And the output should contain "Using schematic: first.kicad_sch"

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
