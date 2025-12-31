Feature: Project Input Resolution
  As a PCB designer
  I want jBOM to find my project files intelligently
  So that I can reference projects flexibly without specifying exact paths

  Background: Test Environment
    Given a clean test environment in "/tmp/jbom_resolution_test"
    And the working directory is "/tmp/jbom_resolution_test"

  # Test Case 1: Specific file takes priority (most specific)
  Scenario: Input resolution prioritizes specific file over directory
    Given a file exists at "./TestProject.kicad_sch" containing:
      | Content Type | Value |
      | SchematicID  | specific-file-schematic |
    And a directory exists at "./TestProject/"
    And a file exists at "./TestProject/TestProject.kicad_sch" containing:
      | Content Type | Value |
      | SchematicID  | directory-matching-schematic |
    When I generate a generic BOM with "TestProject"
    Then the BOM generation succeeds
    And jBOM uses the schematic with ID "specific-file-schematic"
    And the processing reports "Using schematic: ./TestProject.kicad_sch"

  # Test Case 2: Directory with matching file (conventional structure)
  Scenario: Input resolution uses directory with matching filename
    Given no file exists at "./TestProject.kicad_sch"
    And a directory exists at "./TestProject/"
    And a file exists at "./TestProject/TestProject.kicad_sch" containing:
      | Content Type | Value |
      | SchematicID  | directory-matching-schematic |
    And a file exists at "./TestProject/SomeOther.kicad_sch" containing:
      | Content Type | Value |
      | SchematicID  | other-schematic |
    When I generate a generic BOM with "TestProject"
    Then the BOM generation succeeds
    And jBOM uses the schematic with ID "directory-matching-schematic"
    And the processing reports "Using schematic: ./TestProject/TestProject.kicad_sch"

  # Test Case 3: Directory with any schematic file (fallback)
  Scenario: Input resolution uses any schematic in directory as fallback
    Given no file exists at "./TestProject.kicad_sch"
    And a directory exists at "./TestProject/"
    And no file exists at "./TestProject/TestProject.kicad_sch"
    And a file exists at "./TestProject/MainBoard.kicad_sch" containing:
      | Content Type | Value |
      | SchematicID  | fallback-schematic |
    When I generate a generic BOM with "TestProject"
    Then the BOM generation succeeds
    And jBOM uses the schematic with ID "fallback-schematic"
    And the processing reports "Using schematic: ./TestProject/MainBoard.kicad_sch"

  # Test Case 4: Multiple schematics in directory - hierarchical root detection
  Scenario: Input resolution prefers hierarchical root in directory
    Given no file exists at "./ComplexProject.kicad_sch"
    And a directory exists at "./ComplexProject/"
    And no file exists at "./ComplexProject/ComplexProject.kicad_sch"
    And a file exists at "./ComplexProject/Root.kicad_sch" containing:
      | Content Type    | Value |
      | SchematicID     | hierarchical-root |
      | HasSubSheets    | true |
    And a file exists at "./ComplexProject/SubSheet.kicad_sch" containing:
      | Content Type    | Value |
      | SchematicID     | sub-sheet |
      | HasSubSheets    | false |
    When I generate a generic BOM with "ComplexProject"
    Then the BOM generation succeeds
    And jBOM uses the schematic with ID "hierarchical-root"
    And the processing reports "Using hierarchical root: ./ComplexProject/Root.kicad_sch"

  # Test Case 5: Complete resolution failure
  Scenario: Input resolution fails when no valid schematic found
    Given no file exists at "./MissingProject.kicad_sch"
    And no directory exists at "./MissingProject/"
    When I generate a generic BOM with "MissingProject"
    Then the BOM generation fails with exit code 1
    And the error message reports "Project 'MissingProject' not found"
    And the error message lists attempted resolution paths:
      | Resolution Step | Path Attempted |
      | 1 | ./MissingProject.kicad_sch |
      | 2 | ./MissingProject/MissingProject.kicad_sch |
      | 3 | ./MissingProject/ (any .kicad_sch files) |

  # Test Case 6: Directory exists but contains no schematics
  Scenario: Input resolution fails when directory contains no schematic files
    Given no file exists at "./EmptyProject.kicad_sch"
    And a directory exists at "./EmptyProject/"
    And no file exists at "./EmptyProject/EmptyProject.kicad_sch"
    And the directory "./EmptyProject/" contains no ".kicad_sch" files
    And the directory "./EmptyProject/" contains files:
      | Filename | Type |
      | README.md | text |
      | build.sh | script |
    When I generate a generic BOM with "EmptyProject"
    Then the BOM generation fails with exit code 1
    And the error message reports "No schematic files found in directory: ./EmptyProject/"

  # Test Case 7: Absolute path input (bypass resolution)
  Scenario: Absolute paths bypass resolution logic
    Given a file exists at "/tmp/jbom_resolution_test/Absolute.kicad_sch" containing:
      | Content Type | Value |
      | SchematicID  | absolute-path-schematic |
    When I generate a generic BOM with "/tmp/jbom_resolution_test/Absolute.kicad_sch"
    Then the BOM generation succeeds
    And jBOM uses the schematic with ID "absolute-path-schematic"
    And the processing reports "Using schematic: /tmp/jbom_resolution_test/Absolute.kicad_sch"

  # Test Case 8: Relative path with extension (bypass resolution)
  Scenario: Paths with kicad_sch extension bypass resolution logic
    Given a file exists at "./Direct.kicad_sch" containing:
      | Content Type | Value |
      | SchematicID  | direct-file-schematic |
    When I generate a generic BOM with "./Direct.kicad_sch"
    Then the BOM generation succeeds
    And jBOM uses the schematic with ID "direct-file-schematic"
    And the processing reports "Using schematic: ./Direct.kicad_sch"

  # Test Case 9: Directory path with trailing slash
  Scenario: Directory path with trailing slash searches within directory
    Given a directory exists at "./DirProject/"
    And a file exists at "./DirProject/Main.kicad_sch" containing:
      | Content Type | Value |
      | SchematicID  | directory-main-schematic |
    When I generate a generic BOM with "./DirProject/"
    Then the BOM generation succeeds
    And jBOM uses the schematic with ID "directory-main-schematic"
    And the processing reports "Using schematic: ./DirProject/Main.kicad_sch"

  # Test Case 10: Permission denied scenarios
  Scenario: Input resolution handles permission denied gracefully
    Given a file exists at "./PermissionProject.kicad_sch"
    And the file "./PermissionProject.kicad_sch" is not readable
    When I generate a generic BOM with "PermissionProject"
    Then the BOM generation fails with exit code 1
    And the error message reports "Permission denied accessing: ./PermissionProject.kicad_sch"

  # Test Case 11: Symlink resolution
  Scenario: Input resolution follows symbolic links
    Given a file exists at "./Target.kicad_sch" containing:
      | Content Type | Value |
      | SchematicID  | symlink-target-schematic |
    And a symbolic link exists from "./LinkProject.kicad_sch" to "./Target.kicad_sch"
    When I generate a generic BOM with "LinkProject"
    Then the BOM generation succeeds
    And jBOM uses the schematic with ID "symlink-target-schematic"
    And the processing reports "Using schematic: ./LinkProject.kicad_sch"
