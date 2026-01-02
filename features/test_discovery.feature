Feature: Test Step Discovery
  As a developer
  I want to verify behave step discovery works
  So that I can identify discovery issues

  Scenario: Test main directory steps
    Given this is a test step for discovery
    And a test step in the main directory

  Scenario: Test subdirectory steps
    Given a KiCad project named "TestProject"
    And the project uses a schematic named "TestSchematic"
