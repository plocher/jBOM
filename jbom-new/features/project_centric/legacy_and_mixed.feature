Feature: Legacy and mixed project discovery

  # No Background - self-contained scenarios

  Scenario: Prefer modern .kicad_pro over legacy .pro when both exist
    Given a project "legacy" placed in "legacy_project"
    And I create file "legacy_project/legacy.pro" with content "# Legacy project file"
    And the schematic "legacy" contains:
      | Reference | Value | Footprint     | LibID    |
      | R1        | 10K   | R_0805_2012   | Device:R |
    When I run jbom command "bom legacy_project -o console -v"
    Then the command should succeed
    And the error output should mention "using modern project file legacy.kicad_pro"

  Scenario: Fall back to legacy .pro when .kicad_pro missing
    Given I create directory "legacy_only"
    And I create file "legacy_only/old.pro" with content "# Legacy project file"
    And I create file "legacy_only/old.kicad_sch" with content "(kicad_sch (version 20211123) (generator eeschema))"
    When I run jbom command "bom legacy_only -o console -v"
    Then the command should succeed
    And the error output should mention "using legacy project file old.pro"
