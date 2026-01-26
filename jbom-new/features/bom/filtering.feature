Feature: BOM Filtering (DNP / Excluded)
  As a hardware developer
  I want to control which components are included in the BOM
  So that I can generate BOMs for different build configurations

  Background:
    Given the generic fabricator is selected

  Scenario: Include DNP components when requested
    Given a schematic that contains:
      | Reference | Value | Footprint   | DNP |
      | R1        | 10K   | R_0805_2012 | No  |
      | R2        | 22K   | R_0805_2012 | Yes |
    When I run jbom command "bom --include-dnp -o -"
    Then the command should succeed
    And the CSV output has a row where
      | Reference | Value |
      | R2        | 22K   |

  Scenario: Exclude DNP components by default
    Given a schematic that contains:
      | Reference | Value | Footprint   | DNP |
      | R1        | 10K   | R_0805_2012 | No  |
      | R2        | 22K   | R_0805_2012 | Yes |
    When I run jbom command "bom -o -"
    Then the command should succeed
    And the output should not contain "R2"

  Scenario: Include components excluded from BOM when requested
    Given a schematic that contains:
      | Reference | Value | Footprint   | ExcludeFromBOM |
      | R1        | 10K   | R_0805_2012 | No             |
      | R2        | 22K   | R_0805_2012 | Yes            |
    When I run jbom command "bom --include-excluded -o -"
    Then the command should succeed
    And the CSV output has a row where
      | Reference | Value |
      | R2        | 22K   |
