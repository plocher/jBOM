Feature: Audit inventory supplier freshness
  As a hardware developer
  I want jbom audit to detect when supplier PNs are stale or
  when better alternatives exist
  So that I can keep my inventory current and optimal

  Scenario: STALE_PART emitted when existing PN not found by fresh search
    Given a generic supplier
    And an inventory file "inventory.csv" that contains:
      | RowType | IPN          | Category | Value | Package | Supplier | SPN    |
      | ITEM    | RES_10K_0603 | RES      | 10K   | 0603    | generic  | S99999 |
    When I run "jbom audit inventory.csv --supplier generic"
    Then the command should succeed
    And the output should contain "STALE_PART"
    And the output should contain "S99999"

  Scenario: BETTER_AVAILABLE when search finds a different best PN
    Given a generic supplier
    And a supplier catalog that contains:
      | distributor_pn | manufacturer | mpn             | stock_quantity | price |
      | S25804         | Yageo        | RC0603FR-0710KL | 500            | 0.01  |
    And an inventory file "inventory.csv" that contains:
      | RowType | IPN          | Category | Value | Package | Supplier | SPN    |
      | ITEM    | RES_10K_0603 | RES      | 10K   | 0603    | generic  | S99001 |
    When I run "jbom audit inventory.csv --supplier generic"
    Then the command should succeed
    And the output should contain "BETTER_AVAILABLE"
    And the output should contain "S99001"
    And the output should contain "S25804"

  Scenario: Silent when existing PN matches best search result
    Given a generic supplier
    And a supplier catalog that contains:
      | distributor_pn | manufacturer | mpn             | stock_quantity | price |
      | S25804         | Yageo        | RC0603FR-0710KL | 500            | 0.01  |
    And an inventory file "inventory.csv" that contains:
      | RowType | IPN          | Category | Value | Package | Supplier | SPN    |
      | ITEM    | RES_10K_0603 | RES      | 10K   | 0603    | generic  | S25804 |
    When I run "jbom audit inventory.csv --supplier generic"
    Then the command should succeed
    And the output should not contain "STALE_PART"
    And the output should not contain "BETTER_AVAILABLE"

  Scenario: No STALE_PART when item has no supplier PN
    Given a generic supplier
    And an inventory file "inventory.csv" that contains:
      | RowType | IPN          | Category | Value | Package | Supplier | SPN |
      | ITEM    | RES_10K_0603 | RES      | 10K   | 0603    |          |     |
    When I run "jbom audit inventory.csv --supplier generic"
    Then the command should succeed
    And the output should not contain "STALE_PART"

  Scenario: Freshness checks run even without --requirements
    Given a generic supplier
    And an inventory file "inventory.csv" that contains:
      | RowType | IPN          | Category | Value | Package | Supplier | SPN    |
      | ITEM    | RES_10K_0603 | RES      | 10K   | 0603    | generic  | S99999 |
    When I run "jbom audit inventory.csv --supplier generic -o report.csv"
    Then the command should succeed
    And a file named "report.csv" should exist
    And the file "report.csv" should contain "STALE_PART"
