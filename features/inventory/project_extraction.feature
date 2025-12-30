Feature: Project Inventory Extraction
  As a PCB designer
  I want to extract an inventory from my KiCad project
  So that I can create an initial inventory file with all project components

  Background:
    Given a KiCad project named "SimpleProject"

  Scenario: Extract basic inventory from schematic
    Given the schematic contains diverse components
    Then the inventory extracts all unique components with required columns

  Scenario: Extract inventory with distributor format preparation
    Given the schematic contains standard components
    Then the inventory extracts with distributor format including DPN and SMD columns

  Scenario: Extract inventory with UUID tracking for back-annotation
    Given the schematic contains components with UUIDs
    Then the inventory extracts with UUID column for back-annotation

  Scenario: Extract inventory via API
    Given the schematic contains standard components
    Then the API extracts inventory with component count and field names

  Scenario: Handle hierarchical schematic inventory extraction
    Given a hierarchical schematic with sub-sheets
    Then the inventory extracts components from all sheets with merged quantities

  Scenario: Extract inventory with custom field selection
    Given the schematic contains components with properties
    Then the inventory extracts with custom fields "IPN,Value,Package,Manufacturer,MPN"
