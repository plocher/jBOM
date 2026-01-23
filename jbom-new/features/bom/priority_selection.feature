Feature: BOM Priority and Selection Rules
  As a hardware developer
  I want deterministic BOM grouping and selection behavior
  So that results are predictable and reviewable

  Background:
    Given the generic fabricator is selected

  # Deterministic ordering of grouped references (natural numeric order)
  Scenario: Grouped references are listed in natural order
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R10       | 10K   | R_0805_2012 |
      | R2        | 10K   | R_0805_2012 |
      | R1        | 10K   | R_0805_2012 |
    When I run jbom command "bom -o -"
    Then the command should succeed
    And the CSV output has a row where
      | References       | Value | Footprint   | Quantity |
      | R1, R2, R10      | 10K   | R_0805_2012 | 3        |

  # Deterministic line-item ordering for readability (Value then Footprint)
  Scenario: Line items are ordered by Value then Footprint
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 1K    | R_0603_1608 |
      | R2        | 10K   | R_0805_2012 |
      | R3        | 1K    | R_0805_2012 |
    When I run jbom command "bom --aggregation value_footprint"
    Then the command should succeed
    And the output should contain "References,Value,Footprint,Quantity"
    And the output should contain "R1,  R3"  # grouped by 1K should appear together
