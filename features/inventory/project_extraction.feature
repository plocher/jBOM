Feature: Project Inventory Extraction
  As a PCB designer
  I want to extract an inventory from my KiCad project
  So that I can create an initial inventory file with all project components

  Background:
    Given a KiCad project named "SimpleProject"

  Scenario: Extract basic inventory from schematic
    Given the schematic contains components
      | Reference | Value | Footprint     | Quantity |
      | R1,R2     | 10K   | R_0603_1608   | 2        |
      | C1        | 100nF | C_0603_1608   | 1        |
      | U1        | ESP32 | QFN-32        | 1        |
    When I extract inventory from the project
    Then the inventory contains entries for RES, CAP, and IC categories with IPN, Value, Package, and Priority columns

  Scenario: Extract inventory with distributor format preparation
    Given the schematic contains components
      | Reference | Value | Footprint     | Quantity |
      | R1        | 10K   | R_0603_1608   | 1        |
      | C1        | 100nF | C_0603_1608   | 1        |
    When I extract inventory with JLC distributor format
    Then the inventory contains columns "IPN,Category,Value,Package,LCSC,SMD,Priority" for distributor submission

  Scenario: Extract inventory with UUID tracking for back-annotation
    Given the schematic contains components with UUIDs
      | Reference | Value | Footprint   | UUID                                 |
      | R1        | 10K   | R_0603_1608 | 12345678-1234-5678-9abc-123456789012 |
      | C1        | 100nF | C_0603_1608 | 87654321-4321-8765-cba9-210987654321 |
    When I extract inventory with UUID tracking
    Then the inventory contains UUID column with component UUIDs for back-annotation linking

  Scenario: Extract inventory via API
    Given the schematic contains components
      | Reference | Value | Footprint     | Quantity |
      | R1,R2     | 10K   | R_0603_1608   | 2        |
      | C1        | 100nF | C_0603_1608   | 1        |
    When I use the API to extract inventory
    Then the API returns InventoryResult with 2 unique components and field names list

  Scenario: Handle hierarchical schematic inventory extraction
    Given a hierarchical schematic with main sheet components
      | Reference | Value | Footprint     |
      | R1        | 10K   | R_0603_1608   |
    And sub-sheet "power.kicad_sch" with components
      | Reference | Value | Footprint     |
      | R2        | 10K   | R_0603_1608   |
    When I extract inventory from the hierarchical project
    Then the inventory merges R1 and R2 into single RES entry with quantity 2

  Scenario: Extract inventory with custom field selection
    Given the schematic contains components with properties
      | Reference | Value | Footprint   | Manufacturer | MPN            |
      | R1        | 10K   | R_0603_1608 | YAGEO        | RC0603FR-0710K |
    When I extract inventory with custom fields "IPN,Value,Package,Manufacturer,MPN"
    Then the inventory contains only the specified columns excluding default columns
