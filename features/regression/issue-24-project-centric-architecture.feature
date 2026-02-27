@regression
Feature: [Issue #24] Project-Centric Architecture - File-centric commands break KiCad workflows

  # Background: Describe the original issue
  # - What was happening?
  #   jBOM commands required explicit .kicad_sch/.kicad_pcb file paths
  #   Users couldn't run "jbom bom ." in project directories
  #   No cross-command intelligence (e.g., BOM given .kicad_pcb file would fail)
  #   Commands didn't understand KiCad project structure or relationships
  # - Under what conditions?
  #   When users tried natural KiCad workflows with project directories
  #   When users provided "wrong" file type to commands (PCB to BOM, schematic to POS)
  #   When working with hierarchical schematics across multiple files
  # - What was the expected behavior?
  #   Commands should discover project files automatically like KiCad does
  #   Should accept directories, base names, and provide cross-file intelligence

  Background:
    Given the generic fabricator is selected
    And a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10k   | R_0603_1608 |
    And a PCB that contains:
      | Reference | X | Y    | Footprint   |
      | R1        | 5 | 3    | R_0603_1608 |

  Scenario: Core regression - BOM works with current directory
    # Originally: jbom bom . would fail with "file not found" error
    # Minimal test to ensure project discovery doesn't regress

    When I run jbom command "bom -o console"
    Then the command should succeed
    And the BOM output should contain component "R1" with value "10k"

  Scenario: Core regression - POS works with current directory
    # Originally: jbom pos . would fail with "file not found" error
    # Minimal test to ensure project discovery doesn't regress

    When I run jbom command "pos -o console"
    Then the command should succeed
    And the POS output should contain component "R1" at position "5" x "3" y
