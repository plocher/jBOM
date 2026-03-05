Feature: CLI Parts Output Semantics
  As a jBOM user
  I want consistent output handling for the parts command
  So that the CLI is predictable for both humans and automation

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

  Scenario: Default output writes a project-named CSV file
    When I run jbom command "parts"
    Then the command should succeed
    And a file named "project.parts.csv" should exist
    And the file "project.parts.csv" should contain "R1"

  Scenario: Default output is console table (human-first)
    When I run jbom command "parts -o console"
    Then the command should succeed
    And the output should contain "Parts List"
    And the output should contain "R1"

  Scenario: CSV to stdout uses -o -
    When I run jbom command "parts -o -"
    Then the command should succeed
    And the output should contain these fields:
      | Refs | Value | Footprint | Package |
    And the CSV output has rows where:
      | Refs      | Value | Footprint   |
      | R1,R2,R10 | 10K   | R_0805_2012 |
      | C1,C20    | 100nF | C_0603_1608 |

  Scenario: Explicit console output uses -o console
    When I run jbom command "parts -o console"
    Then the command should succeed
    And the output should contain "Parts List"

  Scenario: Custom output filename writes a CSV file
    When I run jbom command "parts -o TestProject.parts.csv"
    Then the command should succeed
    And a file named "TestProject.parts.csv" should exist

  Scenario: Output file named stdout is treated as a literal filename
    When I run jbom command "parts -o stdout"
    Then the command should succeed
    And a file named "stdout" should exist
    And the file "stdout" should contain "R1"

  Scenario: Handle empty schematic with console output
    Given a schematic that contains:
      | Reference | Value | Footprint |
    When I run jbom command "parts -o console"
    Then the command should succeed
    And the output should contain "No components found"
