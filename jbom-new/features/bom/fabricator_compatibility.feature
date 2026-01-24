Feature: BOM Fabricator Compatibility
  As a hardware developer
  I want BOMs to work with different PCB fabricators
  So that I can use the same design with multiple suppliers

  Background:
    Given the generic fabricator is selected
    And a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | C1        | 100nF | C_0603_1608 |

  Scenario: BOM generation works with all configured fabricators
    When I run jbom command "bom"
    Then the BOM works with all configured fabricators

  Scenario: Different fabricators produce different output formats
    When I run jbom command "bom --generic"
    Then the command should succeed
    And the output should contain "Reference"
    When I run jbom command "bom --jlc"
    Then the command should succeed
    And the output should contain "Designator"
    When I run jbom command "bom --pcbway"
    Then the command should succeed
    And the output should contain "Designator"
    When I run jbom command "bom --seeed"
    Then the command should succeed
    And the output should contain "Designator"

  Scenario: Default behavior (generic fabricator)
    When I run jbom command "bom"
    Then the command should succeed
    And the output should contain "Reference"
    And the output should contain "Quantity"
    And the output should contain "Value"
    And the output should contain "Footprint"

  Scenario: No fabricator flag (default behavior)
    When I run jbom command "bom"
    Then the BOM works with all configured fabricators

  Scenario: JLC fabricator specific format
    When I run jbom command "bom --fabricator jlc"
    Then the command should succeed
    And the output should contain "Designator"

  # These will be skipped if fabricators not available
  Scenario: PCBWay fabricator specific format
    When I run jbom command "bom --fabricator pcbway"
    Then the command should succeed
    And the output should contain "Designator"

  Scenario: Seeed fabricator specific format
    When I run jbom command "bom --fabricator seeed"
    Then the command should succeed
    And the output should contain "Designator"
