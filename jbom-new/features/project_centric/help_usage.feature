Feature: CLI help documents project-centric usage

  Scenario: bom --help includes project-centric examples
    When I run jbom command "bom --help"
    Then the command should succeed
    And the output should contain "jbom bom ."
    And the output should contain "jbom bom <project_dir>"
    And the output should contain "jbom bom <base_name>"

  Scenario: pos --help includes project-centric examples
    When I run jbom command "pos --help"
    Then the command should succeed
    And the output should contain "jbom pos ."
    And the output should contain "jbom pos <project_dir>"
    And the output should contain "jbom pos <base_name>"

  Scenario: inventory --help includes project-centric examples
    When I run jbom command "inventory --help"
    Then the command should succeed
    And the output should contain "jbom inventory generate ."
    And the output should contain "jbom inventory generate <project_dir>"
    And the output should contain "jbom inventory generate <base_name>"
