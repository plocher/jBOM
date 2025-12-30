Feature: Component Placement (POS/CPL) Generation
  As a PCB designer
  I want to generate component placement files from my KiCad PCB
  So that PCB assembly services can accurately place components on my board

  Background:
    Given a KiCad project named "SimpleProject" with a PCB file

  Scenario: Generate basic POS file
    Given the PCB contains placed components
    When I run jbom command "pos SimpleProject -o placement.csv"
    Then the command succeeds
    And file "placement.csv" is created
    And the POS file contains all placed components
    And the POS includes columns: Reference, X, Y, Rotation, Side, Footprint

  Scenario: Generate JLCPCB format POS
    Given the PCB contains SMD components for assembly
    When I run jbom command "pos SimpleProject --jlc -o jlc_placement.csv"
    Then the command succeeds
    And file "jlc_placement.csv" is created
    And the POS uses JLCPCB column format: Designator, Mid X, Mid Y, Layer, Rotation
    And coordinates are in millimeters
    And only SMD components are included

  Scenario: Filter SMD components only
    Given the PCB contains both SMD and through-hole components
    When I run jbom command "pos SimpleProject --smd-only -o smd_placement.csv"
    Then the command succeeds
    And file "smd_placement.csv" is created
    And the POS contains only surface mount components
    And through-hole components are excluded

  Scenario: Filter by board layer
    Given the PCB has components on both top and bottom layers
    When I run jbom command "pos SimpleProject --layer TOP -o top_placement.csv"
    Then the command succeeds
    And file "top_placement.csv" is created
    And the POS contains only top-side components
    And bottom-side components are excluded

  Scenario: Generate POS via Python API
    Given the PCB contains placed components
    When I generate POS using Python API
    Then the command succeeds
    And the API result contains placement data for all components
    And the API result includes component count and coordinate information
    And the result can be written to CSV or accessed programmatically

  Scenario: Handle different coordinate units
    Given the PCB contains placed components
    When I run jbom command "pos SimpleProject --units inch -o inch_placement.csv"
    Then the command succeeds
    And file "inch_placement.csv" is created
    And all coordinates are converted to inches
    And the coordinate precision is appropriate for inch units

  Scenario: Use auxiliary origin for coordinates
    Given the PCB has an auxiliary origin defined
    When I run jbom command "pos SimpleProject --origin aux -o aux_placement.csv"
    Then the command succeeds
    And file "aux_placement.csv" is created
    And coordinates are relative to the auxiliary origin
    And the origin choice affects all component positions consistently
