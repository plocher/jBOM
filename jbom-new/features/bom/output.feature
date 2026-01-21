Feature: BOM Output Options
  As a hardware developer
  I want flexible BOM output options
  So that I can customize the output format and filtering

  Background:
    Given the generic fabricator is selected

  Scenario: CSV to stdout with default options
    Given a schematic that contains:
      | Reference | Value | Footprint         |
      | R1        | 10K   | R_0805_2012       |
      | C1        | 100nF | C_0603_1608       |
      | U1        | LM358 | SOIC-8_3.9x4.9mm |
    When I run jbom command "bom"
    Then the command should succeed
    And the output should contain "R1"
    And the output should contain "10K"
    And the output should contain "C1"
    And the output should contain "100nF"
    And the output should contain "U1"
    And the output should contain "LM358"

  Scenario: BOM with aggregated components
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | R2        | 10K   | R_0805_2012 |
      | R3        | 10K   | R_0603_1608 |
    When I run jbom command "bom"
    Then the command should succeed
    And the output should contain "R1"
    And the output should contain "R2"
    And the output should contain "R3"
    And the output should contain "10K"

  Scenario: Console output format
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | C1        | 100nF | C_0603_1608 |
    When I run jbom command "bom -o console"
    Then the command should succeed
    And the output should contain "Bill of Materials"
    And the output should contain "R1"
    And the output should contain "C1"

  Scenario: Verbose output
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
    When I run jbom command "bom -v"
    Then the command should succeed
    And the output should contain "R1"
    And the output should contain "10K"
