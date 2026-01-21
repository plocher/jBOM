@regression
Feature: [Issue #27] Expand project-centric coverage across all commands

  Background:
    Given the sample fixtures under "features/fixtures/kicad_samples"

  Scenario: Inventory command works with project directory (flat project)
    When I run jbom command "inventory generate features/fixtures/kicad_samples/flat_project -o console"
    Then the command should succeed

  Scenario: Inventory command resolves from base name in cwd (flat project)
    Given I am in directory "features/fixtures/kicad_samples/flat_project"
    When I run jbom command "inventory generate flat -o console"
    Then the command should succeed

  Scenario: Discovery handles mismatched names by project (.pro/.kicad_pro)
    When I run jbom command "bom features/fixtures/kicad_samples/mismatched_names -o console -v"
    Then the command should succeed
    And the output should contain "alpha - Bill of Materials"
    And the output should contain "Loading components from beta.kicad_sch"

  Scenario: Hierarchical project BOM includes child sheets
    When I run jbom command "bom features/fixtures/kicad_samples/hier_project -o console -v"
    Then the command should succeed
    And the output should contain "Bill of Materials"

  Scenario: Legacy .pro discovery works
    When I run jbom command "bom features/fixtures/kicad_samples/legacy_pro -o console"
    Then the command should succeed

  Scenario: POS resolves from schematic input with confirmation message
    When I run jbom command "pos features/fixtures/kicad_samples/flat_project/flat.kicad_sch -o console -v"
    Then the command should succeed
    And the output should contain "Component Placement Data"

  Scenario: UX - helpful suggestions for missing files in directory
    Given an empty directory "features/fixtures/empty_dir"
    When I run jbom command "bom features/fixtures/empty_dir -o console"
    Then the command should fail
    And the output should contain "No project files found"
