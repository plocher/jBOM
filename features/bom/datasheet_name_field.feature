Feature: Datasheet Name BOM field selection
  As a hardware developer
  I want to select the inventory's Datasheet Name column via --fields
  So that downstream tooling (e.g. kproj) can deep-link into the shared
  datasheet library using the exact curated Document name

  Background:
    Given the generic fabricator is selected
    And a PCB that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
      | R2        | 22K   | R_0805_2012 |
    And an inventory file "inventory.csv" that contains:
      | IPN     | Category | Value | Package | Manufacturer | MFGPN      | Datasheet                      | Datasheet Name            |
      | RES_10K | RESISTOR | 10K   | 0805    | Yageo        | RC0805-10K | https://example.com/rc0805.pdf | yageo_rc0805_resistor.pdf |
      | RES_22K | RESISTOR | 22K   | 0805    | Yageo        | RC0805-22K | https://example.com/rc0805.pdf |                            |

  Scenario: DatasheetName is selectable and populated for a curated Item
    # CamelCase form avoids spaces in the CLI token; the field system
    # normalizes it to 'datasheet_name' and renders the "Datasheet Name" header.
    When I run jbom command "bom --inventory inventory.csv -f Reference,Value,DatasheetName -o -"
    Then the command should succeed
    And the output should contain CSV headers "Reference,Value,Datasheet Name"
    And the CSV output has rows where:
      | Reference | Datasheet Name             |
      | R1        | yageo_rc0805_resistor.pdf  |

  Scenario: DatasheetName is empty for an uncurated Item
    When I run jbom command "bom --inventory inventory.csv -f Reference,Value,DatasheetName -o -"
    Then the command should succeed
    And the CSV output has rows where:
      | Reference | Datasheet Name |
      | R2        |                |

  Scenario: datasheet_name appears in --list-fields output when present in inventory
    When I run jbom command "bom --inventory inventory.csv --list-fields"
    Then the command should succeed
    And the output should contain "datasheet_name"
