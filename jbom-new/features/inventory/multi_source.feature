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

  Scenario: Single inventory file still works (backward compatibility)
    When I run jbom command "inventory --inventory primary_inventory.csv -o console"
    Then the command should succeed
    And the output should contain "Generated inventory with 4 items"
    And the output should contain "RES_10K"
    And the output should contain "RES_22K"
    And the output should contain "CAP_100N"
    And the output should contain "LED_RED"

  Scenario: Empty inventory files handled gracefully
    Given an empty inventory file "empty_inventory.csv" with headers only:
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
    Given a third inventory file "tertiary_inventory.csv" with contents:
      | IPN       | Category  | Value | Description         | Package | Manufacturer | MFGPN           |
      | RES_10K   | RESISTOR  | 10k   | Tertiary resistor   | 0603    | Panasonic    | ERJ-3EKF1002V   |
      | RES_22K   | RESISTOR  | 22k   | 22k Ohm resistor    | 0603    | Yageo        | RC0603FR-0722KL |
      | IC_LM358  | IC        | LM358 | Dual Op-Amp         | SOIC-8  | TI           | LM358DR         |
    When I run jbom command "inventory --inventory primary_inventory.csv --inventory secondary_inventory.csv --inventory tertiary_inventory.csv -o console -v"
    Then the command should succeed
    And the output should contain "Loading 3 inventory file(s) with precedence order"
    And the output should contain "primary: primary_inventory.csv (2/2 items added)"
    And the output should contain "precedence 2: secondary_inventory.csv (1/2 items added)"
    And the output should contain "precedence 3: tertiary_inventory.csv (2/3 items added)"
    And the output should contain "Merged inventory: 5 total items"
    # Verify primary precedence: RES_10K should be Yageo (primary), not Vishay (secondary) or Panasonic (tertiary)
    And the output should contain "Matched RES_10K"

  Scenario: Filter matches with multiple sources shows only unmatched items
    When I run jbom command "inventory --inventory primary_inventory.csv --inventory secondary_inventory.csv --filter-matches -o console"
    Then the command should succeed
    And the output should contain "Generated inventory with 1 items"
    And the output should contain "RES_22K"  # Only item not in any inventory
    And the output should not contain "RES_10K"  # Matched in primary
    And the output should not contain "CAP_100N" # Matched in primary
    And the output should not contain "LED_RED"  # Matched in secondary

  Scenario: Multi-source inventory export to file
    When I run jbom command "inventory --inventory primary_inventory.csv --inventory secondary_inventory.csv -o merged_output.csv"
    Then the command should succeed
    And a file named "merged_output.csv" should exist
    And the file "merged_output.csv" should contain "RES_10K"  # From primary
    And the file "merged_output.csv" should contain "CAP_100N" # From primary
    And the file "merged_output.csv" should contain "LED_RED"  # From secondary
    And the file "merged_output.csv" should contain "RES_22K"  # Generated from project
