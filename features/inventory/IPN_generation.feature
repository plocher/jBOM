Feature: Inventory Generation from Schematic Components
  As a hardware engineer
  I want jBOM to generate an inventory skeleton from my schematic
  So that I can bootstrap an inventory system and fill in my own IPNs

  # jBOM does NOT auto-generate IPNs. IPN is blank unless the schematic component has
  # an explicit "IPN" property. The inventory command derives Category and populates
  # Value/Package/Description from schematic data so the user can assign their own IPNs.

  Background:
    Given the generic fabricator is selected

  Scenario: Generate inventory skeleton from schematic (IPN blank without explicit property)
    Given a schematic that contains:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10k   | R_0603_1608 | Device:R |
      | C1        | 100nF | C_0603_1608 | Device:C |
      | LED1      | RED   | LED_0603    | Device:LED |
      | U1        | LM358 | SOIC-8_3.9x4.9mm | Device:IC |
    When I run jbom command "inventory -o console"
    Then the command should succeed
    And the output should contain "Generated inventory with 4 items"
    # Category-based classification still works; values are preserved
    And the output should contain "RES"
    And the output should contain "CAP"
    And the output should contain "LED"
    And the output should contain "IC"
    And the output should contain "10k"
    And the output should contain "100nF"

  Scenario: Inventory captures component values accurately
    Given a schematic that contains:
      | Reference | Value  | Footprint   | LibID     |
      | R1        | 1.2k   | R_0603_1608 | Device:R  |
      | R2        | 4.7K   | R_0805_2012 | Device:R  |
      | C1        | 22μF   | C_0805_2012 | Device:C  |
      | C2        | 1nF    | C_0603_1608 | Device:C  |
    When I run jbom command "inventory -o test_values.csv"
    Then the command should succeed
    And a file named "test_values.csv" should exist
    # Values are preserved exactly as authored in schematic
    And the file "test_values.csv" should contain "1.2k"
    And the file "test_values.csv" should contain "4.7K"
    And the file "test_values.csv" should contain "22μF"
    And the file "test_values.csv" should contain "1nF"

  Scenario: Components with unknown LibID get blank IPN and Unknown category
    Given a schematic that contains:
      | Reference | Value | Footprint   | LibID           |
      | R1        | 10k   | R_0603_1608 | Device:R        |
      | X1        | XTAL  | Crystal_SMD | Unknown:Mystery |
      | J1        | CONN  | Connector   |                 |
    When I run jbom command "inventory -o -"
    Then the command should succeed
    # R1 gets RES category; unknown-LibID components get Unknown category
    And the CSV output has rows where:
      | Value | Category |
      | 10k   | RES      |
    And the CSV output has rows where:
      | Value | Category |
      | XTAL  | Unknown  |
      | CONN  | Unknown  |

  Scenario: Inventory captures values with special characters
    Given a schematic that contains:
      | Reference | Value     | Footprint   | LibID    |
      | R1        | 10K Ω     | R_0603_1608 | Device:R |
      | C1        | 100 nF    | C_0603_1608 | Device:C |
      | L1        | 10µH      | L_0805_2012 | Device:L |
    When I run jbom command "inventory -o special.csv"
    Then the command should succeed
    And a file named "special.csv" should exist
    # Values with special characters are preserved exactly as authored
    And the file "special.csv" should contain "Ω"
    And the file "special.csv" should contain "100"
    And the file "special.csv" should contain "µH"

  Scenario: Duplicate components are deduplicated in inventory
    Given a schematic that contains:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10k   | R_0603_1608 | Device:R |
      | R2        | 10k   | R_0603_1608 | Device:R |
      | R3        | 22k   | R_0603_1608 | Device:R |
      | C1        | 100nF | C_0603_1608 | Device:C |
      | C2        | 100nF | C_0603_1608 | Device:C |
    When I run jbom command "inventory -o duplicates.csv"
    Then the command should succeed
    And a file named "duplicates.csv" should exist
    # Should deduplicate - only unique value/footprint combinations
    And the file "duplicates.csv" should contain "10k"
    And the file "duplicates.csv" should contain "22k"
    And the file "duplicates.csv" should contain "100nF"
    # Should show correct number of unique items
    And the output should contain "Generated inventory with 3 items"

  Scenario: Footprint-based IC detection correctly categorizes components
    Given a schematic that contains:
      | Reference | Value   | Footprint      | LibID         |
      | U1        | Unknown | SOIC-8         | Mystery:Part  |
      | U2        | LM358   | DIP-8          | Device:OpAmp  |
      | U3        | 74HC00  | TSSOP-14       | Logic:Gate    |
      | Q1        | 2N3904  | SOT-23         | Device:Q_NPN  |
    When I run jbom command "inventory -o footprint_test.csv"
    Then the command should succeed
    And a file named "footprint_test.csv" should exist
    # Category classification works via LibID/footprint heuristics
    And the file "footprint_test.csv" should contain "IC"
    And the file "footprint_test.csv" should contain "LM358"
    And the file "footprint_test.csv" should contain "74HC00"
    And the file "footprint_test.csv" should contain "2N3904"

  Scenario: IC part number patterns are correctly classified
    Given a schematic that contains:
      | Reference | Value    | Footprint   | LibID        |
      | U1        | LM7805   | TO-220      | Regulator:LM |
      | U2        | TL071    | DIP-8       | Device:OpAmp |
      | U3        | NE555    | DIP-8       | Timer:555    |
      | U4        | MAX232   | DIP-16      | Interface:RS |
      | U5        | CD4017   | DIP-16      | Logic:Counter|
      | U6        | SN74HC00 | SOIC-14     | Logic:Gate   |
    When I run jbom command "inventory -o ic_patterns.csv"
    Then the command should succeed
    And a file named "ic_patterns.csv" should exist
    And the file "ic_patterns.csv" should contain "IC"
    And the file "ic_patterns.csv" should contain "LM7805"
    And the file "ic_patterns.csv" should contain "TL071"

  Scenario: Mixed passives with IC-like prefixes are correctly classified
    Given a schematic that contains:
      | Reference | Value | Footprint   | LibID      |
      | L1        | 10µH  | L_0805      | Device:L   |
      | L2        | LM123 | SOIC-8      | Device:IC  |
      | C1        | 100nF | C_0603      | Device:C   |
      | C2        | CD456 | DIP-8       | Device:IC  |
      | R1        | 10k   | R_0603      | Device:R   |
    When I run jbom command "inventory -o mixed_test.csv"
    Then the command should succeed
    And a file named "mixed_test.csv" should exist
    # Passive LibIDs produce passive categories; IC LibID produces IC category
    And the file "mixed_test.csv" should contain "IND"
    And the file "mixed_test.csv" should contain "CAP"
    And the file "mixed_test.csv" should contain "RES"
    And the file "mixed_test.csv" should contain "IC"

  Scenario: Microcontroller and processor components are classified as IC
    Given a schematic that contains:
      | Reference | Value     | Footprint | LibID         |
      | U1        | ATMEGA328 | QFP-32    | MCU:AVR       |
      | U2        | STM32F4   | BGA-176   | MCU:ARM       |
      | U3        | PIC16F84  | DIP-18    | MCU:PIC       |
      | U4        | ESP32     | QFN-48    | MCU:ESP       |
    When I run jbom command "inventory -o mcu_test.csv"
    Then the command should succeed
    And a file named "mcu_test.csv" should exist
    And the file "mcu_test.csv" should contain "IC"
    And the file "mcu_test.csv" should contain "ATMEGA328"
    And the file "mcu_test.csv" should contain "STM32F4"

  Scenario: Edge cases and ambiguous components are handled gracefully
    Given a schematic that contains:
      | Reference | Value    | Footprint    | LibID           |
      | L1        | CHOKE    | L_Axial      | Device:L        |
      | LED1      | GREEN    | LED_0805     | Device:LED      |
      | D1        | 1N4148   | SOD-123      | Device:D        |
      | U1        |          | SOIC-8       | Unknown:Mystery |
      | Q1        | BC547    | TO-92        | Device:Q_NPN    |
    When I run jbom command "inventory -o edge_cases.csv"
    Then the command should succeed
    And a file named "edge_cases.csv" should exist
    And the file "edge_cases.csv" should contain "CHOKE"
    And the file "edge_cases.csv" should contain "GREEN"
    And the file "edge_cases.csv" should contain "1N4148"
    And the file "edge_cases.csv" should contain "BC547"
