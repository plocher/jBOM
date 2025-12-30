Feature: Error Handling and Edge Cases
  As a PCB designer
  I want jBOM to handle errors gracefully with clear messages
  So that I can quickly identify and fix issues in my workflow

  Scenario: Missing inventory file
    Given a KiCad project and nonexistent inventory file
    Then the error handling reports "Inventory file not found" with missing file path

  Scenario: Invalid inventory file format
    Given a KiCad project and inventory file with invalid format
    Then the error handling reports "missing required columns" with specific column details

  Scenario: Missing project files
    Given nonexistent project files
    Then the error handling reports "project not found" suggesting path check

  Scenario: Corrupted schematic file
    Given a KiCad project with corrupted schematic syntax
    Then the error handling reports "error parsing schematic" identifying problematic file

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
