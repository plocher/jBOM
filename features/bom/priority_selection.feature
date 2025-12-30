Feature: Priority Selection
  As a PCB designer
  I want jBOM to select the lowest priority part when multiple inventory items match
  So that I get preferred parts (local stock, cost-effective options) in my BOM

  Background:
    Given a KiCad project named "SimpleProject"
    And an inventory file with components
      | IPN    | Category | Value | Package | Distributor | DPN     | Priority |
      | R001   | RES      | 10K   | 0603    | JLC         | C25804  | 1        |
      | R001A  | RES      | 10K   | 0603    | JLC         | C25805  | 2        |
      | R001B  | RES      | 10K   | 0603    | JLC         | C25806  | 3        |
      | C001   | CAP      | 100nF | 0603    | JLC         | C14663  | 1        |

  Scenario: Select lowest priority when multiple parts match
    Given the schematic contains a 10K 0603 resistor
    When I generate a BOM
    Then the BOM contains the 10K 0603 resistor matched to inventory item with priority 1

  Scenario: Priority selection works with verbose output
    Given the schematic contains a 10K 0603 resistor
    When I generate a verbose BOM
    Then the verbose BOM shows the priority 1 part selected with priority 2 and 3 alternatives listed

  Scenario: Priority selection includes alternative matches
    Given the schematic contains a 10K 0603 resistor
    When I generate a BOM with alternatives
    Then the BOM includes the selected priority 1 match and lists alternative matches with priorities 2 and 3
