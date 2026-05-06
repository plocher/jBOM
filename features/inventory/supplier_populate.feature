Feature: Inventory supplier PN auto-populate
  As a hardware developer
  I want jbom inventory to populate supplier PNs automatically
  So that I get a complete inventory without manual web browsing

  Scenario: --supplier flag is accepted and succeeds
    Given a generic supplier
    And a schematic that contains:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10K   | R_0603_1608 | Device:R |
    When I run jbom command "inventory --supplier generic -o result.csv"
    Then the command should succeed
    And a file named "result.csv" should exist

  Scenario: Supplier PN populated when catalog has a matching result
    Given a generic supplier
    And a supplier catalog that contains:
      | distributor_pn | manufacturer | mpn             | stock_quantity | price |
      | S25804         | Yageo        | RC0603FR-0710KL | 500            | 0.01  |
    And a schematic that contains:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10K   | R_0603_1608 | Device:R |
    When I run jbom command "inventory --supplier generic -o result.csv"
    Then the command should succeed
    And the file "result.csv" should contain "Supplier"
    And the file "result.csv" should contain "S25804"

  Scenario: Existing supplier PN is preserved, not overwritten
    Given a generic supplier
    And a supplier catalog that contains:
      | distributor_pn | manufacturer | mpn             | stock_quantity | price |
      | S25804         | Yageo        | RC0603FR-0710KL | 500            | 0.01  |
    And a schematic that contains:
      | Reference | Value | Footprint   | LibID    | Supplier | SPN    |
      | R1        | 10K   | R_0603_1608 | Device:R | generic  | S99001 |
    When I run jbom command "inventory --supplier generic -o result.csv"
    Then the command should succeed
    And the file "result.csv" should contain "S99001"

  Scenario: Supplier column present but empty when catalog has no results
    Given a generic supplier
    And a schematic that contains:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10K   | R_0603_1608 | Device:R |
    When I run jbom command "inventory --supplier generic -o result.csv"
    Then the command should succeed
    And the file "result.csv" should contain "Supplier"

  Scenario: Repeatable suppliers add supplier-specific rows in one run
    Given a supplier profile "generic" with catalog that contains:
      | distributor_pn | manufacturer | mpn             | stock_quantity | price |
      | G25804         | Yageo        | RC0603FR-0710KL | 500            | 0.01  |
    And a supplier profile "mouser" with catalog that contains:
      | distributor_pn | manufacturer | mpn             | stock_quantity | price |
      | M25804         | Yageo        | RC0603FR-0710KL | 500            | 0.01  |
    And a schematic that contains:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10K   | R_0603_1608 | Device:R |
    When I run jbom command "inventory --supplier generic --supplier mouser -o result.csv"
    Then the command should succeed
    And the file "result.csv" contains exactly 3 data rows
    And the file "result.csv" should contain "Supplier"
    And the file "result.csv" should contain "Mouser"
    And the file "result.csv" should contain "G25804"
    And the file "result.csv" should contain "M25804"

  Scenario: --limit applies independently to each supplier pass
    Given a supplier profile "generic" with catalog that contains:
      | distributor_pn | manufacturer | mpn             | stock_quantity | price |
      | G10001         | Yageo        | RC0603FR-0710KL | 500            | 0.01  |
      | G10002         | Yageo        | RC0603FR-0710KL | 400            | 0.02  |
    And a supplier profile "mouser" with catalog that contains:
      | distributor_pn | manufacturer | mpn             | stock_quantity | price |
      | M20001         | Yageo        | RC0603FR-0710KL | 500            | 0.01  |
      | M20002         | Yageo        | RC0603FR-0710KL | 400            | 0.02  |
    And a schematic that contains:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10K   | R_0603_1608 | Device:R |
    When I run jbom command "inventory --supplier generic --supplier mouser --limit 1 -o result.csv"
    Then the command should succeed
    And the file "result.csv" contains exactly 3 data rows
    And the file "result.csv" should contain "G10001"
    And the file "result.csv" should contain "M20001"
