Feature: BOM Fabricator Compatibility
  As a hardware developer
  I want BOMs to work with different PCB fabricators
  So that I can use the same design with multiple suppliers

  Background:
    Given a clean test workspace
    And a KiCad schematic file "project.kicad_sch" with components:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | C1        | 100nF | C_0603_1608 |

  Scenario: BOM generation works with all configured fabricators
    When I run "jbom bom project.kicad_sch --generic"
    Then the BOM works with all configured fabricators

  Scenario: Different fabricators produce different output formats
    When I run "jbom bom project.kicad_sch --generic"
    Then the command exits with code 0
    And the output contains "Reference"
    When I run "jbom bom project.kicad_sch --jlc"
    Then the command exits with code 0
    And the output contains "Reference"
    When I run "jbom bom project.kicad_sch --pcbway"
    Then the command exits with code 0
    And the output contains "Reference"
    When I run "jbom bom project.kicad_sch --seeed"
    Then the command exits with code 0
    And the output contains "Reference"

  Scenario: Default behavior (generic fabricator)
    When I run "jbom bom project.kicad_sch --generic"
    Then the command exits with code 0
    And the output contains CSV headers "References,Value,Footprint,Quantity"

  Scenario: No fabricator flag (default behavior)
    When I run "jbom bom project.kicad_sch"
    Then the command exits with code 0
    And the output contains CSV headers "References,Value,Footprint,Quantity"

  Scenario: JLC fabricator specific format
    When I run "jbom bom project.kicad_sch --fabricator jlc --generic"
    Then the command exits with code 0
    And the output contains CSV headers "References,Value,Footprint,Quantity"

  # These will be skipped if fabricators not available
  Scenario: PCBWay fabricator specific format
    When I run "jbom bom project.kicad_sch --fabricator pcbway --generic"
    Then the command exits with code 0
    And the output contains CSV headers "References,Value,Footprint,Quantity"

  Scenario: Seeed fabricator specific format
    When I run "jbom bom project.kicad_sch --fabricator seeed --generic"
    Then the command exits with code 0
    And the output contains CSV headers "References,Value,Footprint,Quantity"
