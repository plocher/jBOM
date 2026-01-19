Feature: BOM Logic - Component Aggregation and Filtering
  As a hardware developer
  I want components to be properly aggregated and filtered
  So that my BOM accurately reflects what needs to be ordered

  # Component Aggregation Scenarios
  Scenario: Aggregate components by value and footprint
    Given a clean test environment
    And a KiCad project named "AggregationProject"
    And the schematic contains multiple similar components:
      | Reference | Value | Footprint |
      | R1        | 10K   | R_0805    |
      | R2        | 10K   | R_0805    |
      | R3        | 10K   | R_0805    |
      | R4        | 1K    | R_0805    |
    When I run "jbom bom --fabricator generic --stdout" in the project directory
    Then the command exits with code 0
    And the BOM contains aggregated entries:
      | References | Value | Footprint | Qty |
      | R1,R2,R3   | 10K   | R_0805    | 3   |
      | R4         | 1K    | R_0805    | 1   |

  Scenario: Handle components with same value but different footprints
    Given a clean test environment
    And a KiCad project named "FootprintProject"
    And the schematic contains:
      | Reference | Value | Footprint |
      | R1        | 10K   | R_0805    |
      | R2        | 10K   | R_1206    |
      | R3        | 10K   | R_0805    |
    When I run "jbom bom --fabricator generic --stdout" in the project directory
    Then the command exits with code 0
    And the BOM contains separate entries for different footprints

  # Component Filtering Scenarios
  Scenario: Exclude DNP components by default
    Given a clean test environment
    And a KiCad project named "FilterProject"
    And the schematic contains components with DNP attributes:
      | Reference | Value | Footprint | DNP   |
      | R1        | 10K   | R_0805    | false |
      | R2        | 1K    | R_0805    | true  |
    When I run "jbom bom --fabricator generic --stdout" in the project directory
    Then the command exits with code 0
    And the BOM excludes DNP components
    And stdout contains "R1"
    And stdout does not contain "R2"

  Scenario: Include DNP components when requested
    Given a clean test environment
    And a KiCad project named "IncludeDnpProject"
    And the schematic contains components with DNP attributes:
      | Reference | Value | Footprint | DNP   |
      | R1        | 10K   | R_0805    | false |
      | R2        | 1K    | R_0805    | true  |
    When I run "jbom bom --fabricator generic --stdout --include-dnp" in the project directory
    Then the command exits with code 0
    And stdout contains "R1"
    And stdout contains "R2"

  Scenario: Exclude components marked exclude_from_bom by default
    Given a clean test environment
    And a KiCad project named "ExcludeProject"
    And the schematic contains components with exclude attributes:
      | Reference | Value | Footprint | Exclude_from_BOM |
      | R1        | 10K   | R_0805    | false            |
      | R2        | 1K    | R_0805    | true             |
    When I run "jbom bom --fabricator generic --stdout" in the project directory
    Then the command exits with code 0
    And stdout contains "R1"
    And stdout does not contain "R2"
