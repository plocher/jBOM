Feature: Test-only fetch-fixtures profile keys are gated out of production
  As a jBOM user
  I want fetch_fixtures_manifest profile keys to never silently replace
  network fetches in normal invocations
  So that a mistaken production profile cannot swap real datasheet content
  for local fixture payloads without a loud failure or explicit test allow

  Scenario: check_urls fixtures in a user profile fail loudly without allow env
    Given a user profile sets check_urls fetch_fixtures_manifest without the allow env
    And an inventory file "inventory.csv" that contains:
      | RowType | IPN  | Category | Value | Package | Datasheet                                       |
      | ITEM    | R001 | RES      | 10K   | 0603    | https://wmsc.lcsc.com/wmsc/upload/file/r001.pdf |
    When I run "jbom audit inventory.csv --check-urls"
    Then the command should fail
    And the output should contain "JBOM_ALLOW_FETCH_FIXTURES"
    And the output should contain "test-only"

  Scenario: sanctioned check_urls fixture path still works with allow env
    Given a check-urls fixture manifest
    And the check-urls URL "https://wmsc.lcsc.com/wmsc/upload/file/r001.pdf" resolves to a PDF
    And an inventory file "inventory.csv" that contains:
      | RowType | IPN  | Category | Value | Package | Datasheet                                       |
      | ITEM    | R001 | RES      | 10K   | 0603    | https://wmsc.lcsc.com/wmsc/upload/file/r001.pdf |
    When I run "jbom audit inventory.csv --check-urls"
    Then the command should succeed
    And the output should contain "test-only fetch fixtures are ACTIVE"
    And the output should contain "1 URL(s) checked, 0 upgrade(s) proposed"

  Scenario: datasheet_staging fixtures in a user profile fail loudly without allow env
    Given a staging directory
    And a user profile sets datasheet_staging fetch_fixtures_manifest without the allow env
    And a supplier profile that contains:
      | key | value   |
      | id  | generic |
    And a supplier catalog that contains:
      | distributor_pn | manufacturer | mpn    | stock_quantity | price | datasheet                                 |
      | S50001         | Texas Inst   | LM358D | 500            | 0.20  | https://example.com/docs/gate-refuse.pdf  |
    When I run jbom command "search LM358 --supplier generic"
    Then the command should fail
    And the output should contain "JBOM_ALLOW_FETCH_FIXTURES"
    And the output should contain "test-only"

  Scenario: sanctioned datasheet_staging fixture path still works with allow env
    Given a staging directory
    And a supplier profile that contains:
      | key | value   |
      | id  | generic |
    And a supplier catalog that contains:
      | distributor_pn | manufacturer | mpn    | stock_quantity | price | datasheet                                  |
      | S50002         | Texas Inst   | LM358D | 500            | 0.20  | https://example.com/docs/gate-allow.pdf    |
    And the datasheet URL "https://example.com/docs/gate-allow.pdf" resolves to a PDF
    When I run jbom command "search LM358 --supplier generic"
    Then the command should succeed
    And the output should contain "test-only fetch fixtures are ACTIVE"
    And the staging directory contains a verified PDF for "https://example.com/docs/gate-allow.pdf"
