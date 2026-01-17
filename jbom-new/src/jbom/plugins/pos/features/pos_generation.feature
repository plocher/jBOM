Feature: Simple POS Generation
  As a jBOM user
  I want to generate placement files from KiCad PCB
  So that I can send them to PCB assembly services

  Scenario: Generate POS from PCB file
    Given a KiCad PCB file exists at "test.kicad_pcb"
    When I run "jbom pos test.kicad_pcb"
    Then a POS file should be created
    And it should contain component placement data
    And the exit code should be 0

  Scenario: Generate POS to stdout
    Given a KiCad PCB file exists at "test.kicad_pcb"
    When I run "jbom pos test.kicad_pcb --output -"
    Then I should see CSV header in the output
    And I should see component placement data in the output
    And the exit code should be 0

  Scenario: Handle missing PCB file
    When I run "jbom pos nonexistent.kicad_pcb"
    Then I should see an error message
    And the exit code should be non-zero
