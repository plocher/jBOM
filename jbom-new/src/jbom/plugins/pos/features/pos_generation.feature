Feature: POS Generation
  As a jBOM user
  I want to generate placement files from KiCad PCB
  So that I can send them to PCB assembly services

  Background: Base Test Data Foundation
    Given a clean test environment
    And a KiCad project named "PosTestProject"

  Scenario: Generate basic POS file with components
    Given the PCB is populated with components:
      | Reference | Value   | Package | Rotation | X    | Y     | Layer | Footprint       |
      | R1        | 1K      | 0603    | 0        | 25.4 | 25.4  | Top   | R_0603_1608Metric |
      | C1        | 0.1uF   | 0603    | 90       | 50.8 | 25.4  | Top   | C_0603_1608Metric |
      | U1        | NE555   | SOIC-8  | 180      | 76.2 | 25.4  | Top   | SOIC-8_3.9x4.9mm |
      | R2        | 2K2     | 0603    | 270      | 101.6| 25.4  | Top   | R_0603_1608Metric |
    When I generate a POS file with no options
    Then the POS file is created successfully
    And the POS contains 4 components
    And the POS has columns: Designator, Val, Package, Mid X, Mid Y, Rotation, Layer

  Scenario: Generate POS to stdout
    Given the PCB is populated with components:
      | Reference | Value   | Package | Rotation | X    | Y     | Layer | Footprint         |
      | R1        | 10K     | 0603    | 0        | 25.4 | 25.4  | Top   | R_0603_1608Metric |
    When I generate a POS file with output to stdout
    Then the output contains CSV data
    And the output contains component "R1"

  Scenario: pos -o console prints human-readable table
    Given the PCB is populated with components:
      | Reference | Value   | Package | Rotation | X    | Y     | Layer | Footprint         |
      | C10       | 1uF     | 0603    | 0        | 10.0 | 12.3  | Bottom| C_0603_1608Metric |
    When I generate a POS file with output to console
    Then the console output contains a placement table
    And the console output mentions component "C10"

  Scenario: Mixed data: long footprints, mixed TOP/BOT, SMD/THT mapping
    Given the PCB is populated with components:
      | Reference | Value | Package | Rotation | X   | Y   | Layer  | Footprint                               | Mount         |
      | U1        | MCU   | QFN48  | 0        | 0.0 | 0.0 | Top    | QFN-48_7x7mm_P0.5mm_ExposedPad           | SMD           |
      | J1        | HDR   | HDR2   | 0        | 5.0 | 8.0 | Bottom | PinHeader_1x02_P2.54mm_Vertical_VeryLong | THROUGH_HOLE  |
      | R100      | 10K   | 0603   | 90       | 2.5 | 1.0 | Top    | R_0603_1608Metric                        | SMD           |
    When I generate a POS file with output to console
    Then the console output contains a placement table
    And the console output mentions component "U1"
    And the console output mentions component "J1"

  Scenario: pos with no options writes a default file, not stdout
    Given the PCB is populated with components:
      | Reference | Value | Package | Rotation | X   | Y   | Layer | Footprint         |
      | R5        | 1K    | 0603   | 0        | 1.0 | 2.0 | Top   | R_0603_1608Metric |
    When I run the POS tool with defaults
    Then a default POS file is created in the project directory
    And no CSV was printed to stdout

  Scenario: Handle missing PCB file
    When I attempt to generate POS from nonexistent PCB
    Then an error is reported
    And the error mentions the missing file
