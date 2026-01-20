Feature: Schematic Loading Edge Cases
  As a user
  I want clear behavior when selecting schematics
  So that errors are actionable and guidance is provided

  Background:
    Given a clean test workspace

  @wip
  Scenario: Directory with multiple schematics requires explicit selection
    Given a KiCad schematic file "a.kicad_sch" with basic components
    And a KiCad schematic file "b.kicad_sch" with basic components
    When I run "jbom bom ."
    Then the command exits with code 1
    And the error output contains "Multiple schematics found"

  @wip
  Scenario: Directory with one schematic is auto-selected
    Given a KiCad schematic file "single.kicad_sch" with basic components
    When I run "jbom bom ."
    Then the command exits with code 0
    And the output contains CSV headers "References,Value,Footprint,Quantity"

  Scenario: Unsupported file extension is rejected
    Given a file "not_schematic.txt" with content "hello"
    When I run "jbom bom not_schematic.txt"
    Then the command exits with code 1
    And the error output contains "Expected .kicad_sch file"
