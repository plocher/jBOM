Feature: Priority Selection
  As a PCB designer
  I want jBOM to select the lowest priority part when multiple inventory items match
  So that I get preferred parts (local stock, cost-effective options) in my BOM

  Background:
    Given a KiCad project named "SimpleProject"

  Scenario: Select lowest priority when multiple parts match including edge cases
    Given the "BasicComponents" schematic
    And the "PriorityTest" inventory
    When I generate a BOM
    Then the BOM selects the part with the lowest priority value among all matching candidates for each component

  Scenario: Priority zero wins over all other priorities
    Given the "BasicComponents" schematic
    And the "PriorityTest" inventory
    When I generate a BOM
    Then the BOM selects parts with priority 0 when available as the highest priority option

  Scenario: Priority selection works with verbose output
    Given the "BasicComponents" schematic
    And the "PriorityTest" inventory
    When I generate a verbose BOM
    Then the verbose BOM shows the lowest priority part selected with higher priority alternatives listed

  Scenario: Priority selection includes alternative matches
    Given the "BasicComponents" schematic
    And the "PriorityTest" inventory
    When I generate a BOM with alternatives
    Then the BOM includes the selected lowest priority match and lists alternative matches ordered by priority
