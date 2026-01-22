Feature: Multi-Source Inventory Edge Cases
  As a developer maintaining jBOM
  I want robust handling of edge cases in multi-source inventory
  So that users get predictable behavior even with problematic data

  Background:
    Given the generic fabricator is selected
    And a minimal test schematic that contains:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10k   | R_0603_1608 | Device:R |

  Scenario: No inventory files specified with --filter-matches
    When I run jbom command "inventory --filter-matches -o console"
    Then the command should succeed
    And the output should contain "Warning: --filter-matches requires --inventory file(s)"
    And the output should contain "Generated inventory with 1 items"

  Scenario: All inventory files missing
    When I run jbom command "inventory --inventory missing1.csv --inventory missing2.csv -o console -v"
    Then the command should succeed
    And the output should contain "Error: Inventory file not found: missing1.csv"
    And the output should contain "Error: Inventory file not found: missing2.csv"
    And the output should contain "Error: No inventory items loaded from any file"
    And the output should contain "Generated inventory with 1 items"

  Scenario: Malformed inventory file with valid backup file
    Given a malformed inventory file "malformed.csv" with contents:
      """
      This is not a valid CSV file
      Missing headers, invalid structure
      R1,10k,incomplete row
      """
    And a valid inventory file "backup.csv" with contents:
      | IPN     | Category | Value | Description | Package | Manufacturer | MFGPN |
      | RES_10K | RESISTOR | 10k   | Backup item | 0603    | Yageo        | TEST  |
    When I run jbom command "inventory --inventory malformed.csv --inventory backup.csv -o console -v"
    Then the command should succeed
    And the output should contain "Error loading malformed.csv:"
    And the output should contain "precedence 2: backup.csv (1/1 items added)"
    And the output should contain "Merged inventory: 1 total items"

  Scenario: Empty project with multi-source inventory
    Given a schematic that contains:
      | Reference | Value | Footprint |
    When I run jbom command "inventory --inventory backup.csv -o console"
    Then the command should fail
    And the output should contain "Error: No components found in project. Cannot create inventory from empty schematic."

  Scenario: Duplicate IPN across multiple files shows precedence
    Given a primary inventory file "dup_primary.csv" with contents:
      | IPN     | Category | Value | Description     | Package | Manufacturer | MFGPN    |
      | RES_10K | RESISTOR | 10k   | Primary version | 0603    | Yageo        | PRIMARY  |
    And a secondary inventory file "dup_secondary.csv" with contents:
      | IPN     | Category | Value | Description       | Package | Manufacturer | MFGPN      |
      | RES_10K | RESISTOR | 10k   | Secondary version | 0603    | Vishay       | SECONDARY  |
    When I run jbom command "inventory --inventory dup_primary.csv --inventory dup_secondary.csv -o console -v"
    Then the command should succeed
    And the output should contain "primary: dup_primary.csv (1/1 items added)"
    And the output should contain "precedence 2: dup_secondary.csv (0/1 items added)"
    And the output should contain "Matched RES_10K"
    # Verify primary version is used in matching, not secondary

  Scenario: Large number of inventory files (stress test)
    Given multiple inventory files with unique IPNs:
      | file_name   | IPN       | Description  |
      | file1.csv   | RES_1K    | File 1 item  |
      | file2.csv   | RES_2K    | File 2 item  |
      | file3.csv   | RES_3K    | File 3 item  |
      | file4.csv   | RES_4K    | File 4 item  |
      | file5.csv   | RES_5K    | File 5 item  |
    When I run jbom command "inventory --inventory file1.csv --inventory file2.csv --inventory file3.csv --inventory file4.csv --inventory file5.csv -o console -v"
    Then the command should succeed
    And the output should contain "Loading 5 inventory file(s) with precedence order"
    And the output should contain "Merged inventory: 5 total items"

  Scenario: File permission errors handled gracefully
    Given an inaccessible inventory file "restricted.csv" with no read permissions
    And a valid inventory file "accessible.csv" with contents:
      | IPN     | Category | Value | Description | Package | Manufacturer | MFGPN |
      | RES_10K | RESISTOR | 10k   | Good item   | 0603    | Yageo        | GOOD  |
    When I run jbom command "inventory --inventory restricted.csv --inventory accessible.csv -o console -v"
    Then the command should succeed
    And the output should contain "Error loading restricted.csv:"
    And the output should contain "precedence 2: accessible.csv (1/1 items added)"

  Scenario: Mixed single and multiple flag usage (argument parsing edge case)
    Given a valid inventory file "single.csv" with contents:
      | IPN     | Category | Value | Description | Package | Manufacturer | MFGPN |
      | RES_10K | RESISTOR | 10k   | Single item | 0603    | Yageo        | SINGLE |
    # Test that the argument parser handles the transition correctly
    When I run jbom command "inventory --inventory single.csv -o console"
    Then the command should succeed
    And the output should contain "Generated inventory with 1 items"

  Scenario: CSV with special characters and encoding
    Given an inventory file "special_chars.csv" with contents:
      | IPN          | Category | Value | Description           | Package | Manufacturer | MFGPN     |
      | RES_SPECIAL  | RESISTOR | 10kΩ  | Résistance spéciale   | 0603    | Müller & Co  | MÜ-10K-Ω  |
    When I run jbom command "inventory --inventory special_chars.csv -o console"
    Then the command should succeed
    And the output should contain "Generated inventory with 1 items"

  Scenario: Very long file paths and names
    Given an inventory file with a very long name "very_long_inventory_file_name_that_exceeds_normal_length_expectations_for_testing_robust_path_handling.csv" with contents:
      | IPN       | Category | Value | Description | Package | Manufacturer | MFGPN  |
      | RES_LONG  | RESISTOR | 10k   | Long path   | 0603    | Yageo        | LONG   |
    When I run jbom command "inventory --inventory very_long_inventory_file_name_that_exceeds_normal_length_expectations_for_testing_robust_path_handling.csv -o console"
    Then the command should succeed
    And the output should contain "Generated inventory with 1 items"
