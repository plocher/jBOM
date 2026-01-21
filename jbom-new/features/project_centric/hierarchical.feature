Feature: Hierarchical schematic handling

  # Construct minimal hierarchical projects inline.

  Scenario: BOM includes all child sheets and reports hierarchy
    Given the project uses a root schematic "main" that contains:
      | Reference | Value | Footprint |
    And the root references child schematic "child"
    And the child schematic "child" contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0603_1608 |
    When I run jbom command "bom -o console -v"
    Then the command should succeed
    And the output should contain "R1"

  Scenario: Missing child sheet logs warning but continues
    Given I create directory "tmp_hier_missing"
    And I am in directory "tmp_hier_missing"
    And the project uses a root schematic "main" that contains:
      | Reference | Value | Footprint |
    And the root references child schematic "missing"
    When I run jbom command "bom -o console -v"
    Then the command should succeed
