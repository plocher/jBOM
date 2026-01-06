Feature: Component Matching
  As a PCB designer
  I want jBOM to match schematic components against inventory items
  So that I can generate accurate BOMs with available parts

  Scenario: Match resistor by exact value and package
    Given a KiCad project named "ComponentTest"
    And the project uses a schematic named "ComponentTest"
    And the "ComponentTest" schematic contains components:
      | Reference | Value | Footprint   | LibID |
      | R1        | 10K   | R_0603_1608 | Device:R |
    And an inventory file "test-inventory.csv" containing components:
      | IPN   | Category | Value | Package | Distributor | DPN     | Priority |
      | R001  | RES      | 10K   | 0603    | Generic     | G25804  | 1        |
      | R002  | RES      | 1K1   | 0603    | Generic     | G11702  | 1        |
    When I generate a generic BOM for ComponentTest using test-inventory.csv
    Then the BOM contains component R1 matched with inventory part R001
    And the matched component has value "10K" and package "0603" from inventory

  Scenario: Match capacitor by exact value and package
    Given a KiCad project named "CapacitorTest"
    And the project uses a schematic named "CapacitorTest"
    And the "CapacitorTest" schematic contains components:
      | Reference | Value | Footprint   | LibID |
      | C1        | 100nF | C_0603_1608 | Device:C |
    And an inventory file "capacitor-inventory.csv" containing components:
      | IPN   | Category | Value | Package | Distributor | DPN     | Priority |
      | C001  | CAP      | 100nF | 0603    | Generic     | G14663  | 1        |
      | C002  | CAP      | 10uF  | 0805    | Generic     | G15850  | 1        |
    When I generate a generic BOM for CapacitorTest using capacitor-inventory.csv
    Then the BOM contains component C1 matched with inventory part C001
    And the matched component has value "100nF" and package "0603" from inventory

  Scenario: Match component by approximate value within tolerance range
    Given a KiCad project named "ToleranceTest"
    And the project uses a schematic named "ToleranceTest"
    And the "ToleranceTest" schematic contains components:
      | Reference | Value | Footprint   | LibID |
      | R2        | 1K    | R_0603_1608 | Device:R |
    And an inventory file "tolerance-inventory.csv" containing components:
      | IPN   | Category | Value | Package | Distributor | DPN     | Priority | Tolerance |
      | R001  | RES      | 10K   | 0603    | Generic     | G25804  | 1        | 5%        |
      | R002  | RES      | 1K1   | 0603    | Generic     | G11702  | 1        | 5%        |
    When I generate a generic BOM for ToleranceTest using tolerance-inventory.csv
    Then the BOM contains component R2 matched with inventory part R002
    And the matched component uses tolerance-based matching for value "1K" to inventory value "1K1"

  Scenario: Match component by normalized value format
    Given a KiCad project named "NormalizationTest"
    And the project uses a schematic named "NormalizationTest"
    And the "NormalizationTest" schematic contains components:
      | Reference | Value | Footprint   | LibID |
      | R3        | 1.1K  | R_0603_1608 | Device:R |
    And an inventory file "normalized-inventory.csv" containing components:
      | IPN   | Category | Value | Package | Distributor | DPN     | Priority |
      | R001  | RES      | 10K   | 0603    | Generic     | G25804  | 1        |
      | R002  | RES      | 1K1   | 0603    | Generic     | G11702  | 1        |
    When I generate a generic BOM for NormalizationTest using normalized-inventory.csv
    Then the BOM contains component R3 matched with inventory part R002
    And the matched component uses value normalization for "1.1K" to inventory value "1K1"

  Scenario: No match for missing component - no fields match
    Given a KiCad project named "UnmatchedTest"
    And the project uses a schematic named "UnmatchedTest"
    And the "UnmatchedTest" schematic contains components:
      | Reference | Value | Footprint   | LibID |
      | R4        | 47K   | R_1206_3216 | Device:R |
    And an inventory file "limited-inventory.csv" containing components:
      | IPN   | Category | Value | Package | Distributor | DPN     | Priority |
      | R001  | RES      | 10K   | 0603    | Generic     | G25804  | 1        |
      | C001  | CAP      | 100nF | 0603    | Generic     | G14663  | 1        |
    When I generate a generic BOM for UnmatchedTest using limited-inventory.csv
    Then the BOM file contains unmatched component R4 with no inventory data

  Scenario: No match for missing component - value matches, package doesn't
    Given a KiCad project named "PackageMismatchTest"
    And the project uses a schematic named "PackageMismatchTest"
    And the "PackageMismatchTest" schematic contains components:
      | Reference | Value | Footprint   | LibID |
      | R5        | 10K   | R_1206_3216 | Device:R |
    And an inventory file "package-mismatch-inventory.csv" containing components:
      | IPN   | Category | Value | Package | Distributor | DPN     | Priority |
      | R001  | RES      | 10K   | 0603    | Generic     | G25804  | 1        |
      | R002  | RES      | 1K1   | 1206    | Generic     | G11702  | 1        |
    When I generate a generic BOM for PackageMismatchTest using package-mismatch-inventory.csv
    Then the BOM file contains unmatched component R5 with no inventory data

  Scenario: No match for missing component - package matches, value doesn't
    Given a KiCad project named "ValueMismatchTest"
    And the project uses a schematic named "ValueMismatchTest"
    And the "ValueMismatchTest" schematic contains components:
      | Reference | Value | Footprint   | LibID |
      | R6        | 100K  | R_0603_1608 | Device:R |
    And an inventory file "value-mismatch-inventory.csv" containing components:
      | IPN   | Category | Value | Package | Distributor | DPN     | Priority |
      | R001  | RES      | 10K   | 0603    | Generic     | G25804  | 1        |
      | C001  | CAP      | 100K  | 0603    | Generic     | G14663  | 1        |
    When I generate a generic BOM for ValueMismatchTest using value-mismatch-inventory.csv
    Then the BOM file contains unmatched component R6 with no inventory data

  Scenario: Generate BOM from actual KiCad project with Excel inventory
    Given a KiCad project file "TestBoard.kicad_sch"
    And an Excel inventory file "parts_database.xlsx"
    When I generate a BOM with --generic fabricator
    Then the BOM contains components extracted from the KiCad schematic
    And components are matched against parts loaded from Excel file

  @wip
  Scenario: Process hierarchical KiCad schematic with CSV inventory
    Given a KiCad project with main sheet "MainBoard.kicad_sch"
    And sub-sheet "PowerSupply.kicad_sch"
    And a CSV inventory file "inventory.csv"
    When I generate a BOM with --generic fabricator
    Then the BOM includes components from both main sheet and sub-sheet
    And component quantities are merged correctly across sheets

  Scenario: Handle mixed file formats in workflow
    Given a KiCad project file "Controller.kicad_sch"
    And multiple inventory sources:
      | File                | Format  |
      | resistors.xlsx      | Excel   |
      | capacitors.csv      | CSV     |
      | ics.numbers         | Numbers |
    When I generate a BOM with --generic fabricator and all inventory sources
    Then the BOM combines parts data from all file formats
    And components are matched across all inventory sources

  Scenario: Process hierarchical project with components across multiple schematics
    Given a KiCad project named "HierarchicalBoard"
    And the project uses a schematic named "MainBoard"
    And the project uses a schematic named "PowerSupply"
    And the project uses a schematic named "AnalogSection"
    And the "MainBoard" schematic contains components:
      | Reference | Value | Footprint   | LibID |
      | U1        | MCU   | QFP64       | MCU:STM32 |
      | R1        | 10k   | R_0603_1608 | Device:R |
    And the "PowerSupply" schematic contains components:
      | Reference | Value | Footprint   | LibID |
      | U2        | VREG  | SOT23       | Regulator:LM317 |
      | R2        | 240   | R_0603_1608 | Device:R |
    And the "AnalogSection" schematic contains components:
      | Reference | Value | Footprint   | LibID |
      | U3        | OPAMP | SOIC8       | Amplifier:LM358 |
      | R3        | 1k    | R_0603_1608 | Device:R |
    And an inventory file "hierarchical-inventory.csv" containing components:
      | IPN   | Category | Value | Package | Distributor | DPN     | Priority |
      | R10K  | RES      | 10k   | 0603    | Generic     | G25804  | 1        |
      | R240  | RES      | 240   | 0603    | Generic     | G11702  | 1        |
      | R1K   | RES      | 1k    | 0603    | Generic     | G33891  | 1        |
    When I generate a generic BOM for HierarchicalBoard using hierarchical-inventory.csv
    Then the BOM file contains components from all schematic files
    And the BOM file contains component R1 from schematic "MainBoard" matched with inventory part R10K
    And the BOM file contains component R2 from schematic "PowerSupply" matched with inventory part R240
    And the BOM file contains component R3 from schematic "AnalogSection" matched with inventory part R1K
    And component quantities are correctly aggregated across all schematics
