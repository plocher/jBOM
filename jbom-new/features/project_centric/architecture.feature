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
    When I run jbom command "bom . -v"
    Then the command should succeed
    And the output should contain "found schematic test_project.kicad_sch"

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
    And the error output should mention "No project files found"

  Scenario: Missing schematic file should suggest alternatives
    Given a KiCad project directory "pcb_only_project"
    And the project contains a file "pcb_only.kicad_pcb" with basic PCB content
    When I run jbom command "bom pcb_only_project"
    Then the command should fail
    And the error output should mention "No schematic file found"

  Scenario: Missing PCB file should suggest alternatives
    Given a KiCad project directory "sch_only_project"
    And the project contains a file "sch_only.kicad_sch" with basic schematic content
    When I run jbom command "pos sch_only_project"
    Then the command should fail
    And the error output should mention "No PCB file found"

  # TODO: Hierarchical schematic scenarios
  # Current implementation uses circular validation (hand-crafted KiCad files that mirror jBOM expectations)
  # Proper approach: Use real KiCad-generated fixture files for authentic compatibility testing
  # See: https://github.com/user/repo/issues/XXX - Replace with fixture-based hierarchical testing

  # TODO: Legacy project file support
  # Current implementation uses fake .pro content that doesn't test real KiCad compatibility
  # Proper approach: Use actual legacy KiCad .pro files from fixtures/
  # See: https://github.com/user/repo/issues/XXX - Replace with fixture-based legacy testing
