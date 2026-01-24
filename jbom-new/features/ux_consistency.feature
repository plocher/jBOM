@skip
Feature: UX Consistency Across Commands
  As a hardware developer
  I want consistent behavior across BOM, POS, and inventory commands
  So that I have a predictable and intuitive user experience

  Background:
    Given the generic fabricator is selected
    And a schematic that contains:
      | Reference | Value | Footprint   | LibID     |
      | R1        | 10k   | R_0603_1608 | Device:R  |
      | C1        | 100nF | C_0603_1608 | Device:C  |
      | U1        | LM358 | SOIC-8      | Device:IC |
    And a PCB that contains:
      | Reference | X | Y | Side |
      | R1        | 5 | 3 | TOP  |
      | C1        | 8 | 6 | TOP  |
      | U1        |12 | 9 | TOP  |
    And an inventory file "test_inventory.csv" that contains:
      | IPN       | Category | Value | Description      | Package |
      | RES_10K   | RES      | 10k   | 10k resistor     | 0603    |
      | CAP_100nF | CAP      | 100nF | 100nF capacitor  | 0603    |
      | IC_LM358  | IC       | LM358 | Op-amp           | SOIC-8  |

  Scenario: All commands default to human-readable console output
    When I run jbom command "bom"
    Then the command should succeed
    And the output should contain "Bill of Materials"
    And the output should contain "R1"
    And the output should contain "10k"

    When I run jbom command "pos"
    Then the command should succeed
    And the output should contain "Component Placement Data"
    And the output should contain "R1"
    And the output should contain "5"

    When I run jbom command "inventory --inventory test_inventory.csv"
    Then the command should succeed
    And the output should contain "Generated inventory"
    And the IPN for component "R1" should be consistent

  Scenario: All commands support -o - for CSV stdout
    When I run jbom command "bom -o -"
    Then the command should succeed
    And the output should contain "Reference"
    And the output should contain "R1"
    And the output should contain "10k"

    When I run jbom command "pos -o -"
    Then the command should succeed
    And the output should contain "Designator"
    And the output should contain "R1,5,3"

    When I run jbom command "inventory --inventory test_inventory.csv -o -"
    Then the command should succeed
    And the output should contain "IPN"
    And the IPN for component "R1" should be consistent

  Scenario: All commands support -o console for explicit table output
    When I run jbom command "bom -o console"
    Then the command should succeed
    And the output should contain "Bill of Materials"
    And the output should contain "R1"
    And the output should contain "10k"

    When I run jbom command "pos -o console"
    Then the command should succeed
    And the output should contain "Component Placement Data"
    And the output should contain "R1"
    And the output should contain "5"

    When I run jbom command "inventory --inventory test_inventory.csv -o console"
    Then the command should succeed
    And the output should contain "Generated inventory"
    And the IPN for component "R1" should be consistent

  Scenario: All commands support -o filename.csv for file output
    When I run jbom command "bom -o test_bom.csv"
    Then the command should succeed
    And a file named "test_bom.csv" should exist
    And the file "test_bom.csv" should contain "R1"
    And the file "test_bom.csv" should contain "10k"

    When I run jbom command "pos -o test_pos.csv"
    Then the command should succeed
    And a file named "test_pos.csv" should exist
    And the file "test_pos.csv" should contain "R1,5,3"

    When I run jbom command "inventory --inventory test_inventory.csv -o test_inventory_output.csv"
    Then the command should succeed
    And a file named "test_inventory_output.csv" should exist
    And the file "test_inventory_output.csv" should contain "RES_10k"

  Scenario: All commands show consistent help patterns
    When I run jbom command "bom --help"
    Then the command should succeed
    And the output should contain "-o"
    And the output should contain "--output"

    When I run jbom command "pos --help"
    Then the command should succeed
    And the output should contain "-o"
    And the output should contain "--output"

    When I run jbom command "inventory --help"
    Then the command should succeed
    And the output should contain "-o"
    And the output should contain "--output"

  Scenario: All commands handle empty projects gracefully
    Given a schematic that contains:
      | Reference | Value | Footprint |
    And a PCB that contains:
      | Reference | X | Y | Side |
    And an inventory file "test_inventory.csv" that contains:
      | IPN       | Category | Value | Description      | Package |
    When I run jbom command "bom"
    Then the command should succeed
    And the output should contain "No components found"

    When I run jbom command "pos"
    Then the command should succeed
    And the output should contain "No components found"

    When I run jbom command "inventory"
    Then the command should fail
    And the output should contain "No components found"
