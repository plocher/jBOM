Feature: Back-Annotation
  As a PCB designer
  I want to update my KiCad schematic with inventory data
  So that my schematic becomes the single source of truth with complete part information

  Background:
    Given a KiCad project named "SimpleProject"

  Scenario: Basic back-annotation with generic fabricator
    Given the "ComponentProperties" schematic
    And the "JLC_Basic" inventory
    When I run back-annotation with --generic fabricator
    Then the back-annotation updates schematic with fields Manufacturer, MPN, Distributor, DPN

  Scenario: Fabricator-specific configuration testing
    Given the "BasicComponents" schematic
    And the "LocalStock" inventory
    When I run back-annotation with --jlc fabricator
    Then the back-annotation updates schematic with fields Manufacturer, MPN, Distributor, DPN
    And the updates match the JLC fabricator configuration
    When I run back-annotation with --pcbway fabricator
    Then the back-annotation updates schematic with fields Manufacturer, MPN, Distributor, DPN
    And the updates match the PCBWay fabricator configuration

  Scenario: Dry-run back-annotation for preview
    Given the "BasicComponents" schematic
    And the "JLC_Basic" inventory
    When I run back-annotation with --dry-run and --generic fabricator
    Then the dry-run back-annotation previews changes without modifying schematic files

  Scenario: Handle missing UUIDs gracefully
    Given the "BasicComponents" schematic
    And inventory file with missing or invalid UUIDs
    When I run back-annotation with --generic fabricator
    Then the back-annotation warns about invalid UUIDs
    And the back-annotation updates only valid components

  Scenario: Update only specific fields preserving existing data
    Given the "ComponentProperties" schematic
    And an inventory file with selective updates (only distributor part numbers)
    When I run back-annotation with --fields "DPN" only and --generic fabricator
    Then the back-annotation updates only DPN fields preserving existing data

  Scenario: Handle inventory-schematic mismatches
    Given the "BasicComponents" schematic
    And the inventory contains components not in the schematic
    When I run back-annotation with --generic fabricator
    Then the back-annotation updates only matching components and reports mismatches

  Scenario: Back-annotate from Excel inventory workflow
    Given the "ComponentProperties" schematic
    And an Excel inventory file with complete distributor data
    When I run back-annotation with --generic fabricator
    Then the back-annotation updates schematic with fields Manufacturer, MPN, Distributor, DPN

  Scenario: Back-annotate hierarchical project workflow
    Given the "HierarchicalDesign" schematic
    And the "JLC_Basic" inventory
    When I run back-annotation with --generic fabricator
    Then the back-annotation updates schematic with fields Manufacturer, MPN, Distributor, DPN

  Scenario: Back-annotate with mixed inventory file formats workflow
    Given the "BasicComponents" schematic
    And multiple inventory sources with overlapping data
    When I run back-annotation with --generic fabricator
    Then the back-annotation updates schematic with fields Manufacturer, MPN, Distributor, DPN
