Feature: Legacy and mixed project discovery

  Background:
    Given the sample fixtures under "features/project_centric/fixtures/kicad_samples"

  Scenario: Prefer modern .kicad_pro over legacy .pro when both exist
    Given I am in directory "features/project_centric/fixtures/kicad_samples/legacy_pro"
    And I create file "features/project_centric/fixtures/kicad_samples/legacy_pro/legacy.kicad_pro" with content "(kicad_project (version 1))"
    When I run jbom command "bom . -o console -v"
    Then the command should succeed
    And the error output should mention "using modern project file legacy.kicad_pro"

  Scenario: Fall back to legacy .pro when .kicad_pro missing
    When I run jbom command "bom features/project_centric/fixtures/kicad_samples/legacy_pro -o console -v"
    Then the command should succeed
    And the error output should mention "using legacy project file legacy.pro"
