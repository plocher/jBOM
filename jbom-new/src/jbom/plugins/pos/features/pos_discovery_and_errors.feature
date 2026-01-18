Feature: POS discovery and error behaviors
  As a user
  I want predictable discovery and clear errors from the main CLI

  Scenario: Multiple PCB files - prefer directory-matching name
    Given a clean test environment
    And a KiCad project named "MatchDir"
    And the PCB is populated with components:
      | Reference | Value | Package | Rotation | X   | Y   | Layer | Footprint         |
      | R1        | 1K    | 0603   | 0        | 1.0 | 2.0 | Top   | R_0603_1608Metric |
    And an extra PCB file named "other.kicad_pcb" exists (empty valid)
    When I run "python -m jbom.cli.main pos" in the project directory
    Then the command exits with code 0
    And a file named "MatchDir.pos.csv" exists in the project directory

  Scenario: Autosave-only PCB file emits warning and is used
    Given a clean test environment
    And a KiCad project named "AutoSaveOnly"
    And the PCB is populated with components:
      | Reference | Value | Package | Rotation | X   | Y   | Layer | Footprint         |
      | C1        | 0.1uF | 0603   | 0        | 1.0 | 2.0 | Top   | C_0603_1608Metric |
    And the PCB is saved only as autosave
    When I run "python -m jbom.cli.main pos --stdout" in the project directory
    Then the command exits with code 0
    And stdout contains "C1"

  Scenario: Nonexistent PCB argument returns error
    Given a clean test environment
    And I am in an empty project directory
    When I run "python -m jbom.cli.main pos missing.kicad_pcb" in the project directory
    Then the command exits with code 2
    And stderr contains "PCB file not found"

  Scenario: Output path is a directory - write failure surfaces as error
    Given a clean test environment
    And a KiCad project named "BadOut"
    And the PCB is populated with components:
      | Reference | Value | Package | Rotation | X   | Y   | Layer | Footprint         |
      | U1        | MCU   | QFN48   | 0        | 0.0 | 0.0 | Top   | QFN-48_7x7mm      |
    When I run "python -m jbom.cli.main pos -o ." in the project directory
    Then the command exits with code 1
    And stderr contains "Error:"
