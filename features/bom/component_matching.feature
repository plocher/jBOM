Feature: Component Matching
  As a PCB designer
  I want jBOM to match schematic components against inventory items
  So that I can generate accurate BOMs with available parts

  Background:
    Given a KiCad project named "SimpleProject"
    And an inventory file with components
      | IPN   | Category | Value | Package | Distributor | DPN     | Priority |
      | R001  | RES      | 10K   | 0603    | JLC         | C25804  | 1        |
      | R002  | RES      | 1K1   | 0603    | JLC         | C11702  | 1        |
      | C001  | CAP      | 100nF | 0603    | JLC         | C14663  | 1        |
      | C002  | CAP      | 10uF  | 0805    | JLC         | C15850  | 1        |

  Scenario: Match resistor by value and package
    Given the schematic contains a 10K 0603 resistor
    When I generate a BOM with --generic fabricator
    Then the BOM contains a matched resistor with value "10K" and package "0603" from the inventory

  Scenario: Match capacitor by value and package
    Given the schematic contains a 100nF 0603 capacitor
    When I generate a BOM with --generic fabricator
    Then the BOM contains a matched capacitor with value "100nF" and package "0603" from the inventory

  Scenario: Match resistor by close value and package - tolerance ranges
    Given the schematic contains a 1K 0603 resistor
    When I generate a BOM with --generic fabricator
    Then the BOM contains a matched resistor with value "1K1" and package "0603" using tolerance matching

  Scenario: Match resistor by exact value and package - tolerance normalizing
    Given the schematic contains a 1.1K 0603 resistor
    When I generate a BOM with --generic fabricator
    Then the BOM contains a matched resistor with normalized value "1K1" and package "0603" from the inventory

  Scenario: No match for missing component - no fields match
    Given the schematic contains a 47K 1206 resistor
    When I generate a BOM with --generic fabricator
    Then the BOM contains an unmatched component entry

  Scenario: No match for missing component - value matches, package doesn't
    Given the schematic contains a 10K 1206 resistor
    When I generate a BOM with --generic fabricator
    Then the BOM contains an unmatched component entry

  Scenario: No match for missing component - package matches, value doesn't
    Given the schematic contains a 100K 0603 resistor
    When I generate a BOM with --generic fabricator
    Then the BOM contains an unmatched component entry

  Scenario: Generate BOM from actual KiCad project with Excel inventory
    Given a KiCad project file "TestBoard.kicad_sch"
    And an Excel inventory file "parts_database.xlsx"
    When I generate a BOM with --generic fabricator
    Then the BOM contains components extracted from the KiCad schematic
    And components are matched against parts loaded from Excel file

  Scenario: Process hierarchical KiCad schematic with CSV inventory
    Given a KiCad project with main sheet "MainBoard.kicad_sch"
    And sub-sheet "PowerSupply.kicad_sch"
    And a CSV inventory file "inventory.csv"
    When I generate a BOM with --generic fabricator
    Then the BOM includes components from both main sheet and sub-sheet
    And component quantities are merged correctly across sheets

  Scenario: Handle mixed file formats in workflow
    Given a KiCad project file "Controller.kicad_sch"
    And multiple inventory sources:
      | File                | Format  |
      | resistors.xlsx      | Excel   |
      | capacitors.csv      | CSV     |
      | ics.numbers         | Numbers |
    When I generate a BOM with --generic fabricator and all inventory sources
    Then the BOM combines parts data from all file formats
    And components are matched across all inventory sources
