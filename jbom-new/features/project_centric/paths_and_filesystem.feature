Feature: Paths and filesystem robustness

  Background:
    Given the sample fixtures under "features/fixtures/kicad_samples"

  Scenario: Relative vs absolute paths yield identical results
    When I run jbom command "bom features/fixtures/kicad_samples/flat_project -o console"
    And I run jbom command "bom `pwd`/features/fixtures/kicad_samples/flat_project -o console"
    Then the two command outputs should be identical

  Scenario: Symlinked project directory resolves to realpath in messages
    Given I create symlink "features/fixtures/flat_link" to "features/fixtures/kicad_samples/flat_project"
    When I run jbom command "bom features/fixtures/flat_link -o console -v"
    Then the command should succeed
    And the error output should mention "resolved path"

  Scenario: Non-ASCII path names are supported
    Given I create directory "features/fixtures/kicad_samples/μControllerProject"
    And I create file "features/fixtures/kicad_samples/μControllerProject/u.kicad_pro" with content "(kicad_project (version 1))"
    And I create file "features/fixtures/kicad_samples/μControllerProject/u.kicad_sch" with content "(kicad_sch (version 20211123))"
    When I run jbom command "bom features/fixtures/kicad_samples/μControllerProject -o console -v"
    Then the command should succeed
    And the error output should mention "μControllerProject"
