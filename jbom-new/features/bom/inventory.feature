Feature: BOM Inventory Enhancement
  As a hardware developer
  I want to enhance my BOM with inventory information
  So that I can see part numbers, descriptions, and availability

  Background:
    Given the generic fabricator is selected

  Scenario: Enhance BOM with inventory data
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | C1        | 100nF | C_0603_1608 |
    And an inventory file "components.csv" that contains:
      | IPN     | Category  | Value | Package | Manufacturer | MFGPN           | LCSC   |
      | RES_10K | RESISTOR  | 10K   | 0805    | Yageo        | RC0805FR-0710KL | C17414 |
      | CAP_100N| CAPACITOR | 100nF | 0603    | Samsung      | CL10B104KB8NNNC | C1591  |
    When I run jbom command "bom --inventory components.csv"
    Then the command should succeed
    And the output should contain "Inventory enhanced"

  Scenario: Handle missing inventory file
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
    When I run jbom command "bom --inventory missing.csv"
    Then the command should fail
    And the error output should mention "Inventory file not found"

  Scenario: BOM with partial inventory matches
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | R2        | 22K   | R_0805_2012 |
    And an inventory file "partial.csv" that contains:
      | IPN     | Category | Value | Description | Package | Manufacturer | MFGPN     |
      | RES_10K | RESISTOR | 10K   | 10K Ohm     | 0805    | Yageo        | RC0805-10K |
    When I run jbom command "bom --inventory partial.csv -o console"
    Then the command should succeed
    And the output should contain "Inventory enhanced: 1/2 items matched"

  # TODO: This scenario doesn't test meaningful functionality - it sets up
  # components and inventory but doesn't validate the actual enhancement.
  # Should verify that R1 gets enhanced with RES_10K data using table-driven
  # validation instead of magic hardcoded column expectations.
  Scenario: Enhanced BOM to file output
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
    And an inventory file "inventory.csv" that contains:
      | IPN     | Category | Value | Description | Package        | Manufacturer | MFGPN     | LCSC   |
      | RES_10K | RESISTOR | 10K   | Res 10K     | R_0805_2012    | Yageo        | RC0805-10K | C25804 |
    When I run jbom command "bom --inventory inventory.csv -o enhanced_bom.csv"
    Then the command should succeed
    And a file named "enhanced_bom.csv" should exist
