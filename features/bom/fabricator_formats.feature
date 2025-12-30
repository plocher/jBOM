Feature: Fabricator Formats
  As a PCB designer
  I want to generate BOMs in different fabricator-specific formats
  So that I can submit to JLCPCB, PCBWay, Seeed Studio, or use generic formats

  Background:
    Given a KiCad project named "SimpleProject"
    And an inventory file with components
      | IPN   | Category | Value | Package | Distributor | DPN        | MPN            | Manufacturer | Description      | Footprint    | Priority |
      | R001  | RES      | 10K   | 0603    | JLC         | C25804     | RC0603FR-0710K | YAGEO        | 10K 0603 Resistor| R_0603_1608  | 1        |
      | R002  | RES      | 10K   | 0603    | PCBWay      | PWR-10K603 | RC0603FR-0710K | YAGEO        | 10K 0603 Resistor| R_0603_1608  | 1        |
      | R003  | RES      | 10K   | 0603    | Seeed       | SRR-10K603 | RC0603FR-0710K | YAGEO        | 10K 0603 Resistor| R_0603_1608  | 1        |
      | C001  | CAP      | 100nF | 0603    | JLC         | C14663     | CC0603KRX7R9BB | YAGEO        | 100nF 0603 Cap  | C_0603_1608  | 1        |
      | C002  | CAP      | 100nF | 0603    | PCBWay      | PWC-100N603| CC0603KRX7R9BB | YAGEO        | 100nF 0603 Cap  | C_0603_1608  | 1        |
      | C003  | CAP      | 100nF | 0603    | Seeed       | SRC-100N603| CC0603KRX7R9BB | YAGEO        | 100nF 0603 Cap  | C_0603_1608  | 1        |

  Scenario: Generate JLCPCB format BOM
    Given the schematic contains standard components
    And I want to generate a JLCPCB format BOM
    Then the BOM generates in the requested format with columns "Reference,Quantity,DPN,Value,Footprint"

  Scenario: Generate PCBWay format BOM
    Given the schematic contains standard components
    And I want to generate a PCBWay format BOM
    Then the BOM generates in the requested format with columns "Reference,Quantity,MPN,Manufacturer,Description"

  Scenario: Generate Seeed Studio format BOM
    Given the schematic contains standard components
    And I want to generate a Seeed format BOM
    Then the BOM generates in the requested format with columns "Reference,Quantity,DPN,Value,Package"

  Scenario: Generate generic format BOM
    Given the schematic contains standard components
    And I want to generate a generic format BOM
    Then the BOM generates in the requested format with columns "Reference,Quantity,Description,Value,Footprint,Manufacturer,MPN"

  Scenario: Custom field selection overrides fabricator format
    Given the schematic contains standard components
    And I want custom BOM fields "Reference,Value,MPN"
    Then the BOM generates with the specified custom fields

  Scenario: Minimal custom fields for assembly
    Given the schematic contains standard components
    And I want custom BOM fields "Reference,MPN,Manufacturer"
    Then the BOM generates with the specified custom fields

  Scenario: Detailed custom fields for procurement
    Given the schematic contains standard components
    And I want custom BOM fields "Reference,Quantity,Value,Package,MPN,Manufacturer,DPN,Distributor"
    Then the BOM generates with the specified custom fields
