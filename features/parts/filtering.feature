Feature: Parts List Filtering
  As a hardware developer
  I want to filter components in my parts list
  So that I can customize the parts list for different assembly scenarios

  Background:
    Given a jBOM CSV sandbox
    And the generic fabricator is selected

  Scenario: Exclude DNP components by default
    Given a schematic that contains:
      | Reference | Value | Footprint   | DNP   |
      | R1        | 10K   | R_0805_2012 | No    |
      | R2        | 10K   | R_0805_2012 | Yes   |
      | C1        | 100nF | C_0603_1608 | No    |
    When I run jbom command "parts"
    Then the command should succeed
    And the CSV output has rows where:
      | Refs | Value |
      | R1   | 10K   |
      | C1   | 100nF |
    And the CSV output does not contain components where:
      | Refs |
      | R2   |

  Scenario: Include DNP components when requested
    Given a schematic that contains:
      | Reference | Value | Footprint   | DNP   |
      | R1        | 10K   | R_0805_2012 | No    |
      | R2        | 10K   | R_0805_2012 | Yes   |
      | C1        | 100nF | C_0603_1608 | No    |
    When I run jbom command "parts --include-dnp"
    Then the command should succeed
    And the CSV output has rows where:
      | Refs  | Value |
      | R1,R2 | 10K   |
      | C1    | 100nF |

  Scenario: Exclude components marked as excluded from BOM by default
    Given a schematic that contains:
      | Reference | Value | Footprint   | ExcludeFromBOM |
      | R1        | 10K   | R_0805_2012 | No             |
      | R2        | 10K   | R_0805_2012 | Yes            |
      | C1        | 100nF | C_0603_1608 | No             |
    When I run jbom command "parts"
    Then the command should succeed
    And the CSV output has rows where:
      | Refs | Value |
      | R1   | 10K   |
      | C1   | 100nF |
    And the CSV output does not contain components where:
      | Refs |
      | R2   |

  Scenario: Include excluded components when requested
    Given a schematic that contains:
      | Reference | Value | Footprint   | ExcludeFromBOM |
      | R1        | 10K   | R_0805_2012 | No             |
      | R2        | 10K   | R_0805_2012 | Yes            |
      | C1        | 100nF | C_0603_1608 | No             |
    When I run jbom command "parts --include-excluded"
    Then the command should succeed
    And the CSV output has rows where:
      | Refs  | Value |
      | R1,R2 | 10K   |
      | C1    | 100nF |

  Scenario: Exclude virtual symbols automatically
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
      | Refs  |
      | #PWR01 |
      | #PWR02 |

  Scenario: Include virtual symbols with --include-all
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | #PWR01    | GND   |             |
      | #PWR02    | VCC   |             |
      | C1        | 100nF | C_0603_1608 |
    When I run jbom command "parts --include-all"
    Then the command should succeed
    And the CSV output has rows where:
      | Refs   | Value |
      | R1     | 10K   |
      | C1     | 100nF |
      | #PWR01 | GND   |
      | #PWR02 | VCC   |

  Scenario: Test both DNP and ExcludeFromBOM flags work independently
    Given a schematic that contains:
      | Reference | Value | Footprint   | DNP   | ExcludeFromBOM |
      | R1        | 10K   | R_0805_2012 | No    | No             |
      | R2        | 10K   | R_0805_2012 | Yes   | No             |
      | R3        | 10K   | R_0805_2012 | No    | Yes            |
      | C1        | 100nF | C_0603_1608 | No    | No             |
    When I run jbom command "parts --include-dnp --include-excluded"
    Then the command should succeed
    And the CSV output has rows where:
      | Refs     | Value |
      | R1,R2,R3 | 10K   |
      | C1       | 100nF |

  Scenario: Include only DNP components (exclude ExcludeFromBOM)
    Given a schematic that contains:
      | Reference | Value | Footprint   | DNP   | ExcludeFromBOM |
      | R1        | 10K   | R_0805_2012 | No    | No             |
      | R2        | 10K   | R_0805_2012 | Yes   | No             |
      | R3        | 10K   | R_0805_2012 | No    | Yes            |
    When I run jbom command "parts --include-dnp"
    Then the command should succeed
    And the CSV output has rows where:
      | Refs  | Value |
      | R1,R2 | 10K   |
    And the CSV output does not contain components where:
      | Refs |
      | R3   |

  Scenario: Include only ExcludeFromBOM components (exclude DNP)
    Given a schematic that contains:
      | Reference | Value | Footprint   | DNP   | ExcludeFromBOM |
      | R1        | 10K   | R_0805_2012 | No    | No             |
      | R2        | 10K   | R_0805_2012 | Yes   | No             |
      | R3        | 10K   | R_0805_2012 | No    | Yes            |
    When I run jbom command "parts --include-excluded"
    Then the command should succeed
    And the CSV output has rows where:
      | Refs  | Value |
      | R1,R3 | 10K   |
    And the CSV output does not contain components where:
      | Refs |
      | R2   |
