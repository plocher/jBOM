Feature: Component Placement (POS/CPL) Generation
  As a PCB designer
  I want to generate component placement files from my KiCad PCB
  So that PCB assembly services can accurately place components on my board

  Background:
    Given a KiCad project named "SimpleProject" with a PCB file

  Scenario: Generate basic POS file
    Given the PCB contains placed components
    Then the POS contains all placed components with columns "Reference,X,Y,Rotation,Side,Footprint"

  Scenario: Generate JLCPCB format POS
    Given the PCB contains SMD components for assembly
    Then the POS generates in JLCPCB format with millimeter coordinates and SMD-only filtering

  Scenario: Filter SMD components only
    Given the PCB contains both SMD and through-hole components
    Then the POS contains only surface mount components excluding through-hole

  Scenario: Filter by board layer
    Given the PCB has components on both top and bottom layers
    Then the POS contains only top-side components excluding bottom-side

  Scenario: Generate POS via API
    Given the PCB contains placed components
    Then the API generates POS with placement data and coordinate information

  Scenario: Handle different coordinate units
    Given the PCB contains placed components
    Then the POS coordinates are converted to inches with appropriate precision

  Scenario: Use auxiliary origin for coordinates
    Given the PCB has an auxiliary origin defined
    Then the POS coordinates are relative to auxiliary origin consistently
