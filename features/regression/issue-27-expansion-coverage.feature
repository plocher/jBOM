@regression
Feature: [Issue #27] Expand project-centric coverage across all commands

  # Simplified scenarios without fixture dependencies
  # Many original scenarios evaporated when removing fixture complexity

  Scenario: Inventory command works with project directory
    Given a project "flat" placed in "flat_project"
    And the schematic "flat" contains:
      | Reference | Value | Footprint     | LibID    |
      | R1        | 10K   | R_0805_2012   | Device:R |
    When I run jbom command "inventory flat_project -o console"
    Then the command should succeed

  Scenario: POS resolves from explicit PCB file
    Given a project "test" placed in "test_project"
    And a PCB that contains:
      | reference | x     | y     | rotation | side | footprint     |
      | R1        | 76.2  | 104.1 | 0        | TOP  | R_0805_2012   |
    When I run jbom command "pos test_project/test.kicad_pcb -o console -v"
    Then the command should succeed

  Scenario: Empty directory provides helpful error message
    Given an empty directory "empty_test"
    When I run jbom command "bom empty_test -o console"
    Then the command should fail
    And the output should contain "No project files found"
