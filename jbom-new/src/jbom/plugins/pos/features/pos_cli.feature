Feature: POS CLI default behavior
  As a user
  I want simple default behavior when running jbom pos with no arguments

  Scenario: No KiCad files present
    Given a clean test environment
    And I am in an empty project directory
    When I run "python -m jbom.cli.pos_cli" in the project directory
    Then the command exits with code 2
    And stderr contains "No .kicad_pcb file"

  Scenario: Project and PCB present, no arguments
    Given a clean test environment
    And a KiCad project named "CliPosProject"
    And the PCB is populated with components:
      | Reference | Value | Package | Rotation | X   | Y   | Layer | Footprint         |
      | R1        | 10K   | 0603   | 0        | 1.0 | 2.0 | Top   | R_0603_1608Metric |
    And a KiCad project file exists in the project directory
    When I run "python -m jbom.cli.pos_cli" in the project directory
    Then the command exits with code 0
    And a file named "CliPosProject.pos.csv" exists in the project directory
