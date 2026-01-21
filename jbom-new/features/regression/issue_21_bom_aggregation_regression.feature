Feature: Issue #21 BOM Aggregation Regression Tests
  As a developer implementing Issue #21
  I want to capture the current BOM aggregation behavior
  So that I can ensure backward compatibility when removing --aggregation flag

  Background:
    Given the generic fabricator is selected

  @regression @issue-21
  Scenario: Current default aggregation behavior (value_footprint)
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | R2        | 10K   | R_0805_2012 |
      | R3        | 10K   | R_0603_1608 |
      | C1        | 100nF | C_0603_1608 |
      | C2        | 100nF | C_0603_1608 |
    When I run jbom command "bom --aggregation value_footprint"
    Then the command should succeed
    And the output should contain "R1, R2"
    And the output should contain "R_0805_2012"
    And the output should contain "2"
    And the output should contain "R3"
    And the output should contain "R_0603_1608"
    And the output should contain "1"
    And the output should contain "C1, C2"
    And the output should contain "100nF"

  @regression @issue-21
  Scenario: Current value_only aggregation behavior
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | R2        | 10K   | R_0603_1608 |
      | C1        | 100nF | C_0603_1608 |
      | C2        | 100nF | C_0805_2012 |
    When I run jbom command "bom --aggregation value_only"
    Then the command should succeed
    And the output should contain "R1, R2"
    And the output should contain "10K"
    And the output should contain "2"
    And the output should contain "C1, C2"
    And the output should contain "100nF"
    And the output should contain "2"

  @regression @issue-21
  Scenario: Current lib_id_value aggregation behavior
    Given a schematic that contains:
      | Reference | Value | Footprint   | Lib_ID          |
      | R1        | 10K   | R_0805_2012 | Device:R        |
      | R2        | 10K   | R_0603_1608 | Device:R        |
      | R3        | 10K   | R_0805_2012 | Device:R_Small  |
    When I run jbom command "bom --aggregation lib_id_value"
    Then the command should succeed
    And the output should contain "R1, R2"
    And the output should contain "10K"
    And the output should contain "2"
    And the output should contain "R3"
    And the output should contain "1"

  @regression @issue-21
  Scenario: Future BOM behavior - always aggregates by value+package (footprint)
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | R2        | 10K   | R_0805_2012 |
      | R3        | 10K   | R_0603_1608 |
      | C1        | 100nF | C_0603_1608 |
      | C2        | 100nF | C_0603_1608 |
    When I run jbom command "bom"
    Then the command should succeed
    And the output should contain "R1, R2"
    And the output should contain "R_0805_2012"
    And the output should contain "2"
    And the output should contain "R3"
    And the output should contain "R_0603_1608"
    And the output should contain "1"
    And the output should contain "C1, C2"
    And the output should contain "100nF"
    And the output should contain "2"

  @regression @issue-21
  Scenario: BOM command should not accept aggregation flag after Issue #21
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
    When I run jbom command "bom --aggregation value_only"
    Then the command should fail
    And the error output should mention "unrecognized arguments: --aggregation"

  @regression @issue-21
  Scenario: Natural reference sorting in aggregated BOM
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R10       | 10K   | R_0805_2012 |
      | R1        | 10K   | R_0805_2012 |
      | R2        | 10K   | R_0805_2012 |
      | R20       | 10K   | R_0805_2012 |
    When I run jbom command "bom"
    Then the command should succeed
    And the output should contain "R1, R2, R10, R20"
    And the output should contain "4"
