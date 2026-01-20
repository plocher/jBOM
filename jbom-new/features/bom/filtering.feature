Feature: BOM Filtering (DNP / Excluded)
  As a hardware developer
  I want to control which components are included in the BOM
  So that I can generate BOMs for different build configurations

  Background:
    Given a clean test workspace

  Scenario: Include DNP components when requested
    Given a KiCad schematic file "dnp_include.kicad_sch" with DNP components
    When I run "jbom bom dnp_include.kicad_sch --include-dnp --generic"
    Then the command exits with code 0
    And the output contains "R2,22K"

  Scenario: Exclude DNP components by default
    Given a KiCad schematic file "dnp_exclude.kicad_sch" with DNP components
    When I run "jbom bom dnp_exclude.kicad_sch --generic"
    Then the command exits with code 0
    And the output does not contain "R2"

  Scenario: Include components excluded from BOM when requested
    Given a KiCad schematic file "excluded.kicad_sch" with components excluded from BOM
    When I run "jbom bom excluded.kicad_sch --include-excluded --generic"
    Then the command exits with code 0
    And the output contains excluded component references
