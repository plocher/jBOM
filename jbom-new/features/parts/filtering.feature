Feature: Parts List Filtering
  As a hardware developer
  I want to filter components in my parts list
  So that I can customize the parts list for different assembly scenarios

  Background:
    Given the generic fabricator is selected

  Scenario: Exclude DNP components by default
    Given a schematic that contains:
      | Reference | Value | Footprint   | DNP   |
      | R1        | 10K   | R_0805_2012 | false |
      | R2        | 10K   | R_0805_2012 | true  |
      | C1        | 100nF | C_0603_1608 | false |
    When I run jbom command "parts"
    Then the command should succeed
    And the output should contain "R1"
    And the output should contain "C1"
    And the output should not contain "R2"

  Scenario: Include DNP components when requested
    Given a schematic that contains:
      | Reference | Value | Footprint   | DNP   |
      | R1        | 10K   | R_0805_2012 | false |
      | R2        | 10K   | R_0805_2012 | true  |
      | C1        | 100nF | C_0603_1608 | false |
    When I run jbom command "parts --include-dnp"
    Then the command should succeed
    And the output should contain "R1"
    And the output should contain "R2"
    And the output should contain "C1"

  Scenario: Exclude components marked as excluded from BOM by default
    Given a schematic that contains:
      | Reference | Value | Footprint   | In_BOM |
      | R1        | 10K   | R_0805_2012 | true   |
      | R2        | 10K   | R_0805_2012 | false  |
      | C1        | 100nF | C_0603_1608 | true   |
    When I run jbom command "parts"
    Then the command should succeed
    And the output should contain "R1"
    And the output should contain "C1"
    And the output should not contain "R2"

  Scenario: Include excluded components when requested
    Given a schematic that contains:
      | Reference | Value | Footprint   | In_BOM |
      | R1        | 10K   | R_0805_2012 | true   |
      | R2        | 10K   | R_0805_2012 | false  |
      | C1        | 100nF | C_0603_1608 | true   |
    When I run jbom command "parts --include-excluded"
    Then the command should succeed
    And the output should contain "R1"
    And the output should contain "R2"
    And the output should contain "C1"

  Scenario: Exclude power symbols automatically
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | #PWR01    | GND   |             |
      | #PWR02    | VCC   |             |
      | C1        | 100nF | C_0603_1608 |
    When I run jbom command "parts"
    Then the command should succeed
    And the output should contain "R1"
    And the output should contain "C1"
    And the output should not contain "#PWR01"
    And the output should not contain "#PWR02"

  Scenario: Combined filtering options
    Given a schematic that contains:
      | Reference | Value | Footprint   | DNP   | In_BOM |
      | R1        | 10K   | R_0805_2012 | false | true   |
      | R2        | 10K   | R_0805_2012 | true  | true   |
      | R3        | 10K   | R_0805_2012 | false | false  |
      | C1        | 100nF | C_0603_1608 | false | true   |
    When I run jbom command "parts --include-dnp --include-excluded"
    Then the command should succeed
    And the output should contain "R1"
    And the output should contain "R2"
    And the output should contain "R3"
    And the output should contain "C1"
