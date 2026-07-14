Feature: BOM diagnostics honor -q/--quiet (Issue #375)
  As a scripting/automation user
  I want -q/--quiet to actually suppress info/warning diagnostics
  So that I can pipe jbom bom's stdout without unwanted noise while still seeing real errors

  Background:
    Given the generic fabricator is selected
    And a PCB that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |

  Scenario: Missing-fields warning appears on stderr without -q, stdout stays pure CSV
    When I run jbom command "bom -f datasheet_name -o -"
    Then the command should succeed
    And the stderr output should contain "Warning: Missing important generic fields"
    And the stdout output should be valid CSV
    And the stdout output should not contain "Warning: Missing important generic fields"

  Scenario: Missing-fields warning is suppressed with -q
    When I run jbom command "-q bom -f datasheet_name -o -"
    Then the command should succeed
    And the stderr output should not contain "Warning: Missing important generic fields"
    And the stdout output should be valid CSV

  Scenario: Errors still print with -q
    When I run jbom command "-q bom --inventory nonexistent.csv -o console"
    Then the command should fail
    And the stderr output should contain "Error: Inventory file not found: nonexistent.csv"

  Scenario: Verbose info diagnostics are suppressed with -q
    When I run jbom command "-q bom -f reference,value -v -o -"
    Then the command should succeed
    And the stderr output should not contain "Selected fields:"
