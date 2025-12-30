Feature: Back-Annotation
  As a PCB designer
  I want to update my KiCad schematic with inventory data
  So that my schematic becomes the single source of truth with complete part information

  Background:
    Given a KiCad project named "SimpleProject"

  Scenario: Basic back-annotation with part numbers
    Given the schematic has components with missing part information and complete inventory data
    Then the back-annotation updates schematic with distributor and manufacturer information

  Scenario: Dry-run back-annotation for preview
    Given the schematic has components needing updates with inventory file
    Then the dry-run back-annotation previews changes without modifying schematic files

  Scenario: Back-annotation via API
    Given the schematic has components needing updates with inventory file
    Then the API back-annotation reports update count and changed details

  Scenario: Handle missing UUIDs gracefully
    Given inventory file with missing or invalid UUIDs
    Then the back-annotation warns about invalid UUIDs and updates only valid components

  Scenario: Update only specific fields
    Given the schematic with partial information and selective inventory updates
    Then the back-annotation updates only DPN fields preserving existing data

  Scenario: Handle inventory-schematic mismatches
    Given the schematic with different components than inventory
    Then the back-annotation updates only matching components and reports mismatches
