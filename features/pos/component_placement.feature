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
  #   * No consistent rotation can be automatically applied across parts
  #   * Every part needs individual rotation correction per datasheet diagram
  #   * Same package/footprint may have different orientations with different tape/reel options
  #   * Multiple suppliers for same part may require different rotations
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
  # TESTING REQUIREMENTS:
  # - Test cardinal points (0°, 90°, 180°, 270°) for mathematical corrections
  # - Test specific parts with known problematic reel orientations
  # - Test same footprint with different packaging orientations

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

  Scenario: Handle JLCPCB per-part reel orientation complexity
    Given a PCB with same footprints but different reel orientations
      | Reference | Footprint   | MPN            | DPN    | KiCad_Rotation | Expected_JLCPCB_Reel_Rotation |
      | R1        | R_0603_1608 | RC0603FR-0710K | C25804 | 0              | 0                             |
      | R2        | R_0603_1608 | RC0603JR-0710K | C25805 | 0              | 90                            |
      | C1        | C_0603_1608 | CC0603KRX7R9BB | C14663 | 90             | 180                           |
      | C2        | C_0603_1608 | CC0603MRX5R8BB | C14664 | 90             | 270                           |
    When I generate JLCPCB format POS with per-part reel corrections
    Then the POS contains part-specific rotation corrections based on MPN and DPN lookup
    And the POS shows different rotations for same footprint with different reel orientations

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
