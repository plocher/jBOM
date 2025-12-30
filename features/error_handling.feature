Feature: Error Handling and Edge Cases
  As a PCB designer
  I want jBOM to handle errors gracefully with clear messages
  So that I can quickly identify and fix issues in my workflow

  Scenario: Missing inventory file
    Given a KiCad project named "SimpleProject"
    And I specify nonexistent inventory file "/path/to/missing.csv"
    When I generate a BOM
    Then the error message reports "Inventory file not found: /path/to/missing.csv" and exits with code 1

  Scenario: Invalid inventory file format
    Given a KiCad project named "SimpleProject"
    And an inventory file with invalid format
      | InvalidColumn | AnotherBadColumn |
      | data1         | data2            |
    When I generate a BOM
    Then the error message reports "Missing required columns: IPN, Category, Value, Package" and exits with code 1

  Scenario: Missing project files
    Given I specify nonexistent project directory "/path/to/missing"
    When I generate a BOM
    Then the error message reports "Project directory not found: /path/to/missing" and suggests checking the path

  Scenario: Corrupted schematic file
    Given a KiCad project named "SimpleProject"
    And the schematic file contains corrupted syntax "(invalid_s_expression_syntax"
    When I generate a BOM
    Then the error message reports "Error parsing schematic: SimpleProject.kicad_sch" with syntax error details

  Scenario: Permission denied for output file
    Given a KiCad project and forbidden output path
    Then the error handling reports "permission denied" suggesting permission check

  Scenario: Empty inventory file
    Given a KiCad project and empty inventory file
    Then the processing succeeds with empty inventory warning and unmatched components

  Scenario: Empty schematic (no components)
    Given a KiCad project with empty schematic
    Then the processing succeeds with no components warning and empty BOM file

  Scenario: Invalid API key for search
    Given invalid API key for search
    Then the error handling reports "authentication failed" suggesting API key check

  Scenario: Network timeout during search
    Given network connectivity issues during search
    Then the error handling reports "network error" suggesting connectivity check

  Scenario: Hierarchical schematic with missing sub-sheet
    Given hierarchical schematic with missing sub-sheet files
    Then the processing succeeds with missing sub-sheet warnings and partial BOM

  Scenario: Graceful degradation with partial failures
    Given mixed valid and invalid conditions
    Then the processing succeeds for valid parts with specific error reporting
