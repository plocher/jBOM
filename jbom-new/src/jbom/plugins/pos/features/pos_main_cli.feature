Feature: POS main CLI command
  As a user
  I want a top-level 'pos' command that works with sensible defaults

  Scenario: No KiCad files present (main CLI)
    Given a clean test environment
    And I am in an empty project directory
    When I run "python -m jbom.cli.main pos" in the project directory
    Then the command exits with code 2
    And stderr contains "No .kicad_pcb file"

  Scenario: Project and PCB present, no arguments (main CLI)
    Given a clean test environment
    And a KiCad project named "MainCliProject"
    And the PCB is populated with components:
      | Reference | Value | Package | Rotation | X   | Y   | Layer | Footprint         |
      | R1        | 10K   | 0603   | 0        | 1.0 | 2.0 | Top   | R_0603_1608Metric |
    And a KiCad project file exists in the project directory
    When I run "python -m jbom.cli.main pos" in the project directory
    Then the command exits with code 0
    And a file named "MainCliProject.pos.csv" exists in the project directory
