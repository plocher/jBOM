Feature: Inventory Generation from KiCad Projects
  As a hardware engineer
  I want to generate component inventories from KiCad projects with intelligent IPN creation
  So that I can bootstrap an inventory system from my design

  Background:
    Given the generic fabricator is selected
    And a schematic that contains:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10K   | R_0603_1608 | Device:R |
      | R2        | 22K   | R_0805_2012 | Device:R |
      | C1        | 100nF | C_0603_1608 | Device:C |
      | LED1      | RED   | LED_0603    | Device:LED |
      | U1        | LM358 | SOIC-8      | Device:IC |

  Scenario: Generate basic inventory with IPN creation
    When I run jbom command "inventory -o -"
    Then the command should succeed
    And the CSV output has rows where
      | IPN       | Category | Value |
      | RES_10K   | RES      | 10K   |
      | RES_22K   | RES      | 22K   |
      | CAP_100nF | CAP      | 100nF |
      | LED_RED   | LED      | RED   |
      | IC_LM358  | IC       | LM358 |

  Scenario: IPN format follows consistent pattern
    When I run jbom command "inventory -o -"
    Then the command should succeed
    And the CSV output has rows where
      | IPN       | Description     |
      | RES_10K   | RES 10K 0603    |
      | CAP_100nF | CAP 100nF 0603  |
      | LED_RED   | LED RED 0603    |
      | IC_LM358  | IC LM358 soic   |

  Scenario: Package information normalized from footprint
    When I run jbom command "inventory -o -"
    Then the command should succeed
    And the CSV output has rows where
      | IPN       | Package |
      | RES_10K   | 0603    |
      | RES_22K   | 0805    |
      | CAP_100nF | 0603    |
      | LED_RED   | 0603    |
      | IC_LM358  | soic    |

  Scenario: Component deduplication works correctly
    Given a schematic that contains:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10K   | R_0603_1608 | Device:R |
      | R2        | 10K   | R_0603_1608 | Device:R |
      | C1        | 100nF | C_0603_1608 | Device:C |
      | C2        | 100nF | C_0603_1608 | Device:C |
    When I run jbom command "inventory -o -"
    Then the command should succeed
    And the CSV output has rows where
      | IPN       | Category | Value |
      | RES_10K   | RES      | 10K   |
      | CAP_100nF | CAP      | 100nF |

  Scenario: Unknown components get blank IPNs
    Given a schematic that contains:
      | Reference | Value | Footprint   | LibID           |
      | R1        | 10K   | R_0603_1608 | Device:R        |
      | X1        | XTAL  | Crystal_SMD | Unknown:Mystery |
      | J1        | CONN  | Connector   |                 |
    When I run jbom command "inventory -o -"
    Then the command should succeed
    And the CSV output has rows where
      | IPN     | Category | Value |
      | RES_10K | RES      | 10K   |
    # Unknown components should have some representation but no IPN magic
