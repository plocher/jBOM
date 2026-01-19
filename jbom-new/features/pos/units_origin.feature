Feature: POS Units and Origin
  As a hardware developer
  I want control over POS units and origin
  So that I can match assembly house requirements

  Background:
    Given a clean test workspace

  Scenario: Output in inches
    Given a KiCad PCB file "units_test.kicad_pcb" with components
    When I run "jbom pos units_test.kicad_pcb --units inch"
    Then the command exits with code 0
    And the output contains CSV headers "Reference,X(in),Y(in),Rotation"
    And the coordinate values are in inches

  Scenario: Use auxiliary origin
    Given a KiCad PCB file "origin_test.kicad_pcb" with auxiliary origin set
    When I run "jbom pos origin_test.kicad_pcb --origin aux"
    Then the command exits with code 0
    And the coordinates are relative to auxiliary origin
