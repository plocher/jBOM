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

  Scenario: Inventory includes all components from hierarchical design
    Given the project uses a root schematic "main" that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
    And the root references child schematic "child"
    And the child schematic "child" contains:
      | Reference | Value | Footprint   |
      | C1        | 100nF | C_0603_1608 |
      | U1        | LM358 | SOIC-8      |
    When I run jbom command "inventory -o console -v"
    Then the command should succeed
    And the output should contain "Generated inventory"
    And the output should contain "hierarchical design"
    And the output should contain "R1"
    And the output should contain "C1"
    And the output should contain "U1"
