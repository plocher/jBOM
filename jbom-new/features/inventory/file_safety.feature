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
    Given a file named "existing_inventory.csv" exists with content:
      """
      IPN,Category,Value
      RES_1K,RESISTOR,1k
      """
    When I run jbom command "inventory -o existing_inventory.csv"
    Then the command should fail
    And the output should contain "Error: Output file 'existing_inventory.csv' already exists. Use --force to overwrite."
    And the file "existing_inventory.csv" should contain "RES_1K"

  Scenario: Allow overwrite with --force flag
    Given a file named "existing_inventory.csv" exists with content:
      """
      IPN,Category,Value
      RES_1K,RESISTOR,1k
      """
    When I run jbom command "inventory -o existing_inventory.csv --force"
    Then the command should succeed
    And the output should contain "Generated inventory with 2 items written to existing_inventory.csv"
    And the file "existing_inventory.csv" should contain "RES_10K"
    And the file "existing_inventory.csv" should contain "CAP_100N"

  Scenario: Create timestamped backup when overwriting with --force
    Given a file named "inventory.csv" exists with content:
      """
      IPN,Category,Value
      OLD_COMPONENT,RESISTOR,1k
      """
    When I run jbom command "inventory -o inventory.csv --force -v"
    Then the command should succeed
    And the output should contain "Created backup: inventory.backup."
    And the output should contain "Generated inventory with 2 items written to inventory.csv"
    And a backup file matching "inventory.backup.*\.csv" should exist
    And the backup file should contain "OLD_COMPONENT"
    And the file "inventory.csv" should contain "RES_10K"

  Scenario: Backup filename format with timestamp
    Given a file named "test_inventory.csv" exists with content:
      """
      IPN,Category,Value
      TEST_COMPONENT,RESISTOR,1k
      """
    When I run jbom command "inventory -o test_inventory.csv --force"
    Then the command should succeed
    And a backup file matching "test_inventory\.backup\.\d{8}_\d{6}\.csv" should exist

  Scenario: Graceful handling of backup failure
    Given a file named "readonly_inventory.csv" exists with content:
      """
      IPN,Category,Value
      TEST,RESISTOR,1k
      """
    And the directory is read-only
    When I run jbom command "inventory -o readonly_inventory.csv --force -v"
    Then the command should succeed
    And the output should contain "Warning: Failed to create backup"
    And the output should contain "Generated inventory with 2 items written to readonly_inventory.csv"

  Scenario: No backup created for new files
    When I run jbom command "inventory -o new_inventory.csv"
    Then the command should succeed
    And the output should contain "Generated inventory with 2 items written to new_inventory.csv"
    And no backup files should exist
    And the file "new_inventory.csv" should exist

  Scenario: Console output bypasses file safety checks
    Given a file named "existing.csv" exists
    When I run jbom command "inventory -o console"
    Then the command should succeed
    And the output should contain "Generated inventory with 2 items"
    And no backup files should exist

  Scenario: CSV stdout output bypasses file safety checks
    Given a file named "existing.csv" exists
    When I run jbom command "inventory -o -"
    Then the command should succeed
    And the output should contain "Reference,X(mm),Y(mm)"
    And no backup files should exist
