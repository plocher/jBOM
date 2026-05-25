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
  Scenario: Same named profile in multiple locations resolves from cwd first
    Given a sandbox
    And the profile repo root is "repo"
    And the profile load cwd is "repo/work"
    And a cwd named profile that contains:
      """
      supplier:
        name: CWD Named Supplier
      """
    And a repo named profile that contains:
      """
      supplier:
        name: Repo Named Supplier
      """
    And profile directory "env_profiles" has a named profile containing:
      """
      supplier:
        name: Env Named Supplier
      """
    And JBOM_PROFILE_PATH contains "env_profiles"
    And a home named profile that contains:
      """
      supplier:
        name: Home Named Supplier
      """
    When I load the named profile
    Then resolved profile value "supplier.name" should equal "CWD Named Supplier"

  Scenario: Same named profile falls back to repo root when cwd is missing
    Given a sandbox
    And the profile repo root is "repo"
    And the profile load cwd is "repo/work"
    And a repo named profile that contains:
      """
      supplier:
        name: Repo Named Supplier
      """
    And profile directory "env_profiles" has a named profile containing:
      """
      supplier:
        name: Env Named Supplier
      """
    And JBOM_PROFILE_PATH contains "env_profiles"
    And a home named profile that contains:
      """
      supplier:
        name: Home Named Supplier
      """
    When I load the named profile
    Then resolved profile value "supplier.name" should equal "Repo Named Supplier"

  Scenario: common profiles layer across locations while named comes from lower-priority tier
    Given a sandbox
    And the profile repo root is "repo"
    And the profile load cwd is "repo/work"
    And a repo common profile that contains:
      """
      defaults:
        search:
          output_fields:
            - repo_only
      supplier:
        website: https://repo.example
      """
    And a cwd common profile that contains:
      """
      defaults:
        search:
          output_fields:
            - cwd_only
      supplier:
        website: https://cwd.example
      """
    And a home common profile that contains:
      """
      supplier:
        description: from_home_common
      """
    And profile directory "env_profiles" has a named profile containing:
      """
      supplier:
        name: Env Named Supplier
      """
    And JBOM_PROFILE_PATH contains "env_profiles"
    When I load the named profile
    Then resolved profile value "supplier.name" should equal "Env Named Supplier"
    And resolved profile value "supplier.website" should equal "https://cwd.example"
    And resolved profile value "supplier.description" should equal "from_home_common"
    And resolved profile value "defaults.search.output_fields" should equal list "cwd_only"
