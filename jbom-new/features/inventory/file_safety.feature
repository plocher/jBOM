Feature: Inventory File Safety and Backup
  As a hardware developer
  I want protection against accidental file overwrites
  So that I don't lose important inventory data

  Background:
    Given the generic fabricator is selected
    And a schematic that contains:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10k   | R_0603_1608 | Device:R |
      | C1        | 100nF | C_0603_1608 | Device:C |

  Scenario: Prevent accidental overwrite without --force flag
    Given an inventory file "existing_inventory.csv" that contains:
      | IPN              | Category | Value |
      | RES-1K-0603-E12  | RESISTOR | 1k    |
    When I run jbom command "inventory -o existing_inventory.csv"
    Then the command should fail
    And the output should contain "Error: Output file 'existing_inventory.csv' already exists. Use --force to overwrite."
    And the file "existing_inventory.csv" should contain "RES-1K-0603-E12"

  Scenario: Allow overwrite with --force flag
    Given an inventory file "existing_inventory.csv" that contains:
      | IPN              | Category | Value |
      | RES-1K-0603-E12  | RESISTOR | 1k    |
    When I run jbom command "inventory -o existing_inventory.csv --force"
    Then the command should succeed
    And the output should contain "Generated inventory with 2 items written to existing_inventory.csv"
    And the file "existing_inventory.csv" should contain "RES_10k"  # Generated (no match)
    And the file "existing_inventory.csv" should contain "CAP_100nF"  # Generated (no match)

  Scenario: Force flag successfully overwrites existing files
    Given an inventory file "inventory.csv" that contains:
      | IPN                     | Category | Value |
      | LEGACY-OLD-PART-V1      | RESISTOR | 1k    |
    When I run jbom command "inventory -o inventory.csv --force"
    Then the command should succeed
    And the file "inventory.csv" should contain "RES_10k"    # Generated (no match)
    And the file "inventory.csv" should contain "CAP_100nF"  # Generated (no match)


  Scenario: Graceful handling of backup failure
    Given an inventory file "readonly_inventory.csv" that contains:
      | IPN  | Category | Value |
      | TEST | RESISTOR | 1k    |
    And the directory is read-only
    When I run jbom command "inventory -o readonly_inventory.csv --force -v"
    Then the command should succeed
    And the output should contain "Warning: Failed to create backup"
    And the output should contain "Generated inventory with 2 items written to readonly_inventory.csv"
