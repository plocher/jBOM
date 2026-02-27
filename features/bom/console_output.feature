Feature: BOM Console Output
  As a hardware developer
  I want a readable console BOM view
  So that I can inspect BOMs without generating files

  Background:
    Given the generic fabricator is selected

  Scenario: Console output formatting
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
    When I run jbom command "bom -o console"
    Then the command should succeed
    And the output should contain "Bill of Materials"
    And the output should contain "R1"
