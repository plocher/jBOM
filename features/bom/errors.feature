Feature: BOM Errors
  As a user
  I want meaningful error messages
  So that I can fix input problems quickly

  Background:
    Given the generic fabricator is selected

  Scenario: Error on missing schematic file
    When I run jbom command "bom missing_file.kicad_sch"
    Then the command should fail
    And the error output should mention "No schematic file found"
