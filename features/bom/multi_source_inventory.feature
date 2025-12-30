Feature: Multi-Source Inventory
  As a PCB designer
  I want to use multiple inventory sources simultaneously
  So that I can prefer local stock while falling back to supplier catalogs

  Background:
    Given a KiCad project named "SimpleProject"

  Scenario: Prefer local inventory over supplier inventory
    Given a local inventory file with components
      | IPN   | Category | Value | Package | Distributor | DPN        | MPN            | Priority |
      | R001  | RES      | 10K   | 0603    | LOCAL       | R-10K-603  | RC0603FR-0710K | 1        |
      | C001  | CAP      | 100nF | 0603    | LOCAL       | C-100N-603 | CC0603KRX7R9BB | 1        |
    And a supplier inventory file with components
      | IPN   | Category | Value | Package | Distributor | DPN        | MPN            | Priority |
      | R002  | RES      | 10K   | 0603    | JLC         | C25804     | RC0603FR-0710K | 2        |
      | C002  | CAP      | 100nF | 0603    | JLC         | C14663     | CC0603KRX7R9BB | 2        |
    And the schematic contains standard components
    When I generate a BOM with both inventory sources
    Then the BOM uses local parts with priority 1 over supplier parts with priority 2

  Scenario: Load distributor export with local CSV
    Given a local inventory CSV file with components
      | IPN   | Category | Value | Package | Distributor | DPN        | Priority |
      | L001  | RES      | 10K   | 0603    | LOCAL       | LOCAL-10K  | 1        |
    And a JLC distributor export file with components
      | IPN   | Category | Value | Package | Distributor | DPN    | Priority |
      | J001  | RES      | 10K   | 0603    | JLC         | C25804 | 2        |
    And the schematic contains standard components
    When I generate a BOM with both inventory sources
    Then the BOM combines L001 and J001 based on priority ranking

  Scenario: Source tracking in verbose mode
    Given inventory source "local.csv" with components
      | IPN   | Category | Value | Package | Distributor | DPN        | Priority |
      | L001  | RES      | 10K   | 0603    | LOCAL       | LOCAL-10K  | 1        |
    And inventory source "supplier.csv" with components
      | IPN   | Category | Value | Package | Distributor | DPN    | Priority |
      | S001  | RES      | 10K   | 0603    | JLC         | C25804 | 2        |
    And the schematic contains a 10K 0603 resistor
    When I generate a verbose BOM with both inventory sources
    Then the BOM shows L001 selected from "local.csv" with S001 from "supplier.csv" as alternative

  Scenario: Multi-source inventory via API
    Given inventory source "primary.csv" with components
      | IPN   | Category | Value | Package | Priority |
      | P001  | RES      | 10K   | 0603    | 1        |
    And inventory source "backup.csv" with components
      | IPN   | Category | Value | Package | Priority |
      | B001  | RES      | 10K   | 0603    | 2        |
    And the schematic contains standard components
    When I use the API to generate BOM with both inventory sources
    Then the API returns BOM entries with source tracking showing selected inventory file for each matched item

  Scenario: Handle inventory source conflicts
    Given inventory source "first.csv" with components
      | IPN   | Category | Value | Package | Voltage |
      | CONF1 | CAP      | 10uF  | 0805    | 16V     |
    And inventory source "second.csv" with components
      | IPN   | Category | Value | Package | Voltage |
      | CONF1 | CAP      | 10uF  | 0805    | 25V     |
    And the schematic contains standard components
    When I generate a BOM with both inventory sources
    Then the BOM uses CONF1 definition from "first.csv" with 16V and warns about conflicting CONF1 in "second.csv" with 25V
