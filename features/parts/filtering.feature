Feature: Parts List Filtering
  As a hardware developer
  I want the parts list to enumerate design components
  So that I have a complete electro-mechanical inventory of the schematic

  Background:
    Given a jBOM CSV sandbox
    And the generic fabricator is selected

  Scenario: Parts list includes DNP components by default
    # Parts list is a design inventory: DNP parts ARE in the design.
    # They appear without a dedicated dnp column (parts is electro-mechanical).
    Given a schematic that contains:
      | Reference | Value | Footprint   | DNP   |
      | R1        | 10K   | R_0805_2012 | No    |
      | R2        | 10K   | R_0805_2012 | Yes   |
      | C1        | 100nF | C_0603_1608 | No    |
    When I run jbom command "parts"
    Then the command should succeed
    And the CSV output has rows where:
      | Refs  | Value |
      | R1,R2 | 10K   |
      | C1    | 100nF |

  Scenario: Parts list excludes components marked exclude_from_bom
    # Components explicitly flagged out of the BOM (mounting holes, logos,
    # fiducials) are excluded. No flag can override this; use jbom audit
    # for full-board inventory.
    Given a schematic that contains:
      | Reference | Value | Footprint   | ExcludeFromBOM |
      | R1        | 10K   | R_0805_2012 | No             |
      | MH1       | ~     | R_0805_2012 | Yes            |
      | C1        | 100nF | C_0603_1608 | No             |
    When I run jbom command "parts"
    Then the command should succeed
    And the CSV output has rows where:
      | Refs | Value |
      | R1   | 10K   |
      | C1   | 100nF |
    And the CSV output does not contain components where:
      | Refs |
      | MH1  |

  Scenario: Parts list excludes virtual symbols automatically
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | #PWR01    | GND   |             |
      | #PWR02    | VCC   |             |
      | C1        | 100nF | C_0603_1608 |
    When I run jbom command "parts"
    Then the command should succeed
    And the CSV output has rows where:
      | Refs | Value |
      | R1   | 10K   |
      | C1   | 100nF |
    And the CSV output does not contain components where:
      | Refs   |
      | #PWR01 |
      | #PWR02 |

  Scenario: Parts CLI no longer accepts removed filter flags
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
    When I run jbom command "parts --include-dnp"
    Then the command should fail
