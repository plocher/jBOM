Feature: Inventory Logic
  As a jBOM user
  I want intelligent inventory processing
  So that my inventory files are accurate and useful

  Scenario: Component type detection from lib_id
    Given a clean test environment
    And a KiCad project named "TypeDetection"
    And the schematic contains components:
      | Reference | Value | LibID        | Footprint         |
      | R1        | 10K   | Device:R     | R_0603_1608Metric |
      | C1        | 100nF | Device:C     | C_0603_1608Metric |
      | L1        | 10uH  | Device:L     | L_1206_3216Metric |
      | D1        | LED   | Device:LED   | LED_0603_1608Metric |
      | U1        | NE555 | Timer:NE555P | SOIC-8_3.9x4.9mm |
    When I run "jbom inventory -o stdout" in the project directory
    Then the command exits with code 0
    And stdout contains "RES,10K"
    And stdout contains "CAP,100nF"
    And stdout contains "IND,10uH"
    And stdout contains "LED,LED"
    And stdout contains "IC,NE555"

  Scenario: Package extraction from footprint names
    Given a clean test environment
    And a KiCad project named "PackageExtraction"
    And the schematic contains components:
      | Reference | Value | Footprint                           |
      | R1        | 1K    | R_0603_1608Metric                   |
      | R2        | 2K    | R_0805_2012Metric                   |
      | U1        | OP07  | SOIC-8_3.9x4.9mm_P1.27mm           |
      | U2        | MCU   | QFN-32-1EP_5x5mm_P0.5mm_EP3.45x3.45mm |
    When I run "jbom inventory -o stdout" in the project directory
    Then the command exits with code 0
    And stdout contains "0603"
    And stdout contains "0805"
    And stdout contains "SOIC-8"
    And stdout contains "QFN-32"

  Scenario: IPN generation with category and value
    Given a clean test environment
    And a KiCad project named "IPNGeneration"
    And the schematic contains components:
      | Reference | Value  | LibID    | Footprint         |
      | R1        | 4K7    | Device:R | R_0603_1608Metric |
      | C1        | 0.1uF  | Device:C | C_0603_1608Metric |
      | L1        | 22uH   | Device:L | L_1206_3216Metric |
      | D1        | 1N4148 | Device:D | SOD-323_P1.5mm    |
    When I run "jbom inventory -o stdout" in the project directory
    Then the command exits with code 0
    And stdout contains "RES_4K7"
    And stdout contains "CAP_0.1uF"
    And stdout contains "IND_22uH"
    And stdout contains "DIODE_1N4148"

  Scenario: Property mapping to inventory fields
    Given a clean test environment
    And a KiCad project named "PropertyMapping"
    And the schematic contains components:
      | Reference | Value | Tolerance | Voltage | Wattage | Type     | Amperage |
      | R1        | 10K   | 1%        | 100V    | 0.25W   |          |          |
      | C1        | 47uF  | 20%       | 25V     |         | Tantalum |          |
      | L1        | 100uH | 10%       |         |         | Ferrite  | 1A       |
    When I run "jbom inventory -o stdout" in the project directory
    Then the command exits with code 0
    And the CSV includes columns for discovered properties
    And stdout contains tolerance, voltage, and type information

  Scenario: E-series resistor value and tolerance handling
    Given a clean test environment
    And a KiCad project named "ESeriesTest"
    And the schematic contains components:
      | Reference | Value | Tolerance |
      | R1        | 10K   | 5%        |
      | R2        | 10K0  | 1%        |
      | R3        | 9K1   | 5%        |
      | R4        | 9K76  | 1%        |
    When I run "jbom inventory -o stdout" in the project directory
    Then the command exits with code 0
    And stdout contains "RES_10K" with 5% tolerance
    And stdout contains "RES_10K0" with 1% tolerance
    And stdout contains "RES_9K1" with 5% tolerance
    And stdout contains "RES_9K76" with 1% tolerance
    And the inventory contains exactly 4 unique items

  Scenario: Simple merge strategy for append mode
    Given a clean test environment
    And an existing inventory file "merge.csv" with:
      | IPN    | Category | Value | Package | Manufacturer |
      | RES_1K | RES      | 1K    | 0603    | Yageo        |
      | RES_2K | RES      | 2K    | 0603    |              |
    And a KiCad project named "MergeTest"
    And the schematic contains components:
      | Reference | Value | Manufacturer | MFGPN  |
      | R1        | 1K    | Vishay       | VIS123 |
      | R2        | 2K    | Murata       | MUR456 |
      | R3        | 4K7   | TDK          | TDK789 |
    When I run "jbom inventory -o merge.csv" in the project directory
    Then the command exits with code 0
    And the existing RES_1K entry is preserved (don't overwrite)
    And the RES_2K entry gets enhanced with Murata data
    And a new RES_4K7 entry is added
