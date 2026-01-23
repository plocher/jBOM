Feature: Parts List Generation (Core Functionality)
  As a hardware developer
  I want to generate a Parts List from KiCad schematics
  So that I can see every component instance for PCB assembly

  Background:
    Given the generic fabricator is selected
    And a schematic that contains:
      | Reference | Value | Footprint         |
      | R1        | 10K   | R_0805_2012       |
      | R2        | 10K   | R_0805_2012       |
      | R10       | 10K   | R_0805_2012       |
      | C1        | 100nF | C_0603_1608       |
      | C20       | 100nF | C_0603_1608       |
      | U1        | LM358 | SOIC-8_3.9x4.9mm |

  Scenario: Generate basic parts list to stdout (CSV format)
    When I run jbom command "parts"
    Then the command should succeed
    And the output should contain "R1"
    And the output should contain "10K"
    And the output should contain "C1"
    And the output should contain "100nF"
    And the output should contain "U1"
    And the output should contain "LM358"

  Scenario: Parts list shows individual components (no aggregation)
    When I run jbom command "parts"
    Then the command should succeed
    And the output should contain "R1"
    And the output should contain "R2"
    And the output should contain "R10"
    And the output should not contain "R1, R2"
    And the output should not contain "Quantity"

  Scenario: Natural reference sorting in parts list
    When I run jbom command "parts"
    Then the command should succeed
    And R1 appears before R2 in the output
    And R2 appears before R10 in the output
    And C1 appears before C20 in the output

  Scenario: Generate parts list to specific output file
    When I run jbom command "parts -o custom_parts.csv"
    Then the command should succeed
    And a file named "custom_parts.csv" should exist
    And the file "custom_parts.csv" should contain "R1"
    And the file "custom_parts.csv" should contain "C1"

  Scenario: Generate parts list with console table output
    When I run jbom command "parts -o console"
    Then the command should succeed
    And the output should contain "Parts List"
    And the output should contain "R1"
    And the output should contain "C1"

  Scenario: Custom output filename with project-based default
    Given a schematic named "TestProject.kicad_sch" that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
    When I run jbom command "parts -o TestProject.parts.csv"
    Then the command should succeed
    And a file named "TestProject.parts.csv" should exist

  Scenario: Handle empty schematic
    Given a schematic that contains:
      | Reference | Value | Footprint |
    When I run jbom command "parts -o console"
    Then the command should succeed
    And the output should contain "No components found"
