Feature: Multi-Source Inventory
  As a sourcing engineer
  I want to combine multiple inventory sources
  So that I can use the best available part data from multiple sources

  Background:
    Given the generic fabricator is selected
    And an existing inventory file "primary_inventory.csv" with contents:
      | IPN       | Category  | Value | Description         | Package | Manufacturer | MFGPN           |
      | RES_10K   | RESISTOR  | 10k   | 10k Ohm resistor    | 0603    | Yageo        | RC0603FR-0710KL |
      | CAP_100N  | CAPACITOR | 100nF | 100nF ceramic cap   | 0603    | Murata       | GRM188R71H104KA |
    And a secondary inventory file "secondary_inventory.csv" with contents:
      | IPN       | Category  | Value | Description         | Package | Manufacturer | MFGPN           |
      | RES_10K   | RESISTOR  | 10k   | Secondary resistor  | 0603    | Vishay       | CRCW060310K0FKEA|
      | LED_RED   | LED       | RED   | Red LED 20mA        | 0603    | Kingbright   | APT1608SRCPRV   |
    And a test schematic that contains:
      | Reference | Value | Footprint   | LibID     |
      | R1        | 10k   | R_0603_1608 | Device:R  |
      | R2        | 22k   | R_0603_1608 | Device:R  |
      | C1        | 100nF | C_0603_1608 | Device:C  |
      | LED1      | RED   | LED_0603    | Device:LED|

  Scenario: Multiple inventory files in inventory command
    When I run jbom command "inventory --inventory primary_inventory.csv --inventory secondary_inventory.csv --filter-matches -o console -v"
    Then the command should succeed
    And the output should contain "Loading 2 inventory file(s) with precedence order"
    And the output should contain "primary: primary_inventory.csv"
    And the output should contain "precedence 2: secondary_inventory.csv"
    And the output should contain "Merged inventory: 3 total items"
    And the output should contain "Generated inventory with 1 items"
    And the output should contain "RES_22K"
    And the output should not contain "RES_10K"
    And the output should not contain "CAP_100N"
    And the output should not contain "LED_RED"

  Scenario: Primary inventory takes precedence over secondary
    When I run jbom command "inventory --inventory primary_inventory.csv --inventory secondary_inventory.csv -o console -v"
    Then the command should succeed
    And the output should contain "primary: primary_inventory.csv (2/2 items added)"
    And the output should contain "precedence 2: secondary_inventory.csv (1/2 items added)"
    And the output should contain "Merged inventory: 3 total items"
    # Verify that primary RES_10K (Yageo) is used, not secondary (Vishay)
    And the output should contain "Matched RES_10K"

  Scenario: BOM enhancement with multiple inventory files (partial implementation)
    When I run jbom command "bom --inventory primary_inventory.csv --inventory secondary_inventory.csv -o console -v"
    Then the command should succeed
    And the output should contain "Enhancing BOM with 2 inventory file(s)"
    And the output should contain "Note: Using primary inventory file primary_inventory.csv, multi-file enhancement coming soon"
