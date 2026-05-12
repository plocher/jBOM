Feature: Unified profile hierarchy and discovery
  Scenario: Built-in unified profile loads from package defaults
    Given a sandbox
    When I load unified profile "generic"
    Then merged profile path "supplier.id" should equal "generic"

  Scenario: common layering merges mappings, replaces lists, and supports null deletes
    Given a sandbox
    And sandbox unified profile "common" contains:
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
    And sandbox unified profile "acme" contains:
      """
      id: acme
      supplier:
        id: acme
        name: Acme Electronics
        description: null
        search:
          fields:
            - mpn
            - description
      """
    When I load unified profile "acme"
    Then merged profile path "supplier.name" should equal "Acme Electronics"
    And merged profile path "supplier.website" should equal "https://common.example"
    And merged profile path "defaults.search.output_fields" should equal list "manufacturer,mpn"
    And merged profile path "supplier.search.fields" should equal list "mpn,description"
    And merged profile path "supplier.description" should be missing

  Scenario: first-match named profile wins while common profiles merge cumulatively
    Given a sandbox
    And profile directory "profiles_low" has unified profile "common" containing:
      """
      defaults:
        field_precedence_policy:
          low_only:
            - manufacturer
      """
    And profile directory "profiles_high" has unified profile "common" containing:
      """
      defaults:
        field_precedence_policy:
          high_only:
            - mpn
      """
    And profile directory "profiles_low" has unified profile "alt" containing:
      """
      supplier:
        id: alt
        name: Lower Priority Supplier
      """
    And profile directory "profiles_high" has unified profile "alt" containing:
      """
      supplier:
        id: alt
        name: Higher Priority Supplier
      """
    And JBOM_PROFILE_PATH contains "profiles_high,profiles_low"
    When I load unified profile "alt"
    Then merged profile path "supplier.name" should equal "Higher Priority Supplier"
    And merged profile path "defaults.field_precedence_policy.high_only" should equal list "mpn"
    And merged profile path "defaults.field_precedence_policy.low_only" should equal list "manufacturer"
