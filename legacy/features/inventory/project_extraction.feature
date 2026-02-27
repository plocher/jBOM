Feature: Project Inventory Extraction
  As a PCB designer
  I want to extract an inventory from my KiCad project
  So that I can create an initial inventory file with all project components

  Background:
    Given a KiCad project named "SimpleProject"

  Scenario: Extract basic inventory from schematic
    Given the "BasicComponents" schematic
    When I extract inventory from the project with --generic fabricator
    Then the inventory contains entries for RES, CAP, and IC categories with columns matching the Generic fabricator configuration

  Scenario: Extract inventory with distributor format preparation
    Given the "BasicComponents" schematic
    When I extract inventory with --jlc fabricator format
    Then the inventory contains columns matching the JLC fabricator configuration for distributor submission

  Scenario: Extract inventory with UUID tracking for back-annotation
    Given the "ComponentProperties" schematic
    When I extract inventory with --generic fabricator and UUID tracking
    Then the inventory contains UUID column with component UUIDs for back-annotation linking

  Scenario: Extract inventory via API
    Given the "BasicComponents" schematic
    When I use the API to extract inventory with --generic fabricator
    Then the API returns InventoryResult with component count and field names matching the Generic fabricator configuration

  Scenario: Handle hierarchical schematic inventory extraction
    Given the "HierarchicalDesign" schematic
    When I extract inventory from the hierarchical project with --generic fabricator
    Then the inventory merges components across sheets with correct quantities

  Scenario: Extract inventory with custom field selection
    Given the "ComponentProperties" schematic
    When I extract inventory with custom fields "Reference,Value,Package,Manufacturer,MPN" for selective extraction
    Then the inventory contains only the specified columns excluding default columns
