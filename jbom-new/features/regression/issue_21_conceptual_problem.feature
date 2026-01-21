Feature: Issue #21 Conceptual Problem - BOM vs Parts List Distinction
  As a developer implementing Issue #21
  I want to demonstrate the conceptual confusion caused by --aggregation flag
  So that the solution clearly separates BOM (procurement) from Parts List (assembly)

  Background:
    Given the generic fabricator is selected

  @regression @issue-21 @problem-solved
  Scenario: Problem solved - BOM no longer accepts confusing aggregation options
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | R2        | 10K   | R_0603_1608 |
      | C1        | 100nF | C_0603_1608 |
    When I run jbom command "bom --aggregation value_only"
    Then the command should fail
    And the error output should mention "unrecognized arguments: --aggregation"
    # Problem solved: The confusing --aggregation flag is gone!

  @regression @issue-21 @problem-solved
  Scenario: Problem solved - Parts command now provides individual component listing
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | R2        | 10K   | R_0805_2012 |
      | R3        | 10K   | R_0603_1608 |
    When I run jbom command "parts"
    Then the command should succeed
    # Problem solved: Parts command gives you individual component listing for assembly
    And the output should contain "R1"
    And the output should contain "R2"
    And the output should contain "R3"
    And the output should not contain "R1, R2"

  @regression @issue-21 @solution
  Scenario: Solution - BOM always aggregates properly for procurement
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | R2        | 10K   | R_0805_2012 |
      | R3        | 10K   | R_0603_1608 |
      | C1        | 100nF | C_0603_1608 |
      | C2        | 100nF | C_0603_1608 |
    When I run jbom command "bom"
    Then the command should succeed
    # BOM aggregates by value+package for proper procurement
    And the output should contain "R1, R2"
    And the output should contain "2"
    And the output should contain "R3"
    And the output should contain "1"
    And the output should contain "C1, C2"
    And the output should contain "2"

  @regression @issue-21 @solution
  Scenario: Solution - Parts list shows individual components for assembly
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | R2        | 10K   | R_0805_2012 |
      | R3        | 10K   | R_0603_1608 |
    When I run jbom command "parts"
    Then the command should succeed
    # Parts list shows every individual component for assembly
    And the output should contain "R1"
    And the output should contain "R2"
    And the output should contain "R3"
    And the output should not contain "R1, R2"
    And the output should not contain "Quantity"

  @regression @issue-21 @solution
  Scenario: Solution - No more confusing aggregation options
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
    When I run jbom command "bom --aggregation value_only"
    Then the command should fail
    And the error output should mention "unrecognized arguments: --aggregation"

  @regression @issue-21 @solution
  Scenario: Solution - Clear command semantics in help
    When I run jbom command "bom --help"
    Then the command should succeed
    And the output should contain "Bill of Materials"
    And the output should not contain "aggregation"
    And the help text should indicate BOM is always aggregated

  @regression @issue-21 @solution
  Scenario: Solution - Parts command available in main help
    When I run jbom command "--help"
    Then the command should succeed
    And the output should contain "parts"
    And the help text should show both bom and parts commands
