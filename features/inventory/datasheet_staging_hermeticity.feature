Feature: Datasheet staging hermeticity guard
  As a jBOM maintainer
  I want the test suite to prove that a real $HOME profile can never leak
  into a jbom CLI subprocess run by the test harness
  So that a maintainer's own datasheet_staging.staging_dir binding on their
  development machine can never cause a test to touch real network
  endpoints or write into a real curated staging directory

  Scenario: a poisoned real HOME profile never leaks into a jbom subprocess
    Given a poisoned "real" HOME profile with a datasheet staging_dir binding
    And a supplier profile that contains:
      | key | value   |
      | id  | generic |
    And a supplier catalog that contains:
      | distributor_pn | manufacturer | mpn    | stock_quantity | price | datasheet                                   |
      | S40001         | Texas Inst   | LM358D | 500            | 0.20  | https://example.com/docs/poison-guard.pdf   |
    And the datasheet URL "https://example.com/docs/poison-guard.pdf" resolves to a PDF
    When I run jbom command "search LM358 --supplier generic"
    Then the command should succeed
    And the poisoned staging directory was never written to
