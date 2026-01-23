Feature: Inventory Matching and Filtering
  As a hardware developer
  I want to match project components against existing inventory
  So that I can identify new components needed and avoid duplicates

  Background:
    Given the generic fabricator is selected
    And an inventory file "existing_inventory.csv" that contains:
      | IPN       | Category  | Value | Description        | Package | Manufacturer | MFGPN           |
      | RES_10K   | RESISTOR  | 10k   | 10k Ohm resistor   | 0603    | Yageo        | RC0603FR-0710KL |
      | RES_1K    | RESISTOR  | 1k    | 1k Ohm resistor    | 0603    | Yageo        | RC0603FR-071KL  |
      | CAP_100N  | CAPACITOR | 100nF | 100nF ceramic cap  | 0603    | Murata       | GRM188R71H104KA |
      | LED_RED   | LED       | RED   | Red LED 20mA       | 0603    | Kingbright   | APT1608SRCPRV   |
    And a schematic that contains:
      | Reference | Value | Footprint   | LibID     |
      | R1        | 10k   | R_0603_1608 | Device:R  |
      | R2        | 22k   | R_0603_1608 | Device:R  |
      | C1        | 100nF | C_0603_1608 | Device:C  |
      | C2        | 22pF  | C_0603_1608 | Device:C  |
      | LED1      | RED   | LED_0603    | Device:LED|
      | U1        | LM358 | SOIC-8      | Device:IC |

  Scenario: Basic inventory matching with --inventory flag
    When I run jbom command "inventory --inventory existing_inventory.csv -o console"
    Then the command should succeed
    And the output should contain "Generated inventory with 6 items"
    And the output should contain "RES_10K"
    And the output should contain "RES_22K"
    And the output should contain "CAP_100N"
    And the output should contain "CAP_22P"
    And the output should contain "LED_RED"
    And the output should contain "IC_LM358"

  Scenario: Filter matched components with --filter-matches
    When I run jbom command "inventory --inventory existing_inventory.csv --filter-matches -o console"
    Then the command should succeed
    And the output should contain "Generated inventory with 4 items"
    And the output should contain "RES_22K"
    And the output should contain "CAP_22P"
    And the output should contain "IC_LM358"
    And the output should not contain "RES_10K"
    And the output should not contain "CAP_100N"
    And the output should not contain "LED_RED"

  Scenario: Verbose matching shows detailed match information
    When I run jbom command "inventory --inventory existing_inventory.csv --filter-matches -o console -v"
    Then the command should succeed
    And the output should contain "Loaded 4 items from existing_inventory.csv"
    And the output should contain "Matched RES_10K"
    And the output should contain "Matched LED_RED"
    And the output should contain "No match for RES_22K"
    And the output should contain "Inventory filtering:"

  Scenario: Warning when --filter-matches used without --inventory
    When I run jbom command "inventory --filter-matches -o console"
    Then the command should succeed
    And the output should contain "Warning: --filter-matches requires --inventory file"
    And the output should contain "Generated inventory with 6 items"

  Scenario: Error handling for missing inventory file
    When I run jbom command "inventory --inventory nonexistent.csv -o console"
    Then the command should succeed
    And the output should contain "Error: Inventory file not found"
    And the output should contain "Generated inventory with 6 items"

  # Removed: Export filtered results to file scenario
  # This was a "two-for" scenario testing both file creation and content verification
  # File output is already covered by basic inventory scenarios
  # Content filtering is already verified by console output scenarios above
