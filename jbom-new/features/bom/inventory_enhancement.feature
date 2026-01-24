Feature: BOM Inventory Enhancement
  As a sourcing engineer
  I want to enhance BOM output with inventory data
  So that I get manufacturer details, part numbers, and sourcing information

  Background:
    Given the generic fabricator is selected
    And an inventory file "component_inventory.csv" that contains:
      | IPN       | Category  | Value | Description         | Package | Manufacturer | MFGPN           | LCSC    | Voltage | Tolerance |
      | RES_10K   | RESISTOR  | 10k   | 10k Ohm resistor    | 0603    | Yageo        | RC0603FR-0710KL | C25804  | 75V     | 1%        |
      | CAP_100N  | CAPACITOR | 100nF | 100nF ceramic cap   | 0603    | Murata       | GRM188R71H104KA | C14663  | 50V     | 10%       |
      | LED_RED   | LED       | RED   | Red LED 20mA        | 0603    | Kingbright   | APT1608SRCPRV   | C2286   | 2V      |           |
    And an inventory file "enhanced_inventory.csv" that contains:
      | IPN       | Category  | Value | Description         | Package | Manufacturer | MFGPN           | LCSC    | Datasheet                    |
      | IC_LM358  | IC        | LM358 | Dual Op-Amp         | SOIC-8  | Texas Instruments | LM358DR  | C7950   | https://ti.com/lit/ds/lm358 |
    And a schematic that contains:
      | Reference | Value | Footprint         | LibID     |
      | R1        | 10k   | R_0603_1608       | Device:R  |
      | R2        | 10k   | R_0603_1608       | Device:R  |
      | C1        | 100nF | C_0603_1608       | Device:C  |
      | LED1      | RED   | LED_0603          | Device:LED|
      | U1        | LM358 | SOIC-8_3.9x4.9mm | Device:IC |

  Scenario: Basic BOM enhancement with single inventory file
    When I run jbom command "bom --inventory component_inventory.csv -o console"
    Then the command should succeed
    And the output should contain "Bill of Materials"
    And the output should contain "R1, R2"
    And the output should contain "10k"
    And the output should contain "C1"
    And the output should contain "100nF"
    And the output should contain "LED1"
    And the output should contain "RED"
    And the output should contain "U1"
    And the output should contain "LM358"
    And the output should contain "Inventory enhanced:"

  Scenario: BOM enhancement with multiple inventory files (current implementation)
    When I run jbom command "bom --inventory component_inventory.csv --inventory enhanced_inventory.csv -o console -v"
    Then the command should succeed
    And the output should contain "Enhancing BOM with 2 inventory file(s)"
    And the output should contain "Note: Using primary inventory file component_inventory.csv, multi-file enhancement coming soon"
    And the output should contain "Bill of Materials"
    And the output should contain "Inventory enhanced:"

  Scenario: BOM enhancement CSV output includes inventory columns
    When I run jbom command "bom --inventory component_inventory.csv -o -"
    Then the command should succeed
    And the output should contain "Reference,Quantity,Description,Value,Package,Footprint,Manufacturer,Part Number"
    And the output should contain "R1, R2"
    And the output should contain "10k,,R_0603_1608"
    And the output should contain "C1,1,,100nF"
    And the output should contain "LED1,1,Red LED 20mA,RED"
    And the output should contain "Kingbright"

  Scenario: BOM enhancement to file output
    When I run jbom command "bom --inventory component_inventory.csv -o enhanced_bom.csv"
    Then the command should succeed
    And a file named "enhanced_bom.csv" should exist
    And the file "enhanced_bom.csv" should contain "Manufacturer,Part Number"
    And the file "enhanced_bom.csv" should contain "Kingbright"
    And the file "enhanced_bom.csv" should contain "Red LED 20mA"

  Scenario: BOM without inventory enhancement (baseline)
    When I run jbom command "bom -o console"
    Then the command should succeed
    And the output should contain "Bill of Materials"
    And the output should contain "R1, R2"
    And the output should contain "10k"
    And the output should not contain "Inventory enhanced:"
    And the output should not contain "Yageo"

  Scenario: BOM with missing inventory file
    When I run jbom command "bom --inventory nonexistent.csv -o console"
    Then the command should fail
    And the output should contain "Error: Inventory file not found: nonexistent.csv"

  Scenario: BOM verbose output shows enhancement details
    When I run jbom command "bom --inventory component_inventory.csv -o console -v"
    Then the command should succeed
    And the output should contain "Enhancing BOM with 1 inventory file(s)"
    And the output should contain "Bill of Materials"
    And the output should contain "Inventory enhanced:"

  Scenario: BOM enhancement with fabricator selection
    When I run jbom command "bom --inventory component_inventory.csv --fabricator jlc -o console"
    Then the command should succeed
    And the output should contain "Bill of Materials"
    And the output should contain "Inventory enhanced:"
    # Inventory enhancement should work with any fabricator preset

  Scenario: BOM enhancement preserves filtering options
    When I run jbom command "bom --inventory component_inventory.csv --include-dnp -o console"
    Then the command should succeed
    And the output should contain "Bill of Materials"
    # Should show both enhanced inventory data and respect DNP filtering

  Scenario: Multiple inventory files with different component coverage
    When I run jbom command "bom --inventory component_inventory.csv --inventory enhanced_inventory.csv -o - -v"
    Then the command should succeed
    And the output should contain "Enhancing BOM with 2 inventory file(s)"
    And the output should contain "Reference,Quantity,Description,Value"
    And the output should contain "R1, R2"
    And the output should contain "10k"
    And the output should contain "U1"
    And the output should contain "LM358"
