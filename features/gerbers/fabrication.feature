Feature: jbom fab — complete fabrication pipeline (BOM + CPL + Gerbers + Backup)
  As a manufacturing engineer
  I want to generate all fabrication artifacts in one command
  So that I can upload a complete package to a PCB manufacturer

  # jbom fab orchestrates BOM → POS → Gerbers → Backup in sequence.
  # The acceptance criteria from issue #227:
  #
  #   production/
  #     jbom.csv                              ← BOM (fabricator-ready)
  #     cpl.csv                               ← CPL/placement
  #     {title}_{revision}.zip                ← Gerber archive
  #     backups/
  #       {title}_{revision}_{timestamp}.zip  ← snapshot of all three artifacts

  Background:
    Given a PCB that contains:
      | Reference | X  | Y  | Rotation | Side | Footprint   |
      | R1        | 10 | 10 | 0        | TOP  | R_0805_2012 |
    And a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
    And mock kicad-cli is available

  Scenario: fab produces the complete production/ directory structure
    When I run jbom command "fab ."
    Then the command should succeed
    And the production directory should exist
    And the production artifact "jbom.csv" should exist
    And the production artifact "cpl.csv" should exist
    And a gerber zip matching "*.zip" should exist in production/
    And a backup zip should exist under "production/backups/"

  Scenario: fab output reports production directory path
    When I run jbom command "fab ."
    Then the command should succeed
    And the output should contain "Production directory:"

  Scenario: fab gerber zip contains files for key copper and profile layers
    When I run jbom command "fab ."
    Then the command should succeed
    # jbom fab passes no --layers flag so mock uses DEFAULT_LAYERS (F.Cu, B.Cu, Edge.Cuts)
    And the gerber zip should contain a file for layer "F.Cu"
    And the gerber zip should contain a file for layer "B.Cu"
    And the gerber zip should contain a file for layer "Edge.Cuts"

  Scenario: backup contains all three production artifacts
    # BOM + CPL + gerber zip = 3 entries in the backup archive
    When I run jbom command "fab ."
    Then the command should succeed
    And the backup zip should contain 3 files

  Scenario: --skip-gerbers produces BOM and CPL but no gerber zip
    When I run jbom command "fab . --skip-gerbers"
    Then the command should succeed
    And the production directory should exist
    And the production artifact "jbom.csv" should exist
    And the production artifact "cpl.csv" should exist
    And no file matching "*.zip" should exist in production/

  Scenario: --skip-gerbers backup contains only BOM and CPL
    # Without gerbers, only 2 artifacts are in the backup
    When I run jbom command "fab . --skip-gerbers"
    Then the command should succeed
    And the backup zip should contain 2 files

  Scenario: --skip-bom skips BOM generation but still creates CPL and gerbers
    When I run jbom command "fab . --skip-bom"
    Then the command should succeed
    And the production directory should exist
    And "production/jbom.csv" should not exist in the sandbox
    And the production artifact "cpl.csv" should exist
    And a gerber zip matching "*.zip" should exist in production/

  Scenario: --dry-run does not write any production files
    When I run jbom command "fab . --dry-run"
    Then the command should succeed
    And "production" should not exist in the sandbox
