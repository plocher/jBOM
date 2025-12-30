Feature: Component Placement (POS/CPL) Generation
  As a PCB designer
  I want to generate component placement files from my KiCad PCB
  So that PCB assembly services can accurately place components on my board

  # TECHNICAL CONTEXT - Component Rotation Standards:
  #
  # IPC-7352 defines the standard for zero degrees orientation, specifying where Pin 1 should be located.
  # Rotation == 0 represents the position of the part when picked up by the pick-and-place machine
  # from the distributor's bulk delivery media (reel or tray).
  #
  # Component rotation angles generally increase in a counter-clockwise direction.
  #
  # CRITICAL: Different manufacturing equipment uses proprietary or slightly different internal
  # rotation standards. It is essential to provide comprehensive documentation and coordinate
  # with your assembly house. The pick-and-place machine's program will use your design's
  # centroid file and adjust rotations as needed to match its physical setup.
  #
  # FABRICATOR-SPECIFIC ROTATION CORRECTIONS:
  # Each fabricator may require different rotation mappings from KiCad's internal rotation
  # to their pick-and-place equipment. These corrections are defined in the *.fab.yaml
  # configuration files and must be tested for the 4 cardinal points: 0°, 90°, 180°, 270°.
  #
  # Example rotation corrections:
  # - JLCPCB: May use 1:1 mapping (KiCad 90° → JLCPCB 90°)
  # - PCBWay: May use different mapping (KiCad 90° → PCBWay 270°)
  # - Generic: Standard IPC-7352 reference orientation

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
