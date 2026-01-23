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

    When I run jbom command "inventory"
    Then the command should succeed
    And the output should contain "Generated inventory"
    And the output should contain "RES_10K"

  Scenario: All commands support -o - for CSV stdout
    When I run jbom command "bom -o -"
    Then the command should succeed
    And the output should contain "Reference,Quantity,Value"
    And the output should contain "R1,1,10k"

    When I run jbom command "pos -o -"
    Then the command should succeed
    And the output should contain "Reference,X(mm),Y(mm)"
    And the output should contain "R1,5,3"

    When I run jbom command "inventory -o -"
    Then the command should succeed
    And the output should contain "IPN,Category,Value"
    And the output should contain "RES_10K,RESISTOR,10k"

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

    When I run jbom command "inventory -o console"
    Then the command should succeed
    And the output should contain "Generated inventory"
    And the output should contain "RES_10K"

  Scenario: All commands support -o filename.csv for file output
    When I run jbom command "bom -o test_bom.csv"
    Then the command should succeed
    And a file named "test_bom.csv" should exist
    And the file "test_bom.csv" should contain "R1,1,10k"

    When I run jbom command "pos -o test_pos.csv"
    Then the command should succeed
    And a file named "test_pos.csv" should exist
    And the file "test_pos.csv" should contain "R1,5,3"

    When I run jbom command "inventory -o test_inventory.csv"
    Then the command should succeed
    And a file named "test_inventory.csv" should exist
    And the file "test_inventory.csv" should contain "RES_10K,RESISTOR,10k"

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
    Given a project with no components
    When I run jbom command "bom"
    Then the command should fail
    And the output should contain "No components found"

    When I run jbom command "pos"
    Then the command should succeed
    And the output should contain "No components found"

    When I run jbom command "inventory"
    Then the command should fail
    And the output should contain "No components found"
