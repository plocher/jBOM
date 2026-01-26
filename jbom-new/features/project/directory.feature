Feature: Directory-based Project References

  Background:
    Given a jBOM CSV sandbox

  Scenario: BOM command with no project parameter finds current directory project
    Given a schematic that contains:
      | Reference | Value | Footprint     |
      | R1        | 10K   | R_0805_2012   |
    When I run jbom command "bom"
    Then the command should succeed

  Scenario: POS command with no project parameter finds current directory project
    Given a PCB that contains:
      | reference | x | y | rotation | side | footprint     |
      | R1        | 5 | 10| 0        | TOP  | R_0805_2012   |
    When I run jbom command "pos"
    Then the command should succeed

  Scenario: Inventory command with no project parameter finds current directory project
    Given a schematic that contains:
      | Reference | Value | Footprint     |
      | R1        | 10K   | R_0805_2012   |
    When I run jbom command "inventory"
    Then the command should succeed

  # Explicit directory reference scenarios

  Scenario: BOM command given directory name finds project in that directory
    Given a project "myproject" placed in "project_dir"
    And the schematic "myproject" contains:
      | Reference | Value | Footprint     |
      | R1        | 10K   | R_0805_2012   |
    When I run jbom command "bom project_dir"
    Then the command should succeed

  Scenario: POS command given directory name finds project in that directory
    Given a project "myproject" placed in "project_dir"
    And a PCB that contains:
      | reference | x | y | rotation | side | footprint     |
      | R1        | 5 | 10| 0        | TOP  | R_0805_2012   |
    When I run jbom command "pos project_dir"
    Then the command should succeed

  Scenario: Inventory command given directory name finds project in that directory
    Given a project "myproject" placed in "project_dir"
    And the schematic "myproject" contains:
      | Reference | Value | Footprint     |
      | R1        | 10K   | R_0805_2012   |
    When I run jbom command "inventory project_dir"
    Then the command should succeed

  # Edge case scenarios

  Scenario: Command given nonexistent directory fails
    When I run jbom command "bom nonexistent_directory"
    Then the command should fail

  Scenario: Command given directory with no project files fails
    Given an empty directory "empty_dir"
    When I run jbom command "bom empty_dir"
    Then the command should fail
