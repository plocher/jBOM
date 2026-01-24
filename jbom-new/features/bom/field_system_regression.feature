Feature: BOM Field System and Output Customization
  As a hardware developer
  I want to customize BOM output fields and use fabricator-specific formats
  So that I can generate BOMs that match different fabricator requirements

  Background:
    Given a schematic that contains:
      | Reference | Value | Footprint   | LCSC    | Manufacturer | MPN      | Package |
      | R1        | 10K   | R_0805_2012 | C17414  | Yageo        | RC0805   | 0805    |
      | C1        | 100nF | C_0603_1608 | C14663  | Murata       | GRM188   | 0603    |

  @regression @current-broken
  Scenario: Different fabricators produce different output headers
    When I run jbom command "bom --fabricator generic -o -"
    Then the command should succeed
    And the output should contain CSV headers "Reference,Quantity,Description,Value,Package,Footprint,Manufacturer,Part Number"
    When I run jbom command "bom --fabricator jlc -o -"
    Then the command should succeed
    And the output should contain CSV headers "Designator,Quantity,Value,Comment,Footprint,LCSC,Surface Mount"
    When I run jbom command "bom --fabricator pcbway -o -"
    Then the command should succeed
    And the output should not contain CSV headers "Reference,Quantity,Description,Value,Package,Footprint,Manufacturer,Part Number"
    When I run jbom command "bom --fabricator seeed -o -"
    Then the command should succeed
    And the output should not contain CSV headers "Reference,Quantity,Description,Value,Package,Footprint,Manufacturer,Part Number"

  @regression @current-broken
  Scenario: Field customization with -f argument
    When I run jbom command "bom -f Reference,Value,LCSC -o -"
    Then the command should succeed
    And the output should contain CSV headers "Reference,Value,LCSC"
    And the output should not contain "Quantity"
    And the output should not contain "Footprint"

  @regression @current-broken
  Scenario: Preset expansion with + syntax
    When I run jbom command "bom -f +minimal -o -"
    Then the command should succeed
    And the output should contain CSV headers "Reference,Quantity,Value,LCSC"
    When I run jbom command "bom -f +standard -o -"
    Then the command should succeed
    And the output should contain "Manufacturer"
    And the output should contain "Datasheet"

  @regression @current-broken
  Scenario: Fabricator-specific presets
    When I run jbom command "bom --fabricator jlc -f +jlc -o -"
    Then the command should succeed
    And the output should contain CSV headers "Designator,Quantity,Value,Comment,LCSC"
    When I run jbom command "bom --fabricator generic -f +generic -o -"
    Then the command should succeed
    And the output should contain CSV headers "Reference,Quantity,Description,Value,Manufacturer,Part Number"

  @regression @current-broken
  Scenario: Mixed syntax - preset plus custom fields
    When I run jbom command "bom -f +minimal,Manufacturer,I:Voltage -o -"
    Then the command should succeed
    And the output should contain "Reference"
    And the output should contain "Value"
    And the output should contain "LCSC"
    And the output should contain "Manufacturer"
    And the output should contain "I:Voltage"

  @regression @current-broken
  Scenario: Inventory field prefixing
    Given an inventory file with fields "Voltage,Tolerance,Package"
    When I run jbom command "bom --inventory inventory.csv -f Reference,Value,I:Voltage,I:Tolerance -o -"
    Then the command should succeed
    And the output should contain CSV headers "Reference,Value,I:Voltage,I:Tolerance"

  @regression @current-broken
  Scenario: Field validation - unknown field should fail
    When I run jbom command "bom -f Reference,Value,UnknownField -o -"
    Then the command should fail
    And the error output contains:
      | Unknown field: 'UnknownField' |

  @regression @current-broken
  Scenario: Preset validation - unknown preset should fail
    When I run jbom command "bom -f +unknown_preset -o -"
    Then the command should fail
    And the error output contains:
      | Unknown preset: +unknown_preset |

  @regression @current-broken
  Scenario: List available fields functionality
    When I run jbom command "bom --list-fields"
    Then the command should succeed
    And the output should contain "Available fields:"
    And the output should contain "reference"
    And the output should contain "value"
    And the output should contain "lcsc"

  @regression @current-broken
  Scenario: Console table respects field selection
    When I run jbom command "bom -f Reference,Value,LCSC"
    Then the command should succeed
    And the console table headers should be "Reference Value LCSC"
    And the console table should not contain "Footprint"

  @regression @current-broken
  Scenario: Default preset behavior
    When I run jbom command "bom -o -"
    Then the command should succeed
    # Should use fabricator-specific default or generic default
    And the output should contain "Reference"
    When I run jbom command "bom --fabricator jlc -o -"
    Then the command should succeed
    # Should use JLC default format
    And the output should contain "Designator"
    And the output should contain "LCSC"

  @regression @current-broken
  Scenario: CLI argument validation - missing field list
    When I run jbom command "bom -f"
    Then the command should fail
    And the error output contains:
      | argument -f/--fields: expected one argument |
