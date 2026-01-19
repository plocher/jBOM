Feature: BOM Output Formats
  As a hardware developer
  I want to generate BOMs in different output formats (CSV, console table)
  So that I can use them for different purposes (manufacturing, review)

  Background:
    Given I have a test schematic with components

  Scenario: Generate CSV file with proper formatting
    When I run "jbom bom --fabricator generic test-project.kicad_sch -o output.csv"
    Then a CSV file "output.csv" should be created
    And the CSV should have proper headers as first row
    And the CSV should use comma separators
    And component references should be comma-separated within cells
    And the CSV should be valid for spreadsheet import

  Scenario: Generate CSV to stdout
    When I run "jbom bom --fabricator generic test-project.kicad_sch --stdout"
    Then the output should be valid CSV format
    And the output should contain component data
    And the first line should contain headers
    And subsequent lines should contain component entries

  Scenario: Generate console table format
    When I run "jbom bom --fabricator generic test-project.kicad_sch -o console"
    Then the output should contain a formatted table
    And the table should have aligned columns
    And the table should have a header row
    And the table should show component data in readable format
    And reference lists should be comma-separated

  Scenario: Generate to file with automatic extension
    When I run "jbom bom --fabricator generic test-project.kicad_sch -o bom_output"
    Then a file "bom_output" should be created
    And the file should contain valid CSV data

  Scenario: Handle special characters in component values
    Given the schematic contains components with special values:
      | Reference | Value    | Footprint |
      | R1        | 10K,5%   | R_0805    |
      | R2        | "quoted" | R_0805    |
      | C1        | 100nF    | C_0603    |
    When I run "jbom bom --fabricator generic test-project.kicad_sch -o output.csv"
    Then the CSV should properly escape special characters
    And the CSV should be parseable by standard CSV readers

  Scenario: Generate empty BOM when no components
    Given the schematic contains no components
    When I run "jbom bom --fabricator generic test-project.kicad_sch -o output.csv"
    Then a CSV file "output.csv" should be created
    And the CSV should contain only the header row
    And the CSV should be valid

  Scenario: Console table with long component lists
    Given the schematic contains many components of the same type:
      | Reference | Value | Footprint |
      | R1        | 10K   | R_0805    |
      | R2        | 10K   | R_0805    |
      | R3        | 10K   | R_0805    |
      | R4        | 10K   | R_0805    |
      | R5        | 10K   | R_0805    |
    When I run "jbom bom --fabricator generic test-project.kicad_sch -o console"
    Then the table should show "R1,R2,R3,R4,R5" in the references column
    And the quantity should be 5
    And the table formatting should remain readable
