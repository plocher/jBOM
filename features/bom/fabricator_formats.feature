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
    When I run jbom command "bom SimpleProject -i test_inventory.csv --jlc -o jlc_bom.csv"
    Then the command succeeds
    And file "jlc_bom.csv" is created
    And the BOM includes columns
      | column      |
      | Reference   |
      | Quantity    |
      | DPN         |
      | Value       |
      | Footprint   |

  Scenario: Generate PCBWay format BOM
    Given the schematic contains standard components
    When I run jbom command "bom SimpleProject -i test_inventory.csv --pcbway -o pcbway_bom.csv"
    Then the command succeeds
    And file "pcbway_bom.csv" is created
    And the BOM includes columns
      | column       |
      | Reference    |
      | Quantity     |
      | MPN          |
      | Manufacturer |
      | Description  |

  Scenario: Generate Seeed Studio format BOM
    Given the schematic contains standard components
    When I run jbom command "bom SimpleProject -i test_inventory.csv --seeed -o seeed_bom.csv"
    Then the command succeeds
    And file "seeed_bom.csv" is created
    And the BOM includes columns
      | column      |
      | Reference   |
      | Quantity    |
      | DPN         |
      | Value       |
      | Package     |

  Scenario: Generate generic format BOM
    Given the schematic contains standard components
    When I run jbom command "bom SimpleProject -i test_inventory.csv --generic -o generic_bom.csv"
    Then the command succeeds
    And file "generic_bom.csv" is created
    And the BOM includes columns
      | column       |
      | Reference    |
      | Quantity     |
      | Description  |
      | Value        |
      | Footprint    |
      | Manufacturer |
      | MPN          |

  Scenario: Custom field selection overrides fabricator format
    Given the schematic contains standard components
    When I run jbom command "bom SimpleProject -i test_inventory.csv --jlc -f 'Reference,Value,MPN' -o custom_bom.csv"
    Then the command succeeds
    And file "custom_bom.csv" is created
    And the BOM contains exactly 3 columns: Reference, Value, MPN
