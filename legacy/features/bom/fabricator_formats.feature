Feature: Fabricator Formats
  As a PCB designer
  I want to generate BOMs in different fabricator-specific formats
  So that I can submit to JLCPCB, PCBWay, Seeed Studio, or use generic formats

  Background:
    Given a KiCad project named "SimpleProject"
    And an inventory file with components
      | IPN   | Category | Value | Package | Distributor | DPN        | MPN            | Manufacturer | Description      | Footprint    | Priority |
      | R001  | RES      | 10K   | 0603    | Generic     | G25804     | RC0603FR-0710K | YAGEO        | 10K 0603 Resistor| R_0603_1608  | 1        |
      | C001  | CAP      | 100nF | 0603    | Generic     | G14663     | CC0603KRX7R9BB | YAGEO        | 100nF 0603 Cap  | C_0603_1608  | 1        |

  Scenario: Generate BOM with default format
    Given the schematic contains standard components
    When I generate a BOM with --generic fabricator
    Then the BOM contains required columns for component assembly
    And the BOM includes component identifiers and quantities

  Scenario: Test fabricator-specific column formats
    Given the schematic contains standard components
    When I generate a BOM with --jlcpcb fabricator
    Then the BOM format matches the JLCPCB fabricator configuration
    When I generate a BOM with --pcbway fabricator
    Then the BOM format matches the PCBWay fabricator configuration
    When I generate a BOM with --seeed fabricator
    Then the BOM format matches the Seeed fabricator configuration

  Scenario: Custom field selection overrides default format
    Given the schematic contains standard components
    When I generate a BOM with --generic fabricator and custom fields "Reference,Value,MPN"
    Then the BOM contains only the specified custom fields
    And the BOM ignores the default fabricator field configuration

  Scenario: Generate BOM with minimal fields for assembly
    Given the schematic contains standard components
    When I generate a BOM with --generic fabricator and custom fields "Reference,MPN,Manufacturer"
    Then the BOM contains only essential assembly information

  Scenario: Generate BOM with detailed fields for procurement
    Given the schematic contains standard components
    When I generate a BOM with --generic fabricator and custom fields "Reference,Quantity,Value,Package,MPN,Manufacturer,DPN,Distributor"
    Then the BOM contains comprehensive procurement information
