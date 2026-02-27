Feature: Multi-Source Inventory Edge Cases
  As a developer maintaining jBOM
  I want robust handling of edge cases in multi-source inventory
  So that users get predictable behavior even with problematic data

  Background:
    Given the generic fabricator is selected
    And a schematic that contains:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10k   | R_0603_1608 | Device:R |

  Scenario: No inventory files specified with --filter-matches
    When I run jbom command "inventory --filter-matches -o console"
    Then the command should fail
    And the output should contain "Error: --filter-matches requires --inventory file(s)"

  Scenario: All inventory files missing
    When I run jbom command "inventory --inventory missing1.csv --inventory missing2.csv -o -"
    Then the command should fail
    And the output reports errors for files:
      | filename     |
      | missing1.csv |
      | missing2.csv |

  Scenario: Malformed inventory file with valid backup file
    Given an inventory file "malformed.csv" that contains:
      """
      This is not a valid CSV file
      Missing headers, invalid structure
      R1,10k,incomplete row
      """
    And an inventory file "backup.csv" that contains:
      | IPN     | Category | Value | Description | Package | Manufacturer | MFGPN |
      | RES_10K | RESISTOR | 10k   | Backup item | 0603    | Yageo        | TEST  |
    When I run jbom command "inventory --inventory malformed.csv --inventory backup.csv -o -"
    Then the command should succeed
    And the output reports errors for files:
      | filename    |
      | malformed.csv |
    And the CSV output has components where:
      | Category | Value |
      | RES      | 10k   |

  Scenario: Empty project with multi-source inventory
    Given a schematic that contains:
      | Reference | Value | Footprint |
    When I run jbom command "inventory --inventory backup.csv -o console"
    Then the command should fail
    And the output should contain "Error: No components found in project. Cannot create inventory from empty schematic."

  Scenario: Multi-supplier alternatives with same IPN
    Given an inventory file "primary_supplier.csv" that contains:
      | IPN     | Category | Value | Package | Manufacturer | MFGPN |
      | RES_10K | RESISTOR | 10k   | 0603    | Yageo        | Y100  |
    And an inventory file "alternate_supplier.csv" that contains:
      | IPN     | Category | Value | Package | Manufacturer | MFGPN  |
      | RES_10K | RESISTOR | 10k   | 0603    | Vishay       | V222   |
    When I run jbom command "inventory --inventory primary_supplier.csv --inventory alternate_supplier.csv -o -"
    Then the command should succeed
    And the CSV output has components where:
      | Category | Value |
      | RES      | 10k   |

  Scenario: Large number of inventory files (stress test)
    Given an inventory file "file1.csv" that contains:
      | IPN    | Category | Value | Description | Package | Manufacturer | MFGPN |
      | RES_1K | RESISTOR | 1k    | File 1 item | 0603    | Yageo        | TEST1 |
    And an inventory file "file2.csv" that contains:
      | IPN    | Category | Value | Description | Package | Manufacturer | MFGPN |
      | RES_2K | RESISTOR | 2k    | File 2 item | 0603    | Yageo        | TEST2 |
    And an inventory file "file3.csv" that contains:
      | IPN    | Category | Value | Description | Package | Manufacturer | MFGPN |
      | RES_3K | RESISTOR | 3k    | File 3 item | 0603    | Yageo        | TEST3 |
    And an inventory file "file4.csv" that contains:
      | IPN    | Category | Value | Description | Package | Manufacturer | MFGPN |
      | RES_4K | RESISTOR | 4k    | File 4 item | 0603    | Yageo        | TEST4 |
    And an inventory file "file5.csv" that contains:
      | IPN    | Category | Value | Description | Package | Manufacturer | MFGPN |
      | RES_5K | RESISTOR | 5k    | File 5 item | 0603    | Yageo        | TEST5 |
    When I run jbom command "inventory --inventory file1.csv --inventory file2.csv --inventory file3.csv --inventory file4.csv --inventory file5.csv -o -"
    Then the command should succeed
    # Project has only one component (10k); merged inventory does not add rows to project-generated inventory.
    And the CSV output has components where:
      | Category | Value |
      | RES      | 10k   |

  Scenario: File permission errors handled gracefully
    Given an inventory file "restricted.csv" that contains:
      | IPN     | Category | Value | Description | Package | Manufacturer | MFGPN |
      | RES_1K  | RESISTOR | 1k    | Test item   | 0603    | Yageo        | TEST  |
    And the file "restricted.csv" is unreadable
    And an inventory file "accessible.csv" that contains:
      | IPN     | Category | Value | Description | Package | Manufacturer | MFGPN |
      | RES_10K | RESISTOR | 10k   | Good item   | 0603    | Yageo        | GOOD  |
    When I run jbom command "inventory --inventory restricted.csv --inventory accessible.csv -o -"
    Then the command should succeed
    And the output reports errors for files:
      | filename       |
      | restricted.csv |
