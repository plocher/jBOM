Feature: BOM Console Output
  As a hardware developer
  I want a readable console BOM view
  So that I can inspect BOMs without generating files

  Background:
    Given a clean test workspace

  Scenario: Console output formatting
    Given a KiCad schematic file "console.kicad_sch" with basic components
    When I run "jbom bom console.kicad_sch -o console --generic"
    Then the command exits with code 0
    And the output contains a formatted table header
    And the output contains component references and values
