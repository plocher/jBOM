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
      | Reference | Value   | Package | Rotation | X    | Y     | Layer | Footprint       |
      | R1        | 10K     | 0603    | 0        | 25.4 | 25.4  | Top   | R_0603_1608Metric |
    When I generate a POS file with output to stdout
    Then the output contains CSV data
    And the output contains component "R1"

  Scenario: Handle missing PCB file
    When I attempt to generate POS from nonexistent PCB
    Then an error is reported
    And the error mentions the missing file
