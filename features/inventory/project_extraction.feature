Feature: Project Inventory Extraction
  As a PCB designer
  I want to extract an inventory from my KiCad project
  So that I can create an initial inventory file with all project components

  Background:
    Given a KiCad project named "SimpleProject"

  Scenario: Extract basic inventory from schematic
    Given the schematic contains diverse components
    When I run jbom command "inventory SimpleProject -o project_inventory.csv"
    Then the command succeeds
    And file "project_inventory.csv" is created
    And the inventory contains all unique components from the schematic
    And the inventory includes required columns: IPN, Category, Value, Package, Distributor, DPN, Priority

  Scenario: Extract inventory with distributor format preparation
    Given the schematic contains standard components
    When I run jbom command "inventory SimpleProject --jlc -o distributor_ready_inventory.csv"
    Then the command succeeds
    And file "distributor_ready_inventory.csv" is created
    And the inventory includes DPN column ready for distributor part number entry
    And the inventory includes SMD column with package-based detection

  Scenario: Extract inventory with UUID tracking for back-annotation
    Given the schematic contains components with UUIDs
    When I run jbom command "inventory SimpleProject -o uuid_inventory.csv"
    Then the command succeeds
    And file "uuid_inventory.csv" is created
    And the inventory includes UUID column for each component
    And the UUID column enables back-annotation to schematic

  Scenario: Extract inventory via Python API
    Given the schematic contains standard components
    When I generate inventory using Python API
    Then the command succeeds
    And the API result contains all schematic components
    And the API result includes component count and field names
    And the API result can be written to CSV, Excel, or displayed

  Scenario: Handle hierarchical schematic inventory extraction
    Given a hierarchical schematic with sub-sheets
    When I run jbom command "inventory HierarchicalProject -o hierarchical_inventory.csv"
    Then the command succeeds
    And file "hierarchical_inventory.csv" is created
    And the inventory includes components from all schematic sheets
    And duplicate components across sheets are merged with combined quantities

  Scenario: Extract inventory with custom field selection
    Given the schematic contains components with properties
    When I run jbom command "inventory SimpleProject -f 'IPN,Value,Package,Manufacturer,MPN' -o custom_inventory.csv"
    Then the command succeeds
    And file "custom_inventory.csv" is created
    And the inventory contains only the specified columns
    And missing properties appear as empty fields
