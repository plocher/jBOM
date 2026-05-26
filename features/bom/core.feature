Feature: BOM Generation (Core Functionality)
  As a hardware developer
  I want to generate a Bill of Materials from KiCad schematics
  So that I can order components and manufacture PCBs

  Background:
    Given the generic fabricator is selected
    And a PCB that contains:
      | Reference | Value | Footprint         |
      | R1        | 10K   | R_0805_2012       |
      | C1        | 100nF | C_0603_1608       |
      | U1        | LM358 | SOIC-8_3.9x4.9mm |

  Scenario: Generate basic BOM with console output (human-first)
    When I run jbom command "bom -o console"
    Then the command should succeed
    And the output should contain "R1"
    And the output should contain "10K"
    And the output should contain "C1"
    And the output should contain "100nF"
    And the output should contain "U1"
    And the output should contain "LM358"

  Scenario: Generate BOM with mixed-case fabricator ID
    When I run jbom command "bom --fabricator JLC -o console"
    Then the command should succeed
    And the output should contain "R1"

  Scenario: Generate BOM to specific output file
    When I run jbom command "bom -o custom_bom.csv"
    Then the command should succeed
    And a file named "custom_bom.csv" should exist

  Scenario: Generate BOM with explicit console table output
    When I run jbom command "bom -o console"
    Then the command should succeed
    And the output should contain "Bill of Materials"
    And the output should contain "R1"
    And the output should contain "C1"

  Scenario: Handle empty schematic
    Given a PCB that contains:
      | Reference | Value | Footprint |
    When I run jbom command "bom -o console"
    Then the command should succeed
    And the output should contain "No components found"

  # The next two scenarios drive divergent sch/pcb fixtures on purpose to
  # validate the user-facing debugging aid: BOM exposes both `sch:` and `pcb:`
  # namespaces so DRC issues are easy to see.  This is the only family of
  # BOM scenarios that legitimately needs a schematic alongside the PCB.

  Scenario: BOM list-fields reflects runtime source discovery and computed fields
    Given a schematic that contains:
      | Reference | Value | Footprint   | LCSC   |
      | R1        | 10K   | R_0805_2012 | C17414 |
    And a PCB that contains:
      | Reference | X | Y | Footprint   | Value |
      | R1        | 5 | 3 | R_0805_2012 | 9K99  |
    When I run jbom command "bom --list-fields"
    Then the command should succeed
    And the output should contain "Name"
    And the output should contain "sch:"
    And the output should contain "pcb:"
    And the output should contain "inv:"
    And the output should contain "sch:value"
    And the output should contain "pcb:value"
    And the output should contain "sch:lcsc"
    And the output should contain "quantity"
    And the output should not contain "ann:"

  Scenario: BOM unqualified fields use PIS source priority
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
    And a PCB that contains:
      | Reference | X | Y | Footprint   | Value |
      | R1        | 5 | 3 | R_0805_2012 | 9K99  |
    When I run jbom command "bom -f reference,quantity,value,fabricator_part_number,sch:value,pcb:value -o -"
    Then the command should succeed
    And the CSV output has rows where:
      | Reference | Value | SCH:Value | PCB:Value |
      | R1        | 9K99  | 10K       | 9K99      |

  Scenario: BOM preserves mixed-case designators from KiCad
    # KiCad allows mixed-case designators by design (e.g., License1, Prop1).
    # jBOM does not uppercase them at read time; they survive unchanged to output.
    # This contrasts with tools like Fabrication-Toolkit that normalize to uppercase.
    Given a PCB that contains:
      | Reference | Value     | Footprint     |
      | License1  | OSHW      | LICENSE_LOGO  |
      | Prop1     | Custom    | CUSTOM_SHAPE  |
      | R1        | 10K       | R_0805_2012   |
    When I run jbom command "bom -f reference,quantity,value -o -"
    Then the command should succeed
    And the output should contain "License1"
    And the output should contain "Prop1"
    And the output should not contain "LICENSE1"
    And the output should not contain "PROP1"
