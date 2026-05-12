Feature: Profile hierarchy and discovery
  Scenario: Built-in profile loads from package defaults
    Given a sandbox
    When I load profile "generic"
    Then resolved profile value "supplier.id" should equal "generic"

  Scenario: common layering merges mappings, replaces lists, and supports null deletes
    Given a sandbox
    And a common profile that contains:
      """
      defaults:
        search:
          output_fields:
            - manufacturer
            - mpn
      supplier:
        website: https://common.example
        description: inherited
        search:
          fields:
            - mpn
            - package
      """
    And a named profile that contains:
      """
      supplier:
        name: Acme Electronics
        description: null
        search:
          fields:
            - mpn
            - description
      """
    When I load the named profile
    Then resolved profile value "supplier.name" should equal "Acme Electronics"
    And resolved profile value "supplier.website" should equal "https://common.example"
    And resolved profile value "defaults.search.output_fields" should equal list "manufacturer,mpn"
    And resolved profile value "supplier.search.fields" should equal list "mpn,description"
    And resolved profile value "supplier.description" should be missing

  Scenario: first-match named profile wins while common profiles merge cumulatively
    Given a sandbox
    And profile directory "profiles_low" has a common profile containing:
      """
      defaults:
        field_precedence_policy:
          low_only:
            - manufacturer
      """
    And profile directory "profiles_high" has a common profile containing:
      """
      defaults:
        field_precedence_policy:
          high_only:
            - mpn
      """
    And profile directory "profiles_low" has a named profile containing:
      """
      supplier:
        name: Lower Priority Supplier
      """
    And profile directory "profiles_high" has a named profile containing:
      """
      supplier:
        name: Higher Priority Supplier
      """
    And JBOM_PROFILE_PATH contains "profiles_high,profiles_low"
    When I load the named profile
    Then resolved profile value "supplier.name" should equal "Higher Priority Supplier"
    And resolved profile value "defaults.field_precedence_policy.high_only" should equal list "mpn"
    And resolved profile value "defaults.field_precedence_policy.low_only" should equal list "manufacturer"
