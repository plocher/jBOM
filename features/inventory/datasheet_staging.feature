Feature: Always-on datasheet staging fetch
  As a hardware developer
  I want jbom search / jbom inventory --supplier to stage Datasheet URLs
  So that candidate documents are collected for later human review without
  ever writing to the inventory or hitting real network endpoints in tests

  Background:
    Given a staging directory

  Scenario: jbom search stages a verified PDF datasheet
    Given a supplier profile that contains:
      | key | value   |
      | id  | generic |
    And a supplier catalog that contains:
      | distributor_pn | manufacturer | mpn    | stock_quantity | price | datasheet                                  |
      | S25804         | Texas Inst   | LM358D | 500            | 0.20  | https://example.com/docs/lm358-series.pdf  |
    And the datasheet URL "https://example.com/docs/lm358-series.pdf" resolves to a PDF
    When I run jbom command "search LM358 --supplier generic"
    Then the command should succeed
    And the staging directory contains a verified PDF for "https://example.com/docs/lm358-series.pdf"

  Scenario: jbom search flags an HTML impostor datasheet
    Given a supplier profile that contains:
      | key | value   |
      | id  | generic |
    And a supplier catalog that contains:
      | distributor_pn | manufacturer | mpn    | stock_quantity | price | datasheet                                   |
      | S25805         | Texas Inst   | LM358D | 500            | 0.20  | https://example.com/docs/lm358-missing.pdf  |
    And the datasheet URL "https://example.com/docs/lm358-missing.pdf" resolves to HTML
    When I run jbom command "search LM358 --supplier generic"
    Then the command should succeed
    And the staging directory contains a flagged unverified file for "https://example.com/docs/lm358-missing.pdf"
    And the output should contain "HTML impostor"

  Scenario: jbom inventory --supplier stages a verified PDF datasheet
    Given a supplier profile that contains:
      | key | value   |
      | id  | generic |
    And a supplier catalog that contains:
      | distributor_pn | manufacturer | mpn             | stock_quantity | price | datasheet                                    |
      | S25804         | Yageo        | RC0603FR-0710KL | 500            | 0.01  | https://example.com/docs/rc0603-series.pdf   |
    And the datasheet URL "https://example.com/docs/rc0603-series.pdf" resolves to a PDF
    And a schematic that contains:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10K   | R_0603_1608 | Device:R |
    When I run jbom command "inventory --supplier generic -o result.csv"
    Then the command should succeed
    And the staging directory contains a verified PDF for "https://example.com/docs/rc0603-series.pdf"

  Scenario: jbom inventory --supplier flags an HTML impostor datasheet
    Given a supplier profile that contains:
      | key | value   |
      | id  | generic |
    And a supplier catalog that contains:
      | distributor_pn | manufacturer | mpn             | stock_quantity | price | datasheet                                     |
      | S25806         | Yageo        | RC0603FR-0710KL | 500            | 0.01  | https://example.com/docs/rc0603-missing.pdf   |
    And the datasheet URL "https://example.com/docs/rc0603-missing.pdf" resolves to HTML
    And a schematic that contains:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10K   | R_0603_1608 | Device:R |
    When I run jbom command "inventory --supplier generic -o result.csv"
    Then the command should succeed
    And the staging directory contains a flagged unverified file for "https://example.com/docs/rc0603-missing.pdf"
