Feature: BOM Aggregation
  As a hardware developer
  I want to control BOM aggregation strategies
  So that the BOM matches my sourcing preferences

  Background:
    Given the generic fabricator is selected

  Scenario: Aggregation by value and footprint
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | R2        | 10K   | R_0805_2012 |
      | R3        | 10K   | R_0603_1608 |
    When I run jbom command "bom --aggregation value_footprint"
    Then the command should succeed
    And the CSV output has a row where
      | References | Value | Footprint   | Quantity |
      | R1, R2     | 10K   | R_0805_2012 | 2        |
    And the CSV output has a row where
      | References | Value | Footprint   | Quantity |
      | R3         | 10K   | R_0603_1608 | 1        |

  Scenario: Aggregation by value only
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | R2        | 10K   | R_0603_1608 |
    When I run jbom command "bom --aggregation value_only"
    Then the command should succeed
    And the CSV output has a row where
      | References | Value | Footprint   | Quantity |
      | "R1, R2"   | 10K   |             | 2        |
