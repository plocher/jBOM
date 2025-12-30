Feature: Component Placement (POS/CPL) Generation
  As a PCB designer
  I want to generate component placement files from my KiCad PCB
  So that PCB assembly services can accurately place components on my board

  Background:
    Given a KiCad project named "SimpleProject" with a PCB file

  Scenario: Generate basic POS file
    Given the PCB contains placed components
      | Reference | X_mm | Y_mm | Rotation | Side | Footprint     | Type |
      | R1        | 10.0 | 20.0 | 0        | Top  | R_0603_1608   | SMD  |
      | C1        | 15.0 | 25.0 | 90       | Top  | C_0603_1608   | SMD  |
      | U1        | 30.0 | 40.0 | 0        | Top  | QFN-32        | SMD  |
    When I generate a POS file
    Then the POS contains 3 components with columns "Reference,X,Y,Rotation,Side,Footprint"

  Scenario: Generate JLCPCB format POS
    Given the PCB contains components
      | Reference | X_mm | Y_mm | Rotation | Side | Footprint     | Type |
      | R1        | 10.0 | 20.0 | 0        | Top  | R_0603_1608   | SMD  |
      | J1        | 5.0  | 5.0  | 0        | Top  | PinHeader_2x5 | THT  |
    When I generate JLCPCB format POS
    Then the POS contains only R1 in JLCPCB format with columns matching the JLCPCB fabricator configuration

  Scenario: Filter SMD components only
    Given the PCB contains components
      | Reference | X_mm | Y_mm | Rotation | Side | Footprint     | Type |
      | R1        | 10.0 | 20.0 | 0        | Top  | R_0603_1608   | SMD  |
      | C1        | 15.0 | 25.0 | 90       | Top  | C_0603_1608   | SMD  |
      | J1        | 5.0  | 5.0  | 0        | Top  | PinHeader_2x5 | THT  |
    When I generate POS with SMD-only filter
    Then the POS contains R1 and C1 but excludes J1 through-hole component

  Scenario: Filter by board layer
    Given the PCB contains components
      | Reference | X_mm | Y_mm | Rotation | Side   | Footprint   | Type |
      | R1        | 10.0 | 20.0 | 0        | Top    | R_0603_1608 | SMD  |
      | R2        | 15.0 | 25.0 | 180      | Bottom | R_0603_1608 | SMD  |
    When I generate POS with top-side filter
    Then the POS contains R1 on top side but excludes R2 bottom-side component

  Scenario: Generate POS via API
    Given the PCB contains components
      | Reference | X_mm | Y_mm | Rotation | Side | Footprint   | Type |
      | R1        | 10.0 | 20.0 | 0        | Top  | R_0603_1608 | SMD  |
      | C1        | 15.0 | 25.0 | 90       | Top  | C_0603_1608 | SMD  |
    When I use the API to generate POS
    Then the API returns POSResult with 2 components and coordinate data in millimeters

  Scenario: Handle different coordinate units
    Given the PCB contains components
      | Reference | X_mm  | Y_mm  | Rotation | Side | Footprint   | Type |
      | R1        | 25.4  | 50.8  | 0        | Top  | R_0603_1608 | SMD  |
    When I generate POS with inch units
    Then the POS coordinates show R1 at (1.000, 2.000) inches with 3 decimal precision

  Scenario: Use auxiliary origin for coordinates
    Given the PCB has auxiliary origin at (10.0, 10.0) mm
    And the PCB contains components
      | Reference | X_mm | Y_mm | Rotation | Side | Footprint   | Type |
      | R1        | 20.0 | 30.0 | 0        | Top  | R_0603_1608 | SMD  |
    When I generate POS using auxiliary origin
    Then the POS coordinates show R1 at (10.0, 20.0) relative to auxiliary origin
