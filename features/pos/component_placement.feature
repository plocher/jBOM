Feature: Component Placement (POS/CPL) Generation
  As a PCB designer
  I want to generate component placement files from my KiCad PCB
  So that PCB assembly services can accurately place components on my board

  # TECHNICAL CONTEXT - Component Rotation Standards:
  #
  # IPC-7352 STANDARD:
  # - Defines zero degrees orientation with Pin 1 in top-left position
  # - KiCad libraries follow this standard (pin 1 in top left)
  # - Rotation == 0 represents standard IPC component orientation
  #
  # Component rotation angles generally increase in a counter-clockwise direction.
  #
  # FABRICATOR ROTATION COMPLEXITY:
  #
  # JLCPCB "REEL ZERO" PROBLEM:
  # - JLCPCB defines rotation based on how the component sits in the tape/feeder
  # - This is intuitive but creates major challenges:
  #   * Passive components (R, C) typically consistent per footprint
  #   * ICs have complex variations based on packaging format and supplier
  #   * Same chip in different packages (SOIC vs DIP vs QFN) requires different rotations
  #   * Multiple suppliers for same IC may use different tape orientations
  #   * Through-hole vs surface-mount versions often have different orientations
  #
  # WHY THIS FEATURE IS "HARD":
  # - Cannot use simple mathematical rotation mapping (KiCad angle + offset)
  # - Requires per-part lookup table based on:
  #   * Manufacturer Part Number (MPN)
  #   * Supplier/Distributor Part Number (DPN)
  #   * Packaging/tape orientation from datasheet
  #   * Specific reel/tray configuration
  #
  # FABRICATOR-SPECIFIC ROTATION CORRECTIONS:
  # These corrections must be defined in *.fab.yaml configuration files:
  # - Generic: Standard IPC-7352 reference (Pin 1 top-left = 0°)
  # - JLCPCB: Per-part "Reel Zero" corrections (requires part-specific lookup)
  # - PCBWay: Equipment-specific mathematical offset corrections
  #
  # EXISTING SOLUTIONS:
  # - JLCKicadTools project: https://github.com/matthewlai/JLCKicadTools/tree/master/jlc_kicad_tools
  #   * Provides CSV database of JLCPCB part-specific rotation corrections
  #   * Demonstrates real-world approach to per-part rotation lookup
  #   * Shows complexity of maintaining part-specific rotation database
  #
  # TESTING REQUIREMENTS:
  # - Test cardinal points (0°, 90°, 180°, 270°) for mathematical corrections
  # - Test specific parts with known problematic reel orientations
  # - Test same footprint with different packaging orientations
  # - Test integration with external rotation correction databases

  Background:
    Given a KiCad project named "SimpleProject" with a PCB file

  Scenario: Generate basic POS file
    Given the "BasicPCB" PCB layout
    When I generate a POS file with --generic fabricator
    Then the POS contains components with columns matching the Generic fabricator configuration

  Scenario: Generate JLCPCB format POS with fabricator-specific rotation corrections
    Given a PCB with components at cardinal rotation angles
      | Reference | KiCad_Rotation | Expected_JLCPCB_Rotation | Footprint   |
      | R1        | 0              | 0                        | R_0603_1608 |
      | C1        | 90             | 90                       | C_0603_1608 |
      | U1        | 180            | 180                      | QFN-32      |
      | R2        | 270            | 270                      | R_0603_1608 |
    When I generate JLCPCB format POS with fabricator-specific rotations
    Then the POS contains rotation corrections matching the JLCPCB fabricator configuration
    And the POS excludes THT components per JLCPCB SMD-only policy

  Scenario: Generate PCBWay format POS with different rotation corrections
    Given a PCB with components at cardinal rotation angles
      | Reference | KiCad_Rotation | Expected_PCBWay_Rotation | Footprint   |
      | R1        | 0              | 0                        | R_0603_1608 |
      | C1        | 90             | 270                      | C_0603_1608 |
      | U1        | 180            | 180                      | QFN-32      |
      | R2        | 270            | 90                       | R_0603_1608 |
    When I generate PCBWay format POS with fabricator-specific rotations
    Then the POS contains rotation corrections matching the PCBWay fabricator configuration

  Scenario: Handle JLCPCB per-part reel orientation complexity for IC packaging variations
    Given a PCB with ICs in different packaging formats requiring different reel orientations
      | Reference | Footprint       | MPN             | DPN    | KiCad_Rotation | Expected_JLCPCB_Reel_Rotation | Notes                    |
      | U1        | SOIC-24_7.5x15  | LM324DR         | C7950  | 0              | 0                             | Standard SOIC reel       |
      | U2        | SOIC-24_7.5x15  | LM324ADR        | C7951  | 0              | 180                           | Alternate supplier reel  |
      | U3        | DIP-32_15.24x39 | ATMega328P-PU   | C14877 | 90             | 90                            | Through-hole DIP         |
      | U4        | QFN-32_5x5      | ATMega328PB-AU  | C14878 | 90             | 270                           | QFN surface mount        |
    When I generate JLCPCB format POS with per-part reel corrections
    Then the POS contains part-specific rotation corrections based on MPN and DPN lookup
    And the POS shows different rotations for same chip in different packaging formats
    And resistors and capacitors use consistent rotation corrections per footprint

  Scenario: Filter SMD components only
    Given the "MixedSMDTHT_PCB" PCB layout
    When I generate POS with --generic fabricator and SMD-only filter
    Then the POS contains SMD components but excludes THT components

  Scenario: Filter by board layer
    Given the "MixedSMDTHT_PCB" PCB layout
    When I generate POS with --generic fabricator and top-side filter
    Then the POS contains top-side components but excludes bottom-side components

  Scenario: Generate POS with coordinate and component data
    Given the "BasicPCB" PCB layout
    When I generate POS with --generic fabricator
    Then the POS contains component count and coordinate data in millimeters matching the Generic fabricator configuration

  Scenario: Handle different coordinate units
    Given the "BasicPCB" PCB layout
    When I generate POS with --generic fabricator and inch units
    Then the POS coordinates show components in inches with 3 decimal precision

  Scenario: Use auxiliary origin for coordinates
    Given the "BasicPCB" PCB layout with auxiliary origin offset
    When I generate POS with --generic fabricator using auxiliary origin
    Then the POS coordinates show components relative to auxiliary origin
