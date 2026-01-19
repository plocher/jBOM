Feature: Inventory Generation
  As a jBOM user
  I want to create and maintain inventory files from KiCad projects
  So that I can build an indirection layer between designs and fabrication

  Scenario: Bootstrap inventory from single project
    Given a clean test environment
    And a KiCad project named "Project1"
    And the schematic contains components:
      | Reference | Value | Package | Footprint         | Tolerance | Voltage | Type     | Manufacturer | MFGPN  |
      | R1        | 10K   | 0603    | R_0603_1608Metric | 5%        |         |          |              |        |
      | R2        | 10K   | 0603    | R_0603_1608Metric | 5%        |         |          |              |        |
      | C1        | 100nF | 0603    | C_0603_1608Metric |           | 50V     | Ceramic  |              |        |
      | U1        | NE555 | SOIC-8  | SOIC-8_3.9x4.9mm  |           |         |          | TI           | NE555P |
    When I run "jbom inventory" in the project directory
    Then the command exits with code 0
    And a file named "Project1.inventory.csv" exists in the project directory
    And the inventory file contains 3 unique items
    And the inventory has standard columns: IPN, Category, Value, Package, Description

  Scenario: Generate inventory to stdout
    Given a clean test environment
    And a KiCad project named "StdoutProject"
    And the schematic contains components:
      | Reference | Value | Package | Footprint         |
      | R1        | 4.7K  | 0805    | R_0805_2012Metric |
    When I run "jbom inventory -o stdout" in the project directory
    Then the command exits with code 0
    And stdout contains CSV data with headers
    And stdout contains "RES_4.7K,RES,4.7K,0805"

  Scenario: Generate inventory to console table
    Given a clean test environment
    And a KiCad project named "ConsoleProject"
    And the schematic contains components:
      | Reference | Value | Package | Footprint         |
      | L1        | 10uH  | 1206    | L_1206_3216Metric |
      | L2        | 22uH  | 1206    | L_1206_3216Metric |
    When I run "jbom inventory -o console" in the project directory
    Then the command exits with code 0
    And the console output contains "Generated 2 inventory items"
    And the console output contains a formatted inventory table

  Scenario: Append components to existing inventory
    Given a clean test environment
    And an existing inventory file "base.csv" with components:
      | IPN       | Category | Value | Package | Manufacturer | MFGPN          |
      | RES_1K    | RES      | 1K    | 0603    | Yageo        | RC0603FR-071KL |
      | CAP_100nF | CAP      | 100nF | 0603    |              |                |
    And a KiCad project named "Project2"
    And the schematic contains components:
      | Reference | Value | Package | Footprint         | Tolerance |
      | R1        | 10K0  | 0603    | R_0603_1608Metric | 1%        |
      | R2        | 1K0   | 0603    | R_0603_1608Metric | 5%        |
      | L1        | 22uH  | 1206    | L_1206_3216Metric |           |
    When I run "jbom inventory -o base.csv" in the project directory
    Then the command exits with code 0
    And the inventory file "base.csv" contains 4 unique items
    And the existing RES_1K entry is preserved
    And new entries RES_10K and IND_22uH are added

  Scenario: Handle component deduplication
    Given a clean test environment
    And a KiCad project named "DedupeProject"
    And the schematic contains components:
      | Reference | Value | Package | Footprint         | Tolerance |
      | R1        | 10K   | 0603    | R_0603_1608Metric | 5%        |
      | R2        | 10K   | 0603    | R_0603_1608Metric | 5%        |
      | R3        | 10K0  | 0603    | R_0603_1608Metric | 1%        |
      | C1        | 100nF | 0603    | C_0603_1608Metric |           |
    When I run "jbom inventory -o stdout" in the project directory
    Then the command exits with code 0
    And the inventory contains exactly 3 unique items
    And stdout contains "RES_10K" for 5% tolerance and "RES_10K0" for 1% tolerance

  Scenario: Handle empty schematic
    Given a clean test environment
    And a KiCad project named "EmptyProject"
    And the schematic contains no components
    When I run "jbom inventory -o stdout" in the project directory
    Then the command exits with code 0
    And stdout contains CSV headers only
    And the output shows "Generated 0 inventory items from 0 components"
