Feature: BOM Priority and Selection Rules
  As a hardware developer
  I want deterministic BOM grouping and selection behavior
  So that results are predictable and reviewable

  Background:
    Given a clean test workspace

  # Deterministic ordering of grouped references (natural numeric order)
  Scenario: Grouped references are listed in natural order
    Given a KiCad schematic file "ordering.kicad_sch" with components:
      | Reference | Value | Footprint   |
      | R10       | 10K   | R_0805_2012 |
      | R2        | 10K   | R_0805_2012 |
      | R1        | 10K   | R_0805_2012 |
    When I run "jbom bom ordering.kicad_sch --aggregation value_footprint --generic"
    Then the command exits with code 0
    And the CSV output has a row where
      | References       | Value | Footprint   | Quantity |
      | R1, R2, R10      | 10K   | R_0805_2012 | 3        |

  # Deterministic line-item ordering for readability (Value then Footprint)
  @wip
  Scenario: Line items are ordered by Value then Footprint
    Given a KiCad schematic file "line_order.kicad_sch" with components:
      | Reference | Value | Footprint   |
      | R1        | 1K    | R_0603_1608 |
      | R2        | 10K   | R_0805_2012 |
      | R3        | 1K    | R_0805_2012 |
    When I run "jbom bom line_order.kicad_sch --aggregation value_footprint --generic"
    Then the command exits with code 0
    And the output contains "References,Value,Footprint,Quantity"
    And the output contains "R1,  R3"  # grouped by 1K should appear together
