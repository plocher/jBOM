Feature: Inventory no-aggregate export
  As a hardware designer
  I want one inventory row per component instance
  So that I can triage sparse metadata with category sub-headers

  Background:
    Given a schematic that contains:
      | UUID    | Reference | Value | Footprint                           | LibID    |
      | uuid-r2 | R2        | 10K   | Resistor_SMD:R_0603_1608Metric     | Device:R |
      | uuid-c1 | C1        | 100nF | Capacitor_SMD:C_0603_1608Metric    | Device:C |
      | uuid-r1 | R1        | 10K   | Resistor_SMD:R_0603_1608Metric     | Device:R |

  Scenario: no-aggregate output uses Project ProjectName UUID SourceFile Refs Category IPN leading columns
    When I run jbom command "inventory --no-aggregate -o noagg.csv"
    Then the command should succeed
    And the file "noagg.csv" contains "Project,ProjectName,UUID,SourceFile,Refs,Category,IPN"

  Scenario: no-aggregate output emits one data row per component instance
    When I run jbom command "inventory --no-aggregate -o noagg.csv"
    Then the command should succeed
    And the file "noagg.csv" contains exactly 3 no-aggregate data rows

  Scenario: no-aggregate output inserts category sub-header sentinel rows
    When I run jbom command "inventory --no-aggregate -o noagg.csv"
    Then the command should succeed
    And the file "noagg.csv" contains a no-aggregate sub-header row for each category
    And the no-aggregate sub-header row in "noagg.csv" marks required and optional fields
