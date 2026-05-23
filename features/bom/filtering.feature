Feature: BOM Filtering (DNP / Excluded)
  As a hardware developer
  I want the BOM to reflect the full design intent
  So that assembly houses have explicit DNP declarations per IPC J-STD-001

  Background:
    Given the generic fabricator is selected

  Scenario: BOM includes DNP rows with explicit DNP marker by default
    # IPC J-STD-001 expects DNPs to be declared in writing so the assembly
    # operator can tell empty pads are intentional. Procurement consumers
    # filter the dnp column themselves.
    Given a PCB that contains:
      | Reference | Value   | Footprint   | DNP |
      | R1        | 10K     | R_0805_2012 | No  |
      | R2        | No_Load | R_0805_2012 | Yes |
    When I run jbom command "bom -o -"
    Then the command should succeed
    And the CSV output has rows where:
      | Reference | Value   | DNP |
      | R1        | 10K     |     |
      | R2        | No_Load | DNP |

  Scenario: BOM keeps populated and DNP variants of the same part on separate rows
    # Aggregation key includes the DNP boolean so qty is never inflated by
    # merging in a DNP row.
    Given a PCB that contains:
      | Reference | Value | Footprint   | DNP |
      | R1        | 10K   | R_0805_2012 | No  |
      | R2        | 10K   | R_0805_2012 | Yes |
    When I run jbom command "bom -o -"
    Then the command should succeed
    And the CSV output has rows where:
      | Reference | Value | Quantity | DNP |
      | R1        | 10K   | 1        |     |
      | R2        | 10K   | 1        | DNP |

  Scenario: BOM drops exclude_from_bom refs unconditionally
    # Mounting holes, fiducials, OSHW logos etc. carry exclude_from_bom on
    # the PCB. Under the simplified contract there is no flag to override
    # this; full-board audit lives in `jbom audit`.
    Given a PCB that contains:
      | Reference | Value | Footprint                | ExcludeFromBOM |
      | R1        | 10K   | R_0805_2012              | No             |
      | MH1       | ~     | MountingHole_3.2mm_M3    | Yes            |
    When I run jbom command "bom -o -"
    Then the command should succeed
    And the output should contain "R1"
    And the output should not contain "MH1"

  Scenario: POS unconditionally drops DNP rows
    # The mandatory companion BOM declares DNP explicitly. The POS file is
    # exclusively "place these components" — adding non-placeable rows
    # makes it inconsistent with the P&P machine's input contract.
    Given a PCB that contains:
      | Reference | Value | Footprint   | X | Y | Rotation | Side | DNP |
      | R1        | 10K   | R_0805_2012 | 5 | 5 | 0        | TOP  | No  |
      | R2        | 10K   | R_0805_2012 | 6 | 5 | 0        | TOP  | Yes |
    When I run jbom command "pos -o -"
    Then the command should succeed
    And the output should contain "R1"
    And the output should not contain "R2"

  Scenario: BOM CLI no longer accepts the removed filter flags
    Given a PCB that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
    When I run jbom command "bom --include-dnp -o -"
    Then the command should fail

  Scenario: POS CLI no longer accepts --include-dnp
    Given a PCB that contains:
      | Reference | Value | Footprint   | X | Y | Rotation | Side |
      | R1        | 10K   | R_0805_2012 | 5 | 5 | 0        | TOP  |
    When I run jbom command "pos --include-dnp -o -"
    Then the command should fail
