Feature: Inventory flows with project-centric inputs

  Background:
    Given the sample fixtures under "features/fixtures/kicad_samples"

  Scenario: Inventory from project directory (flat)
    When I run jbom command "inventory generate features/fixtures/kicad_samples/flat_project -o console"
    Then the command should succeed

  Scenario: Inventory from base name in cwd (hierarchical)
    Given I am in directory "features/fixtures/kicad_samples/hier_project"
    When I run jbom command "inventory generate hier -o console -v"
    Then the command should succeed
    And the error output should mention "Processing hierarchical design"
