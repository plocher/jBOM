Feature: BOM Errors
  As a user
  I want meaningful error messages
  So that I can fix input problems quickly

  Scenario: Error on missing schematic file
    When I run "jbom bom missing_file.kicad_sch"
    Then the command exits with code 1
    And the error output contains "Schematic file not found"
