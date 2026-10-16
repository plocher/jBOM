Feature: BOM Datasheet URL group-fill from Datasheet Name family
  As a fabrication BOM consumer
  I want blank Datasheet URL cells filled from the family's canonical provenance row
  So that curated one-URL-per-Name inventory still yields complete datasheet links in output

  Background:
    Given the generic fabricator is selected

  Scenario: Family members with blank Datasheet inherit the canonical URL
    Given a PCB that contains:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10K   | R_0805_2012 | Device:R |
      | R2        | 22K   | R_0805_2012 | Device:R |
      | R3        | 33K   | R_0805_2012 | Device:R |
    And an inventory file "family_inventory.csv" that contains:
      | IPN     | Category | Value | Package | Manufacturer | MFGPN      | Datasheet                      | Datasheet Name            |
      | RES_10K | RESISTOR | 10K   | 0805    | Yageo        | RC0805-10K | https://example.com/rc0805.pdf | yageo_rc0805_resistor.pdf |
      | RES_22K | RESISTOR | 22K   | 0805    | Yageo        | RC0805-22K |                                | yageo_rc0805_resistor.pdf |
      | RES_33K | RESISTOR | 33K   | 0805    | Yageo        | RC0805-33K |                                | yageo_rc0805_resistor.pdf |
    When I run jbom command "bom --inventory family_inventory.csv -f Reference,Value,Datasheet -o -"
    Then the command should succeed
    And the CSV output has rows where:
      | Reference | Datasheet                      |
      | R1        | https://example.com/rc0805.pdf |
      | R2        | https://example.com/rc0805.pdf |
      | R3        | https://example.com/rc0805.pdf |
    # Inventory on disk is never rewritten by generation.
    And the file "family_inventory.csv" should contain "RES_22K,RESISTOR,22K,0805,Yageo,RC0805-22K,,yageo_rc0805_resistor.pdf"

  Scenario: Conflicting family URLs leave blank Datasheet cells blank
    Given a PCB that contains:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10K   | R_0805_2012 | Device:R |
      | R2        | 22K   | R_0805_2012 | Device:R |
    And an inventory file "conflict_inventory.csv" that contains:
      | IPN     | Category | Value | Package | Manufacturer | MFGPN      | Datasheet                   | Datasheet Name |
      | RES_10K | RESISTOR | 10K   | 0805    | Yageo        | RC0805-10K | https://example.com/a.pdf   | shared-family  |
      | RES_22K | RESISTOR | 22K   | 0805    | Yageo        | RC0805-22K | https://example.com/b.pdf   | shared-family  |
    When I run jbom command "bom --inventory conflict_inventory.csv -f Reference,Value,Datasheet -o -"
    Then the command should succeed
    # Each row keeps its own populated URL; generation does not invent a winner.
    And the CSV output has rows where:
      | Reference | Datasheet                 |
      | R1        | https://example.com/a.pdf |
      | R2        | https://example.com/b.pdf |

  Scenario: Family with no URL and no-Name rows emit blank Datasheet
    Given a PCB that contains:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10K   | R_0805_2012 | Device:R |
      | R2        | 22K   | R_0805_2012 | Device:R |
      | R3        | 33K   | R_0805_2012 | Device:R |
    And an inventory file "missing_inventory.csv" that contains:
      | IPN     | Category | Value | Package | Manufacturer | MFGPN      | Datasheet | Datasheet Name |
      | RES_10K | RESISTOR | 10K   | 0805    | Yageo        | RC0805-10K |           | empty-family   |
      | RES_22K | RESISTOR | 22K   | 0805    | Yageo        | RC0805-22K |           | empty-family   |
      | RES_33K | RESISTOR | 33K   | 0805    | Yageo        | RC0805-33K |           |                |
    When I run jbom command "bom --inventory missing_inventory.csv -f Reference,Value,Datasheet -o -"
    Then the command should succeed
    And the CSV output has rows where:
      | Reference | Datasheet |
      | R1        |           |
      | R2        |           |
      | R3        |           |
