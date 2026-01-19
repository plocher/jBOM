Feature: Inventory Generation
  As a hardware developer
  I want to generate inventory from project components
  So that I can track and manage component requirements

  Scenario: Generate inventory from schematic components
    Given a KiCad schematic file "project.kicad_sch" with components:
      | Reference | Value | Footprint     | Library        |
      | R1        | 10K   | R_0805_2012   | Device:R       |
      | C1        | 100nF | C_0603_1608   | Device:C       |
      | U1        | LM358 | SOIC-8_3.9x4.9mm | Amplifier_Operational:LM358 |
    When I run "jbom inventory generate project.kicad_sch -o project_inventory.csv"
    Then the command exits with code 0
    And a file named "project_inventory.csv" exists
    And the file "project_inventory.csv" contains CSV headers "IPN,Category,Value,Package,Description"
    And the file "project_inventory.csv" contains "RES_10K,RESISTOR,10K"
    And the file "project_inventory.csv" contains "CAP_100nF,CAPACITOR,100nF"
    And the file "project_inventory.csv" contains "IC_LM358,INTEGRATED_CIRCUIT,LM358"

  Scenario: Generate inventory with grouped components
    Given a KiCad schematic file "grouped.kicad_sch" with components:
      | Reference | Value | Footprint   | Library  |
      | R1        | 10K   | R_0805_2012 | Device:R |
      | R2        | 10K   | R_0805_2012 | Device:R |
      | R3        | 22K   | R_0805_2012 | Device:R |
    When I run "jbom inventory generate grouped.kicad_sch -o grouped_inventory.csv"
    Then the command exits with code 0
    And the file "grouped_inventory.csv" contains exactly 2 data rows
    And the file "grouped_inventory.csv" contains "RES_10K"
    And the file "grouped_inventory.csv" contains "RES_22K"

  Scenario: Handle missing schematic file
    When I run "jbom inventory generate missing.kicad_sch -o output.csv"
    Then the command exits with code 1
    And the error output contains "Schematic file not found"

  Scenario: Generate inventory with verbose output
    Given a KiCad schematic file "verbose.kicad_sch" with basic components
    When I run "jbom inventory generate verbose.kicad_sch -o verbose_inventory.csv -v"
    Then the command exits with code 0
    And the output contains verbose information about component processing
    And the output contains "Generated inventory with"

  Scenario: Help command
    When I run "jbom inventory generate --help"
    Then the command exits with code 0
    And the output contains "Generate inventory from project components"
    And the output contains "-o OUTPUT"
    And the output contains "--verbose"
