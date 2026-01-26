Feature: Multi-Source Inventory
  As a sourcing engineer
  I want to combine multiple inventory sources
  So that I can use the available part data from multiple sources

  Background:
    Given the generic fabricator is selected
    And an inventory file "primary_inventory.csv" that contains:
      | IPN                | Category  | Value | Description         | Package | Manufacturer | MFGPN           |
      | RES-10K-0603-E12   | RESISTOR  | 10k   | 10k Ohm resistor    | 0603    | Yageo        | RC0603FR-0710KL |
      | CAP-100nF-0603-X7R | CAPACITOR | 100nF | 100nF ceramic cap   | 0603    | Murata       | GRM188R71H104KA |
    And an inventory file "secondary_inventory.csv" that contains:
      | IPN                | Category  | Value | Description         | Package | Manufacturer | MFGPN           |
      | RES-10K-0603-E24   | RESISTOR  | 10k   | Secondary resistor  | 0603    | Vishay       | CRCW060310K0FKEA|
      | LED-RED-0603-20mA  | LED       | RED   | Red LED 20mA        | 0603    | Kingbright   | APT1608SRCPRV   |
    And a schematic that contains:
      | Reference | Value | Footprint   | LibID     |
      | R1        | 10k   | R_0603_1608 | Device:R  |
      | R2        | 22k   | R_0603_1608 | Device:R  |
      | C1        | 100nF | C_0603_1608 | Device:C  |
      | LED1      | RED   | LED_0603    | Device:LED|

  Scenario: Multiple inventory files in inventory command
    When I run jbom command "inventory --inventory primary_inventory.csv --inventory secondary_inventory.csv --filter-matches -o -"
    Then the command should succeed
    # only unmatched project components should remain
    And the CSV output has rows where:
      | Value | Category |
      | 22k   | RES      |

  Scenario: BOM enhancement with multiple inventory files (partial implementation)
    When I run jbom command "bom --inventory primary_inventory.csv --inventory secondary_inventory.csv -o console -v"
    Then the command should succeed

  Scenario: Empty inventory files handled gracefully
    Given an inventory file "empty_inventory.csv" that contains:
      | IPN | Category | Value | Description | Package | Manufacturer | MFGPN |
    When I run jbom command "inventory --inventory primary_inventory.csv --inventory empty_inventory.csv --filter-matches -o -"
    Then the command should succeed
    And the CSV output has rows where:
      | Value | Category |
      | 22k   | RES      |

  Scenario: Missing inventory file handling with multiple files
    When I run jbom command "inventory --inventory primary_inventory.csv --inventory nonexistent.csv --filter-matches -o -"
    Then the command should fail

  Scenario: Three inventory files with complex precedence
    # Validate remaining unmatched after three inventories (LED may remain)
    Given an inventory file "tertiary_inventory.csv" that contains:
      | IPN                  | Category  | Value | Description         | Package | Manufacturer | MFGPN           |
      | RES-10K-0603-E96     | RESISTOR  | 10k   | Tertiary resistor   | 0603    | Panasonic    | ERJ-3EKF1002V   |
      | RES-22K-0603-E12     | RESISTOR  | 22k   | 22k Ohm resistor    | 0603    | Yageo        | RC0603FR-0722KL |
      | IC-LM358-SOIC8-STD   | IC        | LM358 | Dual Op-Amp         | SOIC-8  | TI           | LM358DR         |
    When I run jbom command "inventory --inventory primary_inventory.csv --inventory secondary_inventory.csv --inventory tertiary_inventory.csv --filter-matches -o -"
    Then the command should succeed
    And the CSV output has components where:
      | Category | Value |
      | LED      | RED   |
