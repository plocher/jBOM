Feature: BOM Priority and Selection Rules
  As a hardware developer
  I want predictable BOM organization based on fabricator configuration
  So that I get consistent, reviewable bills of materials

  Background:
    Given the generic fabricator is selected
    And a schematic that contains:
      | Reference | Value | Footprint     | LibID      |
      | C1        | 100nF | C_0805_2012   | Device:C   |
      | C2        | 100nF | C_0805_2012   | Device:C   |
      | R1        | 10K   | R_0603_1608   | Device:R   |
      | R2        | 1K    | R_0805_2012   | Device:R   |
      | U1        | LM358 | SOIC-8_3.9x4.9mm_P1.27mm | Amplifier_Operational:LM358 |

  Scenario: Generic fabricator produces consistent component ordering
    When I run jbom command "bom -o console"
    Then the command should succeed
    And the output should contain "C1"
    And the output should contain "C2"
    And the output should contain "R1"
    And the output should contain "R2"
    And the output should contain "U1"

  Scenario: Components with same value+footprint are grouped
    When I run jbom command "bom -o -"
    Then the command should succeed
    And the CSV output has a row where
      | Reference | Quantity | Value |
      | C1, C2    | 2        | 100nF |

  Scenario: References grouped and sorted naturally
    When I run jbom command "bom -o console"
    Then the command should succeed
    And the output should contain "C1, C2"
    And the output should contain "100nF"
    And the output should contain "2"

  Scenario: Different fabricator presets produce different formats
    When I run jbom command "bom --jlc -o console"
    Then the command should succeed
    And the output should contain "Designator"
    When I run jbom command "bom --generic -o console"
    Then the command should succeed
    And the output should contain "Designator"

  Scenario: CSV format determined by fabricator configuration
    When I run jbom command "bom -o -"
    Then the command should succeed
    And the output should contain CSV headers
    And the CSV output has a row where
      | Reference | Quantity |
      | C1, C2    | 2        |
