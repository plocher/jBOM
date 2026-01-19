Feature: BOM Output Options
  As a hardware developer
  I want flexible BOM output options
  So that I can customize the output format and filtering

  Scenario: BOM with different aggregation strategies
    Given a KiCad schematic file "aggregation_test.kicad_sch" with components:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | R2        | 10K   | R_0805_2012 |
      | R3        | 10K   | R_0603_1608 |
    When I run "jbom bom aggregation_test.kicad_sch --aggregation value_footprint"
    Then the command exits with code 0
    And the output contains "\"R1, R2\",10K,R_0805_2012,2"
    And the output contains "R3,10K,R_0603_1608,1"

  Scenario: BOM with value-only aggregation
    Given a KiCad schematic file "value_test.kicad_sch" with components:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | R2        | 10K   | R_0603_1608 |
    When I run "jbom bom value_test.kicad_sch --aggregation value_only"
    Then the command exits with code 0
    And the output contains "\"R1, R2\",10K"
    And the line count is 2

  Scenario: Include DNP components
    Given a KiCad schematic file "dnp_test.kicad_sch" with components:
      | Reference | Value | Footprint   | DNP |
      | R1        | 10K   | R_0805_2012 | No  |
      | R2        | 22K   | R_0805_2012 | Yes |
    When I run "jbom bom dnp_test.kicad_sch --include-dnp"
    Then the command exits with code 0
    And the output contains "R1,10K"
    And the output contains "R2,22K"

  Scenario: Exclude DNP components (default)
    Given a KiCad schematic file "dnp_exclude_test.kicad_sch" with DNP components
    When I run "jbom bom dnp_exclude_test.kicad_sch"
    Then the command exits with code 0
    And the output does not contain DNP component references

  Scenario: Include components excluded from BOM
    Given a KiCad schematic file "excluded_test.kicad_sch" with components excluded from BOM
    When I run "jbom bom excluded_test.kicad_sch --include-excluded"
    Then the command exits with code 0
    And the output contains excluded component references

  Scenario: Verbose output
    Given a KiCad schematic file "verbose_test.kicad_sch" with basic components
    When I run "jbom bom verbose_test.kicad_sch -v"
    Then the command exits with code 0
    And the output contains verbose information

  Scenario: Help command
    When I run "jbom bom --help"
    Then the command exits with code 0
    And the output contains "Specify PCB fabricator for field presets"
    And the output contains "--aggregation"
    And the output contains "--inventory"
    And the output contains "--include-dnp"
