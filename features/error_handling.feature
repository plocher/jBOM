Feature: Error Handling and Edge Cases
  As a PCB designer
  I want jBOM to handle errors gracefully with clear messages
  So that I can quickly identify and fix issues in my workflow

  Scenario: Missing inventory file
    Given a KiCad project named "SimpleProject"
    And I specify nonexistent inventory file "/path/to/missing.csv"
    When I generate a BOM
    Then the error message reports "Inventory file not found: /path/to/missing.csv" and exits with code 1

  Scenario: Invalid inventory file format
    Given a KiCad project named "SimpleProject"
    And an inventory file with invalid format
      | InvalidColumn | AnotherBadColumn |
      | data1         | data2            |
    When I generate a BOM
    Then the error message reports "Inventory file is missing required columns: IPN, Category" and exits with code 1

  Scenario: Missing project files
    Given I specify nonexistent project directory "/path/to/missing"
    When I generate a BOM
    Then the error message reports "Input file not found: /path/to/missing" and suggests checking the path

  Scenario: Schematic with malformed S-expression syntax
    Given a schematic named "CorruptedProject" containing malformed S-expression:
      """
      (kicad_sch (version 20230121) (generator eeschema)
        (uuid "corrupted-test-uuid")
        (paper "A4"
        (lib_symbols)
        (symbol_instances)
        (sheet_instances
          (path "/" (page "1"))
        # Missing closing parentheses - concrete syntax error
      """
    When I generate a generic BOM with CorruptedProject
    Then the BOM generation fails with exit code 1
    And the error message reports "Error parsing schematic: CorruptedProject.kicad_sch"
    And the error message includes syntax error details

  Scenario: Output file permission denied
    Given a KiCad project named "SimpleProject"
    And a read-only directory "./notwritable"
    And an output path "./notwritable/output.csv"
    When I generate a generic BOM with SimpleProject writing to "./notwritable/output.csv"
    Then the BOM generation fails with exit code 1
    And the error message reports "Permission denied writing to: ./notwritable/output.csv"
    And the error message suggests checking directory write permissions
    And no file was created at "./notwritable/output.csv"

  Scenario: Empty inventory file with header only
    Given a KiCad project named "SimpleProject" containing components:
      | Reference | Value | Footprint |
      | R1        | 10k   | R_0805    |
      | C1        | 100nF | C_0805    |
    And an inventory file "empty-inventory.csv" containing only headers:
      | IPN | Category | Value | Package | Manufacturer | Description |
    When I generate a generic BOM for SimpleProject using empty-inventory.csv
    Then the BOM generation succeeds with exit code 0
    And the BOM file contains unmatched components R1 and C1
    And the BOM output shows 2 components with 0 matched and 2 unmatched

  Scenario: Empty schematic with no components
    Given a KiCad project named "EmptyProject" with valid schematic structure but no symbol instances
    And an inventory file "standard-inventory.csv" containing components:
      | IPN | Category | Value | Package | Manufacturer | Description |
      | RES001 | Resistor | 10k | R_0805 | Generic | 10k ohm resistor |
    When I generate a generic BOM for EmptyProject using standard-inventory.csv
    Then the BOM generation succeeds with exit code 0
    And the BOM file contains header row but no data rows

  @wip
  Scenario: Invalid API key for component search
    Given a KiCad project named "SimpleProject" containing components:
      | Reference | Value | Footprint |
      | R1        | 10k   | R_0805    |
    And I set the MOUSER_API_KEY environment variable to "invalid-key-12345"
    When I generate search-enhanced inventory for SimpleProject with --mouser fabricator
    Then the command fails with exit code 1
    And the error message reports "Authentication failed: Invalid API key"
    And the error message suggests "Please verify your MOUSER_API_KEY environment variable"

  @wip
  Scenario: Network timeout during component search
    Given a KiCad project named "SimpleProject" containing components:
      | Reference | Value | Footprint |
      | R1        | 10k   | R_0805    |
    And I set the MOUSER_API_KEY environment variable to a valid key
    And I configure network timeout to 1 second for testing
    When I generate search-enhanced inventory for SimpleProject with --mouser fabricator
    Then the command fails with exit code 1
    And the error message reports "Network timeout: Unable to reach Mouser API"
    And the error message suggests "Please check your internet connection and try again"

  @wip
  Scenario: Graceful degradation with inventory matching failures
    Given a KiCad project named "MixedProject" containing components:
      | Reference | Value | Footprint |
      | R1        | 10k   | R_0805    |
      | C1        | 100nF | C_0805    |
      | U1        | Unknown | QFN64   |
    And an inventory file "partial-inventory.csv" containing some matching components:
      | IPN | Category | Value | Package | Manufacturer | Description |
      | RES001 | Resistor | 10k | R_0805 | Generic | 10k ohm resistor |
      | CAP001 | Capacitor | 100nF | C_0805 | Generic | 100nF capacitor |
    When I generate a generic BOM for MixedProject using partial-inventory.csv
    Then the BOM generation succeeds with exit code 0
    And the output contains warning "Unable to match component U1 (Unknown, QFN64) - no suitable inventory parts found"
    And the BOM file contains matched components R1 and C1 with inventory data
    And the BOM file contains unmatched component U1 with schematic data only
