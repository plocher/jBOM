Feature: BOM Aggregation
  As a hardware developer
  I want to control BOM aggregation strategies
  So that the BOM matches my sourcing preferences

  Background:
    Given a clean test workspace

  Scenario: Aggregation by value and footprint
    Given a KiCad schematic file "aggregation.kicad_sch" with components:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | R2        | 10K   | R_0805_2012 |
      | R3        | 10K   | R_0603_1608 |
    When I run "jbom bom aggregation.kicad_sch --aggregation value_footprint"
    Then the command exits with code 0
    And the output contains "\"R1, R2\",10K,R_0805_2012,2"
    And the output contains "R3,10K,R_0603_1608,1"

  Scenario: Aggregation by value only
    Given a KiCad schematic file "value_only.kicad_sch" with components:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | R2        | 10K   | R_0603_1608 |
    When I run "jbom bom value_only.kicad_sch --aggregation value_only"
    Then the command exits with code 0
    And the output contains "\"R1, R2\",10K"
    And the line count is 2
