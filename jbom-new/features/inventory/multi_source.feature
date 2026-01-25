Feature: Multi-Source Inventory
  As a sourcing engineer
  I want to combine multiple inventory sources with proper precedence
  So that I can use the best available part data from multiple sources

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
    When I run jbom command "inventory --inventory primary_inventory.csv --inventory secondary_inventory.csv --filter-matches -o console -v"
    Then the command should succeed
    And the output should contain "Loading 2 inventory file(s) with precedence order"
    And the output should contain "primary: primary_inventory.csv"
    And the output should contain "precedence 2: secondary_inventory.csv"
    And the output should contain "Merged inventory: 4 total items"
    And the output should not contain "RES-10K-0603-E12"
    And the output should not contain "CAP-100nF-0603-X7R"
    And the output should not contain "LED-RED-0603-20mA"

  Scenario: Primary inventory takes precedence over secondary
    # Verifies that when RES_10K exists in both inventories, primary (Yageo) wins over secondary (Vishay)
    When I run jbom command "inventory --inventory primary_inventory.csv --inventory secondary_inventory.csv -o console -v"
    Then the command should succeed
    And the output should contain "primary: primary_inventory.csv (2/2 items added)"
    And the output should contain "precedence 2: secondary_inventory.csv (1/2 items added)"
    And the output should contain "Merged inventory: 3 total items"
    And the output should contain "Matched RES-10K-0603-E12"

  Scenario: BOM enhancement with multiple inventory files (partial implementation)
    When I run jbom command "bom --inventory primary_inventory.csv --inventory secondary_inventory.csv -o console -v"
    Then the command should succeed
    And the output should contain "Enhancing BOM with 2 inventory file(s)"
    And the output should contain "Note: Using primary inventory file primary_inventory.csv, multi-file enhancement coming soon"

  Scenario: Single inventory file for reference (backward compatibility)
    # Test that single --inventory file works for reference/filtering
    When I run jbom command "inventory --inventory primary_inventory.csv -o single_output.csv"
    Then the command should succeed

  Scenario: Empty inventory files handled gracefully
    Given an inventory file "empty_inventory.csv" that contains:
      | IPN | Category | Value | Description | Package | Manufacturer | MFGPN |
    When I run jbom command "inventory --inventory primary_inventory.csv --inventory empty_inventory.csv -o console -v"
    Then the command should succeed
    And the output should contain "primary: primary_inventory.csv (2/2 items added)"
    And the output should contain "precedence 2: empty_inventory.csv (0/0 items added)"
    And the output should contain "Merged inventory: 2 total items"

  Scenario: Missing inventory file handling with multiple files
    When I run jbom command "inventory --inventory primary_inventory.csv --inventory nonexistent.csv -o console -v"
    Then the command should succeed
    And the output should contain "Error: Inventory file not found: nonexistent.csv"
    And the output should contain "primary: primary_inventory.csv (2/2 items added)"
    And the output should contain "Merged inventory: 2 total items"

  Scenario: Three inventory files with complex precedence
    # Tests that primary inventory takes precedence over secondary and tertiary for RES_10K
    # RES_10K appears in all three: Yageo (primary) should win over Vishay (secondary) and Panasonic (tertiary)
    Given an inventory file "tertiary_inventory.csv" that contains:
      | IPN                  | Category  | Value | Description         | Package | Manufacturer | MFGPN           |
      | RES-10K-0603-E96     | RESISTOR  | 10k   | Tertiary resistor   | 0603    | Panasonic    | ERJ-3EKF1002V   |
      | RES-22K-0603-E12     | RESISTOR  | 22k   | 22k Ohm resistor    | 0603    | Yageo        | RC0603FR-0722KL |
      | IC-LM358-SOIC8-STD   | IC        | LM358 | Dual Op-Amp         | SOIC-8  | TI           | LM358DR         |
    When I run jbom command "inventory --inventory primary_inventory.csv --inventory secondary_inventory.csv --inventory tertiary_inventory.csv -o console -v"
    Then the command should succeed
    And the output should contain "Loading 3 inventory file(s) with precedence order"
    And the output should contain "primary: primary_inventory.csv (2/2 items added)"
    And the output should contain "precedence 2: secondary_inventory.csv (1/2 items added)"
    And the output should contain "precedence 3: tertiary_inventory.csv (2/3 items added)"
    And the output should contain "Merged inventory: 5 total items"
    And the output should contain "Matched RES-10K-0603-E12"

  Scenario: Filter matches with multiple sources shows only unmatched items
    # This scenario verifies that --filter-matches only shows components
    # that couldn't be matched in ANY of the provided inventory files
    When I run jbom command "inventory --inventory primary_inventory.csv --inventory secondary_inventory.csv --filter-matches -o console"
    Then the command should succeed
    And the output should not contain "RES-10K-0603-E12"
    And the output should not contain "CAP-100nF-0603-X7R"
    And the output should not contain "LED-RED-0603-20mA"

  Scenario: Multi-source inventory export to file
    # Verifies that merged inventory includes components from all sources with proper precedence
    When I run jbom command "inventory --inventory primary_inventory.csv --inventory secondary_inventory.csv -o merged_output.csv"
    Then the command should succeed
    And a file named "merged_output.csv" should exist
    And the file "merged_output.csv" should contain these inventory data elements:
      | RES-10K-0603-E12 | CAP-100nF-0603-X7R | LED-RED-0603-20mA |
