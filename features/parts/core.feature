Feature: Parts List Generation (Core Functionality)
  As a hardware developer
  I want to generate a Parts List from KiCad schematics
  So that I can see electro-mechanically grouped components for PCB assembly

  Background:
    Given a jBOM CSV sandbox
    And the generic fabricator is selected
    And a schematic that contains:
      | Reference | Value | Footprint         |
      | R1        | 10K   | R_0805_2012       |
      | R2        | 10K   | R_0805_2012       |
      | R10       | 10K   | R_0805_2012       |
      | C1        | 100nF | C_0603_1608       |
      | C20       | 100nF | C_0603_1608       |
      | U1        | LM358 | SOIC-8_3.9x4.9mm |

  Scenario: Generate basic parts list (CSV output)
    When I run jbom command "parts"
    Then the command should succeed
    And the output should contain these fields:
      | Refs | Value | Footprint | Package |
    And the CSV output has rows where:
      | Refs      | Value | Footprint   |
      | R1,R2,R10 | 10K   | R_0805_2012 |
      | C1,C20    | 100nF | C_0603_1608 |

  Scenario: Parts list aggregates electro-mechanically identical components
    When I run jbom command "parts"
    Then the command should succeed
    And the CSV output row count is 3
    And the CSV output has rows where:
      | Refs      | Value | Footprint   |
      | R1,R2,R10 | 10K   | R_0805_2012 |

  Scenario: Natural reference sorting within aggregated refs
    When I run jbom command "parts"
    Then the command should succeed
    And the output should contain "R1,R2,R10"
    And the output should contain "C1,C20"

  Scenario: Parts list does not aggregate when package differs
    Given a schematic that contains:
      | Reference | Value | Footprint   | Package |
      | R1        | 10K   | R_0805_2012 | 0603    |
      | R2        | 10K   | R_0805_2012 | 0805    |
    When I run jbom command "parts"
    Then the command should succeed
    And the CSV output row count is 2
    And the CSV output has rows where:
      | Refs | Value | Footprint   | Package |
      | R1   | 10K   | R_0805_2012 | 0603    |
      | R2   | 10K   | R_0805_2012 | 0805    |

  Scenario: Explicit namespace fields are available in parts output
    Given a PCB that contains:
      | Reference | X | Y | Footprint   |
      | R1        | 5 | 3 | R_0805_2012 |
      | R2        | 6 | 3 | R_0805_2012 |
      | R10       | 7 | 3 | R_0805_2012 |
      | C1        | 8 | 3 | C_0603_1608 |
      | C20       | 9 | 3 | C_0603_1608 |
      | U1        | 1 | 1 | SOIC-8_3.9x4.9mm |
    When I run jbom command "parts -f refs,s:footprint,p:footprint,c:footprint"
    Then the command should succeed
    And the output should contain these fields:
      | Refs | S:Footprint | P:Footprint | C:Footprint |
    And the CSV output has rows where:
      | Refs      | S:Footprint | P:Footprint | C:Footprint |
      | R1,R2,R10 | R_0805_2012 | R_0805_2012 | R_0805_2012 |

  Scenario: Parts list-fields includes merge namespace fields
    When I run jbom command "parts --list-fields"
    Then the command should succeed
    And the output should contain "Known parts fields"
    And the output should contain "s:value"
    And the output should contain "p:footprint"
    And the output should contain "c:value"
    And the output should contain "a:value"
