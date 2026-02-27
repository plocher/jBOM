Feature: POS Units and Origin
  As a hardware developer
  I want control over POS units and origin
  So that I can match assembly house requirements

  Background:
    Given the generic fabricator is selected

  Scenario: Use auxiliary origin
    Given a PCB that contains:
      | Reference | X | Y | Side | Footprint   |
      | R1        | 10| 5 | TOP  | R_0805_2012 |
      | C1        | 15| 8 | TOP  | C_0603_1608 |
    When I run jbom command "pos --origin aux"
    Then the command should succeed
    And the output should contain "R1"
    And the output should contain "C1"
