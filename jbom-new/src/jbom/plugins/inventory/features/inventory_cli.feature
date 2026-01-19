Feature: Inventory CLI Flags and Error Handling
  As a user
  I want reliable CLI control and clear error messages
  So that I can manage inventory files confidently

  Scenario: -o stdout writes CSV to stdout
    Given a clean test environment
    And a KiCad project named "FlagsProject"
    And the schematic contains components:
      | Reference | Value | Package | Footprint         |
      | R1        | 10K   | 0603    | R_0603_1608Metric |
      | C1        | 100nF | 0603    | C_0603_1608Metric |
    When I run "jbom inventory -o stdout" in the project directory
    Then the command exits with code 0
    And stdout contains "IPN,Category,Value,Package"
    And stdout contains "RES_10K,RES,10K,0603"
    And stdout contains "CAP_100nF,CAP,100nF,0603"

  Scenario: Standard field mapping
    Given a clean test environment
    And a KiCad project named "FlagsProject"
    And the schematic contains components:
      | Reference | Value | Package | Footprint         | Tolerance | Voltage |
      | R1        | 4K7   | 0805    | R_0805_2012Metric | 5%        | 25V     |
    When I run "jbom inventory -o stdout" in the project directory
    Then the command exits with code 0
    And stdout contains property columns for Tolerance and Voltage
    And stdout contains "5%" and "25V" in the data

  Scenario: -o console shows formatted table
    Given a clean test environment
    And a KiCad project named "ConsoleFlags"
    And the schematic contains components:
      | Reference | Value | Package | Footprint         |
      | R1        | 470   | 0603    | R_0603_1608Metric |
      | C1        | 22pF  | 0603    | C_0603_1608Metric |
    When I run "jbom inventory -o console" in the project directory
    Then the command exits with code 0
    And the console output contains "Generated 2 inventory items"
    And the console output contains a formatted table
    And the console output contains "RES_470"
    And the console output contains "CAP_22pF"

  Scenario: Custom output file path
    Given a clean test environment
    And a KiCad project named "CustomPath"
    And the schematic contains components:
      | Reference | Value | Package | Footprint         |
      | L1        | 10uH  | 1206    | L_1206_3216Metric |
    When I run "jbom inventory -o my_custom_inventory.csv" in the project directory
    Then the command exits with code 0
    And a file named "my_custom_inventory.csv" exists in the project directory
    And the file contains "IND_10uH"

  Scenario: Multiple schematic files - prefer directory-matching name
    Given a clean test environment
    And a KiCad project named "MainProject"
    And the main schematic contains components:
      | Reference | Value | Package | Footprint         |
      | R1        | 1K    | 0603    | R_0603_1608Metric |
    And an extra schematic file named "submodule.kicad_sch" exists with components:
      | Reference | Value | Package | Footprint         |
      | R2        | 2K    | 0603    | R_0603_1608Metric |
    When I run "jbom inventory -o stdout" in the project directory
    Then the command exits with code 0
    And stdout contains "RES_1K"
    And stdout does not contain "RES_2K"

  Scenario: Append to nonexistent file creates new file
    Given a clean test environment
    And a KiCad project named "NewFile"
    And the schematic contains components:
      | Reference | Value | Package | Footprint         |
      | R1        | 4K7   | 0805    | R_0805_2012Metric |
    When I run "jbom inventory -o new_inventory.csv" in the project directory
    Then the command exits with code 0
    And a file named "new_inventory.csv" exists in the project directory
    And the file contains the component from the project

  Scenario: No schematic files in directory returns error
    Given a clean test environment
    And I am in an empty project directory
    When I run "jbom inventory" in the project directory
    Then the command exits with code 2
    And stderr contains "No .kicad_sch file found"

  Scenario: Nonexistent project path returns error
    Given a clean test environment
    And I am in an empty project directory
    When I run "jbom inventory nonexistent_project.kicad_sch" in the project directory
    Then the command exits with code 2
    And stderr contains "PROJECT not found"

  Scenario: Permission denied on output file
    Given a clean test environment
    And a read-only directory named "readonly"
    And a KiCad project named "PermissionTest"
    And the schematic contains components:
      | Reference | Value | Package | Footprint         |
      | R1        | 1K    | 0603    | R_0603_1608Metric |
    When I run "jbom inventory -o readonly/output.csv" in the project directory
    Then the command exits with code 1
    And stderr contains "Permission denied"
