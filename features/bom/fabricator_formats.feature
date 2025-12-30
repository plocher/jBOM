Feature: Fabricator Formats
  As a PCB designer
  I want to generate BOMs in different fabricator-specific formats
  So that I can submit to JLCPCB, PCBWay, Seeed Studio, or use generic formats

  Background:
    Given a KiCad project named "SimpleProject"
    And an inventory file with components
      | IPN   | Category | Value | Package | Distributor | DPN     | MPN            | Manufacturer | Priority |
      | R001  | RES      | 10K   | 0603    | JLC         | C25804  | RC0603FR-0710K | YAGEO        | 1        |
      | C001  | CAP      | 100nF | 0603    | JLC         | C14663  | CC0603KRX7R9BB | YAGEO        | 1        |

  Scenario: Generate JLCPCB format BOM
    Given the schematic contains standard components
    Then the BOM generates in JLCPCB format with columns "Reference,Quantity,DPN,Value,Footprint"

  Scenario: Generate PCBWay format BOM
    Given the schematic contains standard components
    Then the BOM generates in PCBWay format with columns "Reference,Quantity,MPN,Manufacturer,Description"

  Scenario: Generate Seeed Studio format BOM
    Given the schematic contains standard components
    Then the BOM generates in Seeed format with columns "Reference,Quantity,DPN,Value,Package"

  Scenario: Generate generic format BOM
    Given the schematic contains standard components
    Then the BOM generates in generic format with columns "Reference,Quantity,Description,Value,Footprint,Manufacturer,MPN"

  Scenario: Custom field selection overrides fabricator format
    Given the schematic contains standard components
    Then the BOM generates with custom fields "Reference,Value,MPN"
