Feature: Hierarchical schematic handling

  Background:
    Given the sample fixtures under "features/fixtures/kicad_samples"

  Scenario: BOM includes all child sheets and reports count
    When I run jbom command "bom features/fixtures/kicad_samples/hier_project -o console -v"
    Then the command should succeed
    And the error output should mention "Processing hierarchical design"

  Scenario: Missing child sheet logs warning but continues
    Given an empty directory "features/fixtures/tmp_hier_missing"
    And I create file "features/fixtures/tmp_hier_missing/main.kicad_sch" with content "(kicad_sch (version 20211123) (sheet (property \"Sheetfile\" \"missing.kicad_sch\")))"
    When I run jbom command "bom features/fixtures/tmp_hier_missing -o console -v"
    Then the command should succeed
    And the error output should contain "missing sheet missing.kicad_sch"
