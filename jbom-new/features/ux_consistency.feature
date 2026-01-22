Feature: UX Consistency Across Commands
  As a hardware developer
  I want consistent behavior across BOM, POS, and inventory commands
  So that I have a predictable and intuitive user experience

  Background:
    Given the generic fabricator is selected
    And a complete project with components and PCB layout:
      | Reference | Value | Footprint   | LibID     | X | Y | Side |
      | R1        | 10k   | R_0603_1608 | Device:R  | 5 | 3 | TOP  |
      | C1        | 100nF | C_0603_1608 | Device:C  | 8 | 6 | TOP  |
      | U1        | LM358 | SOIC-8      | Device:IC |12 | 9 | TOP  |

  Scenario: All commands default to human-readable console output
    When I run jbom command "bom"
    Then the command should succeed
    And the output should contain a formatted table
    And the output should not be CSV format

    When I run jbom command "pos"
    Then the command should succeed
    And the output should contain "Component Placement Data"
    And the output should not be CSV format

    When I run jbom command "inventory"
    Then the command should succeed
    And the output should contain "Generated inventory"
    And the output should not be CSV format

  Scenario: All commands support -o - for CSV stdout
    When I run jbom command "bom -o -"
    Then the command should succeed
    And the output should be in CSV format
    And the output should contain "Reference,Quantity,Value"

    When I run jbom command "pos -o -"
    Then the command should succeed
    And the output should be in CSV format
    And the output should contain "Reference,X(mm),Y(mm)"

    When I run jbom command "inventory -o -"
    Then the command should succeed
    And the output should be in CSV format
    And the output should contain "IPN,Category,Value"

  Scenario: All commands support -o console for explicit table output
    When I run jbom command "bom -o console"
    Then the command should succeed
    And the output should contain a formatted table
    And the output should contain "Bill of Materials"

    When I run jbom command "pos -o console"
    Then the command should succeed
    And the output should contain a formatted table
    And the output should contain "Component Placement Data"

    When I run jbom command "inventory -o console"
    Then the command should succeed
    And the output should contain a formatted table
    And the output should contain "Generated inventory"

  Scenario: All commands support -o filename.csv for file output
    When I run jbom command "bom -o test_bom.csv"
    Then the command should succeed
    And a file named "test_bom.csv" should exist
    And the file "test_bom.csv" should be in CSV format

    When I run jbom command "pos -o test_pos.csv"
    Then the command should succeed
    And a file named "test_pos.csv" should exist
    And the file "test_pos.csv" should be in CSV format

    When I run jbom command "inventory -o test_inventory.csv"
    Then the command should succeed
    And a file named "test_inventory.csv" should exist
    And the file "test_inventory.csv" should be in CSV format

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
