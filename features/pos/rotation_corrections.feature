Feature: POS Rotation Corrections (DB-driven, Part 1 of 2)
  As a manufacturing engineer
  I want footprint DB rotation corrections applied when requested
  So that I can correct KiCad orientations for fabricators that expect different reel orientations

  Background:
    Given the generic fabricator is selected

  Scenario: Without --apply-corrections, raw KiCad rotations are unchanged
    Given a PCB that contains:
      | Reference | X | Y | Rotation | Side | Footprint   |
      | U1        | 10| 5 | 0        | TOP  | SOT-23_3    |
      | R1        | 15| 8 | 90       | TOP  | R_0805_2012 |
    When I run jbom command "pos -o -"
    Then the command should succeed
    And the CSV output has rows where:
      | Designator | Rotation |
      | U1         | 0        |
      | R1         | 90       |

  Scenario: With --apply-corrections, DB rotation deltas are applied
    Given a PCB that contains:
      | Reference | X | Y | Rotation | Side | Footprint   |
      | U1        | 10| 5 | 0        | TOP  | SOT-23_3    |
      | R1        | 15| 8 | 90       | TOP  | R_0805_2012 |
    When I run jbom command "pos --apply-corrections -o -"
    Then the command should succeed
    # SOT-23_3 matches '^SOT-23' in transformations.csv -> +180 deg delta
    # R_0805_2012 has no matching rule -> delta is 0 (output format changes to float)
    And the CSV output has rows where:
      | Designator | Rotation |
      | U1         | 180.0    |
      | R1         | 90.0     |

  Scenario: With --apply-corrections --verbose, per-component diagnostics are emitted
    Given a PCB that contains:
      | Reference | X | Y | Rotation | Side | Footprint |
      | U1        | 10| 5 | 0        | TOP  | SOT-23_3  |
    When I run jbom command "pos --apply-corrections --verbose -o -"
    Then the command should succeed
    And the output should contain "Corrected U1"

  Scenario: Multiple footprint families each receive their own DB correction
    Given a PCB that contains:
      | Reference | X  | Y  | Rotation | Side | Footprint        |
      | C1        | 10 | 5  | 0        | TOP  | CP_Elec_5x5      |
      | U1        | 20 | 10 | 0        | TOP  | SOIC-8_3.9x4.9mm |
      | R1        | 30 | 15 | 0        | TOP  | R_0805_2012      |
    When I run jbom command "pos --apply-corrections -o -"
    Then the command should succeed
    # CP_Elec_5x5 -> '^CP_Elec_' -> +180 deg
    # SOIC-8_3.9x4.9mm -> '^SOIC-8_' -> +270 deg
    # R_0805_2012 -> no rule -> 0 deg delta (only format changes to float)
    And the CSV output has rows where:
      | Designator | Rotation |
      | C1         | 180.0    |
      | U1         | 270.0    |
      | R1         | 0.0      |
