Feature: IPN Generation from Schematic Components
  As a hardware engineer
  I want jBOM to generate IPNs for components when no inventory exists
  So that I can bootstrap an inventory system from my schematic

  Background:
    Given the generic fabricator is selected

  Scenario: Generate IPNs from schematic components (no existing inventory)
    Given a schematic that contains:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10k   | R_0603_1608 | Device:R |
      | C1        | 100nF | C_0603_1608 | Device:C |
      | LED1      | RED   | LED_0603    | Device:LED |
      | U1        | LM358 | SOIC-8_3.9x4.9mm | Device:IC |
    When I run jbom command "inventory -o console"
    Then the command should succeed
    And the output should contain "Generated inventory with 4 items"
    # These should be generated IPNs based on component data
    And the output should contain "RES_10k"
    And the output should contain "CAP_100nF"
    And the output should contain "LED_RED"
    And the output should contain "IC_LM358"

  Scenario: Generated IPNs follow consistent format
    Given a schematic that contains:
      | Reference | Value  | Footprint   | LibID     |
      | R1        | 1.2k   | R_0603_1608 | Device:R  |
      | R2        | 4.7K   | R_0805_2012 | Device:R  |
      | C1        | 22μF   | C_0805_2012 | Device:C  |
      | C2        | 1nF    | C_0603_1608 | Device:C  |
    When I run jbom command "inventory -o test_ipns.csv"
    Then the command should succeed
    And a file named "test_ipns.csv" should exist
    # Generated IPNs should preserve original values exactly
    And the file "test_ipns.csv" should contain "RES_1.2k"
    And the file "test_ipns.csv" should contain "RES_4.7K"
    And the file "test_ipns.csv" should contain "CAP_22μF"
    And the file "test_ipns.csv" should contain "CAP_1nF"

  Scenario: Components with unknown LibID get blank IPNs
    Given a schematic that contains:
      | Reference | Value | Footprint   | LibID           |
      | R1        | 10k   | R_0603_1608 | Device:R        |
      | X1        | XTAL  | Crystal_SMD | Unknown:Mystery |
      | J1        | CONN  | Connector   |                 |
    When I run jbom command "inventory -o -"
    Then the command should succeed
    And the CSV output has rows where:
      | IPN    | Value | Category |
      | RES_10k| 10k   | RES      |
    And the CSV output has rows where:
      | Value | Category |
      | XTAL  | Unknown  |
      | CONN  | Unknown  |

  Scenario: IPN generation handles special characters properly
    Given a schematic that contains:
      | Reference | Value     | Footprint   | LibID    |
      | R1        | 10K Ω     | R_0603_1608 | Device:R |
      | C1        | 100 nF    | C_0603_1608 | Device:C |
      | L1        | 10µH      | L_0805_2012 | Device:L |
    When I run jbom command "inventory -o special.csv"
    Then the command should succeed
    And a file named "special.csv" should exist
    # Spaces should be replaced with underscores, special chars preserved
    And the file "special.csv" should contain "RES_10K_Ω"
    And the file "special.csv" should contain "CAP_100_nF"
    And the file "special.csv" should contain "IND_10µH"

  Scenario: Generate inventory for project with duplicate components
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
    And the file "duplicates.csv" should contain "RES_10k"
    And the file "duplicates.csv" should contain "RES_22k"
    And the file "duplicates.csv" should contain "CAP_100nF"
    # Should show correct quantities or component groupings
    And the output should contain "Generated inventory with 3 items"

  Scenario: Footprint-based IC detection works correctly
    Given a schematic that contains:
      | Reference | Value   | Footprint      | LibID         |
      | U1        | Unknown | SOIC-8         | Mystery:Part  |
      | U2        | LM358   | DIP-8          | Device:OpAmp  |
      | U3        | 74HC00  | TSSOP-14       | Logic:Gate    |
      | Q1        | 2N3904  | SOT-23         | Device:Q_NPN  |
    When I run jbom command "inventory -o footprint_test.csv"
    Then the command should succeed
    And a file named "footprint_test.csv" should exist
    # All IC footprints should be detected as ICs
    And the file "footprint_test.csv" should contain "IC_Unknown"
    And the file "footprint_test.csv" should contain "IC_LM358"
    And the file "footprint_test.csv" should contain "IC_74HC00"
    # Transistor in SOT-23 should remain transistor
    And the file "footprint_test.csv" should contain "Q_2N3904"

  Scenario: IC part number patterns are recognized
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
    # All should be recognized as ICs based on part number patterns
    And the file "ic_patterns.csv" should contain "IC_LM7805"
    And the file "ic_patterns.csv" should contain "IC_TL071"
    And the file "ic_patterns.csv" should contain "IC_NE555"
    And the file "ic_patterns.csv" should contain "IC_MAX232"
    And the file "ic_patterns.csv" should contain "IC_CD4017"
    And the file "ic_patterns.csv" should contain "IC_SN74HC00"

  Scenario: Mixed passive components with IC-like prefixes are handled correctly
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
    # Real inductor should stay inductor
    And the file "mixed_test.csv" should contain "IND_10µH"
    # IC with L prefix should be IC due to footprint/part number
    And the file "mixed_test.csv" should contain "IC_LM123"
    # Real capacitor should stay capacitor
    And the file "mixed_test.csv" should contain "CAP_100nF"
    # IC with C prefix should be IC due to footprint/part number
    And the file "mixed_test.csv" should contain "IC_CD456"
    # Resistor should stay resistor
    And the file "mixed_test.csv" should contain "RES_10k"

  Scenario: Microcontroller and processor detection
    Given a schematic that contains:
      | Reference | Value     | Footprint | LibID         |
      | U1        | ATMEGA328 | QFP-32    | MCU:AVR       |
      | U2        | STM32F4   | BGA-176   | MCU:ARM       |
      | U3        | PIC16F84  | DIP-18    | MCU:PIC       |
      | U4        | ESP32     | QFN-48    | MCU:ESP       |
    When I run jbom command "inventory -o mcu_test.csv"
    Then the command should succeed
    And a file named "mcu_test.csv" should exist
    # All microcontrollers should be detected as ICs
    And the file "mcu_test.csv" should contain "IC_ATMEGA328"
    And the file "mcu_test.csv" should contain "IC_STM32F4"
    And the file "mcu_test.csv" should contain "IC_PIC16F84"
    And the file "mcu_test.csv" should contain "IC_ESP32"

  Scenario: Edge cases and ambiguous components
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
    # Inductor with text value should work
    And the file "edge_cases.csv" should contain "IND_CHOKE"
    # LED should be correctly categorized
    And the file "edge_cases.csv" should contain "LED_GREEN"
    # Diode should work
    And the file "edge_cases.csv" should contain "DIO_1N4148"
    # Unknown component with IC footprint should be IC, but blank value creates just category
    And the file "edge_cases.csv" should contain "IC"
    # Transistor should work
    And the file "edge_cases.csv" should contain "Q_BC547"
