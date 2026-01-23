Feature: File Extension Validation
  As a user
  I want clear errors for unsupported file types
  So that I know what files jBOM can process

  Background:
    Given a clean test workspace

  Scenario: Unsupported file extension is rejected
    Given I create file "not_schematic.txt" with content "hello"
    When I run "jbom bom not_schematic.txt"
    Then the command exits with code 1
    And the error output contains "Expected .kicad_sch file"

  # REMOVED: WIP scenarios based on incorrect project discovery assumptions
  # These assumed jBOM looks for loose *.kicad_sch files, but it actually:
  # 1. Looks for *.kicad_pro files first
  # 2. Derives schematic names from project file or basename
  # 3. Does not glob for random schematic files
  #
  # If fallback-to-glob behavior is needed, it belongs in project_centric/ domain
  # with proper .kicad_pro context, not as schematic-loading edge cases.
