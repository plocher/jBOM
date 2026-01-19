Feature: BOM Discovery and Error Handling
  As a hardware developer
  I want predictable file discovery and clear error messages
  So that I can work efficiently with different project layouts

  Background:
    Given I have various KiCad project configurations

  Scenario: Generate BOM from directory with .kicad_pro file
    Given I have a directory "test-project" containing:
      | File                        | Type     |
      | test-project.kicad_pro      | project  |
      | test-project.kicad_sch      | schematic|
      | additional-sheet.kicad_sch  | schematic|
    When I run "jbom bom --fabricator generic test-project"
    Then the command should succeed
    And a file "test-project/test-project.bom.csv" should be created
    And the BOM should include components from all schematic files

  Scenario: Generate BOM from project basename
    Given I have files in current directory:
      | File                        | Type     |
      | my-board.kicad_pro          | project  |
      | my-board.kicad_sch          | schematic|
      | power-supply.kicad_sch      | schematic|
    When I run "jbom bom --fabricator generic my-board"
    Then the command should succeed
    And a file "my-board.bom.csv" should be created
    And the BOM should include components from all related schematic files

  Scenario: Generate BOM from specific schematic file
    Given I have a single schematic file "standalone.kicad_sch"
    When I run "jbom bom --fabricator generic standalone.kicad_sch"
    Then the command should succeed
    And a file "standalone.bom.csv" should be created
    And the BOM should include components from that schematic file only

  Scenario: Generate BOM from current directory (implicit PROJECT)
    Given I am in a directory containing:
      | File                     | Type     |
      | current.kicad_pro        | project  |
      | current.kicad_sch        | schematic|
    When I run "jbom bom --fabricator generic"
    Then the command should succeed
    And a file "current.bom.csv" should be created
    And the BOM should include components from the schematic

  Scenario: Handle hierarchical schematics in PROJECT
    Given I have a project with hierarchical schematics:
      | File                     | Type           |
      | main.kicad_pro           | project        |
      | main.kicad_sch           | root schematic |
      | cpu-module.kicad_sch     | sub schematic  |
      | power-module.kicad_sch   | sub schematic  |
    When I run "jbom bom --fabricator generic main"
    Then the command should succeed
    And the BOM should include components from all schematic files
    And hierarchical components should be properly aggregated

  Scenario: Error when no schematic files found
    Given I have a directory "empty-project" with only:
      | File              | Type    |
      | empty.kicad_pro   | project |
    When I run "jbom bom --fabricator generic empty-project"
    Then the command should fail
    And the error should mention "No .kicad_sch files found"

  Scenario: Error when PROJECT doesn't exist
    When I run "jbom bom --fabricator generic non-existent-project"
    Then the command should fail
    And the error should mention the non-existent path

  Scenario: Generate BOM with custom output path from PROJECT
    Given I have a project directory "my-project"
    When I run "jbom bom --fabricator generic my-project -o /tmp/custom-bom.csv"
    Then the command should succeed
    And a file "/tmp/custom-bom.csv" should be created
    And the BOM should contain project components
