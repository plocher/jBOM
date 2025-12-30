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
    When I run jbom command "annotate SimpleProject -i updated_inventory.csv"
    Then the command succeeds
    And the schematic components are updated with distributor part numbers
    And the schematic components are updated with manufacturer information
    And the output reports the number of components updated

  Scenario: Dry-run back-annotation for preview
    Given the schematic has components needing updates
    And an inventory file with updated information
    When I run jbom command "annotate SimpleProject -i updated_inventory.csv --dry-run"
    Then the command succeeds
    And the schematic files are not modified
    And the output shows what would be updated
    And the output includes component UUIDs and proposed changes

  Scenario: Back-annotation via Python API
    Given the schematic has components needing updates
    And an inventory file with updated information
    When I perform back-annotation using Python API
    Then the command succeeds
    And the API result reports successful update count
    And the API result includes details of what was changed
    And the schematic files contain the updated information

  Scenario: Handle missing UUIDs gracefully
    Given an inventory file with missing or invalid UUIDs
    When I run jbom command "annotate SimpleProject -i incomplete_inventory.csv"
    Then the command succeeds
    And the output warns about components without valid UUIDs
    And only components with valid UUIDs are updated
    And the operation does not fail due to missing UUIDs

  Scenario: Update only specific fields
    Given the schematic has components with partial information
    And an inventory file with selective updates (only distributor part numbers)
    When I run jbom command "annotate SimpleProject -i dpn_only_inventory.csv"
    Then the command succeeds
    And only the DPN fields are updated in the schematic
    And existing Value and Footprint fields remain unchanged
    And empty inventory fields do not overwrite existing schematic data

  Scenario: Handle inventory-schematic mismatches
    Given the schematic has different components than the inventory
    And the inventory contains components not in the schematic
    When I run jbom command "annotate SimpleProject -i mismatched_inventory.csv"
    Then the command succeeds
    And only matching components are updated
    And the output reports components that could not be matched
    And no spurious components are added to the schematic
