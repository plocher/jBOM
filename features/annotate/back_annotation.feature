Feature: Back-Annotation
  As a PCB designer
  I want to update my KiCad schematic with inventory data
  So that my schematic becomes the single source of truth with complete part information

  Background:
    Given a KiCad project named "SimpleProject"

  Scenario: Basic back-annotation with part numbers
    Given the schematic has components with UUIDs
      | Reference | UUID                                 | Current_LCSC | Current_MPN |
      | R1        | 12345678-1234-1234-1234-123456789012 | ""           | ""          |
      | C1        | 87654321-4321-4321-4321-210987654321 | ""           | ""          |
    And an inventory file with complete distributor and manufacturer data
      | UUID                                 | IPN  | Value | Distributor | DPN    | Manufacturer | MPN            |
      | 12345678-1234-1234-1234-123456789012 | R001 | 10K   | JLC         | C25804 | YAGEO        | RC0603FR-0710K |
      | 87654321-4321-4321-4321-210987654321 | C001 | 100nF | JLC         | C14663 | YAGEO        | CC0603KRX7R9BB |
    When I run back-annotation
    Then component R1 has LCSC property set to "C25804"
    And component R1 has MPN property set to "RC0603FR-0710K"
    And component R1 has Manufacturer property set to "YAGEO"
    And component C1 has LCSC property set to "C14663"
    And component C1 has MPN property set to "CC0603KRX7R9BB"
    And component C1 has Manufacturer property set to "YAGEO"
    And the schematic file modification time is updated

  Scenario: Dry-run back-annotation for preview
    Given the schematic has components with UUIDs
      | Reference | UUID                                 | Current_LCSC |
      | R1        | 12345678-1234-1234-1234-123456789012 | ""           |
    And an inventory file with updated information
      | UUID                                 | DPN    | MPN            |
      | 12345678-1234-1234-1234-123456789012 | C25804 | RC0603FR-0710K |
    When I run back-annotation with --dry-run flag
    Then the output shows "Would update R1: LCSC = C25804, MPN = RC0603FR-0710K"
    And the schematic file modification time is unchanged
    And component R1 still has empty LCSC property

  Scenario: Back-annotation via API
    Given the schematic has components with UUIDs
      | Reference | UUID                                 | Current_LCSC |
      | R1        | 12345678-1234-1234-1234-123456789012 | ""           |
      | C1        | 87654321-4321-4321-4321-210987654321 | ""           |
    And an inventory file with updated information
      | UUID                                 | DPN    | MPN            |
      | 12345678-1234-1234-1234-123456789012 | C25804 | RC0603FR-0710K |
      | 87654321-4321-4321-4321-210987654321 | C14663 | CC0603KRX7R9BB |
    When I run back-annotation via API
    Then the API returns BackAnnotationResult with update_count = 2
    And the API result includes changed_components = ["R1", "C1"]
    And the API result includes updated_fields = ["LCSC", "MPN"]

  Scenario: Handle missing UUIDs gracefully
    Given the schematic has components with UUIDs
      | Reference | UUID                                 | Current_LCSC |
      | R1        | 12345678-1234-1234-1234-123456789012 | ""           |
      | R2        | 11111111-1111-1111-1111-111111111111 | ""           |
    And an inventory file with missing or invalid UUIDs
      | UUID                                 | DPN    |
      | 12345678-1234-1234-1234-123456789012 | C25804 |
      | "invalid-uuid"                       | C11702 |
      | ""                                   | C14663 |
    When I run back-annotation
    Then component R1 has LCSC property set to "C25804"
    And component R2 still has empty LCSC property
    And the output warns "Invalid UUID: invalid-uuid"
    And the output warns "Empty UUID in inventory row"

  Scenario: Update only specific fields
    Given the schematic has components with existing data
      | Reference | UUID                                 | Current_LCSC | Current_MPN        |
      | R1        | 12345678-1234-1234-1234-123456789012 | "C99999"     | "OLD_PART_NUMBER" |
    And an inventory file with selective updates
      | UUID                                 | DPN    |
      | 12345678-1234-1234-1234-123456789012 | C25804 |
    When I run back-annotation with --fields "LCSC" only
    Then component R1 has LCSC property set to "C25804"
    And component R1 still has MPN property set to "OLD_PART_NUMBER"

  Scenario: Handle inventory-schematic mismatches
    Given the schematic has components
      | Reference | UUID                                 |
      | R1        | 12345678-1234-1234-1234-123456789012 |
      | C1        | 87654321-4321-4321-4321-210987654321 |
    And an inventory file with different components
      | UUID                                 | DPN    | Comment        |
      | 12345678-1234-1234-1234-123456789012 | C25804 | "matches R1"   |
      | 99999999-9999-9999-9999-999999999999 | C11702 | "no match"     |
    When I run back-annotation
    Then component R1 has LCSC property set to "C25804"
    And component C1 still has empty LCSC property
    And the output reports "1 component updated, 1 component unmatched"
    And the output lists "Unmatched inventory: UUID 99999999-9999-9999-9999-999999999999"

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
