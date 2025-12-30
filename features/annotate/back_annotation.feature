Feature: Back-Annotation
  As a PCB designer
  I want to update my KiCad schematic with inventory data
  So that my schematic becomes the single source of truth with complete part information

  Background:
    Given a KiCad project named "SimpleProject"

  Scenario: Basic back-annotation with part numbers
    Given the schematic has components with missing part information
    And an inventory file with complete distributor and manufacturer data
      | UUID                                 | IPN  | Value | Distributor | DPN    | Manufacturer | MPN            |
      | 12345678-1234-1234-1234-123456789012 | R001 | 10K   | JLC         | C25804 | YAGEO        | RC0603FR-0710K |
      | 87654321-4321-4321-4321-210987654321 | C001 | 100nF | JLC         | C14663 | YAGEO        | CC0603KRX7R9BB |
    Then the back-annotation updates schematic with distributor and manufacturer information

  Scenario: Dry-run back-annotation for preview
    Given the schematic has components needing updates
    And an inventory file with updated information
    Then the dry-run back-annotation previews changes without modifying schematic files

  Scenario: Back-annotation via API
    Given the schematic has components needing updates
    And an inventory file with updated information
    Then the API back-annotation reports update count and changed details

  Scenario: Handle missing UUIDs gracefully
    Given the schematic has components with valid UUIDs
    And an inventory file with missing or invalid UUIDs
    Then the back-annotation warns about invalid UUIDs and updates only valid components

  Scenario: Update only specific fields
    Given the schematic has components with partial information
    And an inventory file with selective updates (only distributor part numbers)
    Then the back-annotation updates only DPN fields preserving existing data

  Scenario: Handle inventory-schematic mismatches
    Given the schematic has different components than the inventory
    And the inventory contains components not in the schematic
    Then the back-annotation updates only matching components and reports mismatches

  Scenario: Back-annotate KiCad project from Excel inventory
    Given a KiCad schematic file "ProductBoard.kicad_sch" with incomplete part information
    And an Excel inventory file "updated_parts.xlsx" with complete distributor data
    When I run back-annotation
    Then the KiCad schematic file is updated with part numbers and manufacturer data from Excel
    And component properties include LCSC, MPN, and Manufacturer fields

  Scenario: Back-annotate hierarchical project from Numbers inventory
    Given a hierarchical KiCad project:
      | File                  | Components |
      | MainBoard.kicad_sch   | U1, R1, C1 |
      | PowerSupply.kicad_sch | U2, R2, C2 |
    And a Numbers inventory file "parts_database.numbers"
    When I run back-annotation on the project directory
    Then all schematic files are updated with inventory data
    And component UUIDs are preserved across updates

  Scenario: Back-annotate with mixed inventory file formats
    Given a KiCad schematic "ControllerBoard.kicad_sch"
    And multiple inventory sources with overlapping data:
      | File               | Format  | Components    |
      | resistors.csv      | CSV     | R1, R2, R3    |
      | ics.xlsx           | Excel   | U1, U2        |
      | connectors.numbers | Numbers | J1, J2        |
    When I run back-annotation with all inventory sources
    Then schematic components are updated from their respective inventory sources
    And no component data is overwritten by conflicting sources
