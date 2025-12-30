Feature: Error Handling and Edge Cases
  As a PCB designer
  I want jBOM to handle errors gracefully with clear messages
  So that I can quickly identify and fix issues in my workflow

  Scenario: Missing inventory file
    Given a KiCad project named "SimpleProject"
    When I run jbom command "bom SimpleProject -i nonexistent.csv -o output.csv"
    Then the command fails
    And the output contains "Inventory file not found"
    And the error message includes the missing file path

  Scenario: Invalid inventory file format
    Given a KiCad project named "SimpleProject"
    And an inventory file with invalid format (missing required columns)
    When I run jbom command "bom SimpleProject -i invalid_inventory.csv -o output.csv"
    Then the command fails
    And the output contains "missing required columns"
    And the error message lists which columns are missing

  Scenario: Missing project files
    When I run jbom command "bom NonexistentProject -i test_inventory.csv -o output.csv"
    Then the command fails
    And the output contains "project not found" or "no .kicad_sch files found"
    And the error message suggests checking the project path

  Scenario: Corrupted schematic file
    Given a KiCad project with corrupted schematic syntax
    When I run jbom command "bom CorruptedProject -i test_inventory.csv -o output.csv"
    Then the command fails
    And the output contains "error parsing schematic"
    And the error message identifies the problematic file

  Scenario: Permission denied for output file
    Given a KiCad project named "SimpleProject"
    And an inventory file with components
    When I run jbom command "bom SimpleProject -i test_inventory.csv -o /root/forbidden.csv"
    Then the command fails
    And the output contains "permission denied" or "cannot write"
    And the error message suggests checking file permissions

  Scenario: Empty inventory file
    Given a KiCad project named "SimpleProject"
    And an empty inventory file
    When I run jbom command "bom SimpleProject -i empty_inventory.csv -o output.csv"
    Then the command succeeds
    And the output warns about empty inventory
    And the BOM contains unmatched components only

  Scenario: Empty schematic (no components)
    Given a KiCad project with empty schematic
    And an inventory file with components
    When I run jbom command "bom EmptyProject -i test_inventory.csv -o output.csv"
    Then the command succeeds
    And the output warns about no components found
    And the BOM file is created but contains no entries

  Scenario: Invalid API key for search
    Given a KiCad project named "SimpleProject"
    When I run jbom command "search '10k resistor' --api-key INVALID_KEY"
    Then the command fails
    And the output contains "authentication failed" or "invalid API key"
    And the error suggests checking the API key

  Scenario: Network timeout during search
    Given network connectivity issues
    When I run jbom command "search '10k resistor' --limit 1"
    Then the command fails gracefully
    And the output contains "network error" or "timeout"
    And the error suggests checking internet connectivity

  Scenario: Hierarchical schematic with missing sub-sheet
    Given a hierarchical schematic referencing missing sub-sheet files
    When I run jbom command "bom HierarchicalProject -i test_inventory.csv -o output.csv"
    Then the command succeeds with warnings
    And the output warns about missing sub-sheet files
    And the BOM includes components from available sheets only
    And the missing sheets do not cause complete failure

  Scenario: Graceful degradation with partial failures
    Given mixed conditions (some files missing, some valid)
    When I run jbom command "bom MixedProject -i test_inventory.csv -o output.csv"
    Then the command succeeds for valid parts
    And the output reports specific errors for invalid parts
    And the BOM contains successfully processed components
    And the exit code indicates partial success
