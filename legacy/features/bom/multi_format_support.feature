Feature: Multi-Format Inventory Support
  As a PCB designer
  I want to use inventory files in CSV, Excel, or Numbers formats
  So that I can work with inventory data regardless of the file format

  Scenario: Process inventory files in all supported formats
    Given a KiCad project named "MultiFormatTest"
    And the project uses a schematic named "TestBoard"
    And the "TestBoard" schematic contains components:
      | Reference | Value | Footprint   | LibID |
      | R1        | 10k   | R_0603_1608 | Device:R |
      | C1        | 100nF | C_0603_1608 | Device:C |
      | L1        | 10uH  | L_0603_1608 | Device:L |
    And I test with existing inventory files in all formats:
      | Format  | File |
      | CSV     | examples/example-INVENTORY.csv |
      | Excel   | examples/example-INVENTORY.xlsx |
      | Numbers | examples/example-INVENTORY.numbers |
    When I generate BOMs using each inventory format
    Then all supported formats produce equivalent BOM results
    And components are successfully matched across all formats

  Scenario: Combine multiple inventory formats in single workflow
    Given a KiCad project named "MixedFormatWorkflow"
    And the project uses a schematic named "ComplexBoard"
    And the "ComplexBoard" schematic contains components:
      | Reference | Value | Footprint   | LibID |
      | R1        | 10k   | R_0603_1608 | Device:R |
      | R2        | 1k    | R_0603_1608 | Device:R |
      | C1        | 100nF | C_0603_1608 | Device:C |
      | C2        | 10uF  | C_0805_2012 | Device:C |
      | U1        | MCU   | QFP64       | MCU:STM32 |
    And I use multiple existing inventory files:
      | Format  | File | Priority |
      | CSV     | examples/example-INVENTORY.csv | 1 |
      | Excel   | examples/example-INVENTORY.xlsx | 2 |
      | Numbers | examples/example-INVENTORY.numbers | 3 |
    When I generate a combined BOM for MixedFormatWorkflow using multiple inventory files
    Then the BOM combines data from all supported file formats
    And component matching uses priority-based selection across formats
    And the BOM shows inventory source format for each matched component
