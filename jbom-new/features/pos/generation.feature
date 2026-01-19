Feature: POS Generation
  As a hardware developer
  I want to generate component placement files from my PCB
  So that I can provide data for assembly

  Background:
    Given a clean test workspace

  Scenario: Generate POS CSV from PCB
    Given a KiCad PCB file "board.kicad_pcb" with components:
      | Reference | X(mm) | Y(mm) | Rotation | Side | Footprint        |
      | R1        | 10.0  | 5.0   | 0        | TOP  | R_0805_2012      |
      | C1        | 15.0  | 8.0   | 90       | TOP  | C_0603_1608      |
      | U1        | 25.0  | 12.0  | 180      | TOP  | SOIC-8_3.9x4.9mm |
    When I run "jbom pos board.kicad_pcb"
    Then the command exits with code 0
    And the output contains CSV headers "Reference,X(mm),Y(mm),Rotation,Side,Footprint,Package"

  Scenario: Write POS to file
    Given a KiCad PCB file "output_test.kicad_pcb" with basic components
    When I run "jbom pos output_test.kicad_pcb -o placement.csv"
    Then the command exits with code 0
    And a file named "placement.csv" exists
    And the file "placement.csv" contains valid CSV placement data

  Scenario: Console POS table
    Given a KiCad PCB file "console_test.kicad_pcb" with basic components
    When I run "jbom pos console_test.kicad_pcb -o console"
    Then the command exits with code 0
    And the output contains "Component Placement Data"
    And the output contains a formatted table header with coordinates

  Scenario: Help command
    When I run "jbom pos --help"
    Then the command exits with code 0
    And the output contains "Generate component placement files from KiCad PCB"
    And the output contains "--smd-only"
    And the output contains "--layer"
    And the output contains "--units"

  Scenario: Missing PCB file
    When I run "jbom pos nonexistent.kicad_pcb"
    Then the command exits with code 1
    And the error output contains "PCB file not found"
