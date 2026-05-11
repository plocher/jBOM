Feature: jbom gerbers — standalone Gerber/drill generation
  As a PCB engineer
  I want to generate Gerber and drill files from a KiCad project
  So that I can submit fabrication files to a PCB manufacturer

  Background:
    Given a PCB that contains:
      | Reference | X  | Y  | Rotation | Side | Footprint   |
      | R1        | 10 | 10 | 0        | TOP  | R_0805_2012 |
    And a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
    And mock kicad-cli is available

  Scenario: Standard 9-layer gerbers produced with correct Protel extensions
    When I run jbom command "gerbers ."
    Then the command should succeed
    # 9 layers from generic/JLC config + 2 drill files (split PTH/NPTH)
    And the gerbers output directory should contain 11 gerber files
    And a gerber file for layer "F.Cu" should exist
    And a gerber file for layer "B.Cu" should exist
    And a gerber file for layer "Edge.Cuts" should exist
    And the gerber file for layer "F.Cu" should use extension ".gtl"
    And the gerber file for layer "B.Cu" should use extension ".gbl"
    # Edge.Cuts uses .gm1 in KiCad 10 — NOT .gko
    And the gerber file for layer "Edge.Cuts" should use extension ".gm1"
    And the gerber file for layer "F.Mask" should use extension ".gts"
    And the gerber file for layer "B.Mask" should use extension ".gbs"
    And a drill file should exist in the gerbers output directory

  Scenario: Gerber files contain valid X2 attribute headers
    When I run jbom command "gerbers ."
    Then the command should succeed
    # Mock writes structurally valid Gerber X2 headers — verify key attributes
    And the gerber file for layer "F.Cu" should contain "TF.GenerationSoftware"
    And the gerber file for layer "F.Cu" should contain "TF.FileFunction"
    And the gerber file for layer "F.Cu" should contain "TF.FilePolarity,Positive"
    And the gerber file for layer "F.Cu" should contain "%FSLAX46Y46*%"
    And the gerber file for layer "F.Cu" should contain "%MOMM*%"
    And the gerber file for layer "Edge.Cuts" should contain "TF.FileFunction,Profile,NP"

  Scenario: Each copper layer carries the correct Copper FileFunction attribute
    When I run jbom command "gerbers ."
    Then the command should succeed
    And the gerber file for layer "F.Cu" should contain "TF.FileFunction,Copper,L1,Top"
    And the gerber file for layer "B.Cu" should contain "TF.FileFunction,Copper,L2,Bot"
    And the gerber file for layer "F.Mask" should contain "TF.FileFunction,Soldermask,Top"
    And the gerber file for layer "B.Mask" should contain "TF.FileFunction,Soldermask,Bot"
    And the gerber file for layer "F.Silkscreen" should contain "TF.FileFunction,Legend,Top"

  Scenario: Output directory reported in command output
    When I run jbom command "gerbers ."
    Then the command should succeed
    And the output should contain "Written:"

  Scenario: dry-run reports prerequisites without generating files
    When I run jbom command "gerbers . --dry-run"
    # dry-run always exits 0 when kicad-cli is found (mock is on PATH)
    # It prints the resolved PCB path and output directory without writing files
    Then the command should succeed
    And the output should contain "Dry run: PCB file"
    And the output should contain "Dry run: Output dir"
    And "gerbers" should not exist in the sandbox
