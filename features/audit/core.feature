Feature: Audit command core behavior
  As a hardware designer
  I want jbom audit to check field quality and inventory coverage
  So that I can find problems before generating fabrication files

  # ──────────────────────────────────────────────────────────────
  # Quality checks (project mode, no --inventory)
  # ──────────────────────────────────────────────────────────────

  Scenario: Audit exits 0 and produces no report rows for a clean project
    Given a schematic that contains:
      | UUID    | Reference | Value | Footprint            | Package | LibID    | Manufacturer | MFGPN              |
      | uuid-r1 | R1        | 10K   | Resistor_SMD:R_0603  | 0603    | Device:R | YAGEO        | RC0603FR-0710KL    |
    When I run jbom command "audit ."
    Then the command should succeed
    And the exit code should be 0

  Scenario: required-field gaps appear in project couplet audit output
    Given a schematic that contains:
      | UUID    | Reference | Value | Footprint            | Package | LibID    |
      | uuid-r1 | R1        |       | Resistor_SMD:R_0603  | 0603    | Device:R |
    When I run jbom command "audit ."
    Then the command should fail
    And the output should contain "RowType"
    And the output should contain "Missing attributes: Value"
    And the output should contain "SUGGESTED"
    And the output should contain "MISSING"

  Scenario: project audit suggestions focus on EM fields and exclude supply-chain fields
    Given a schematic that contains:
      | UUID    | Reference | Value | Footprint            | Package | LibID    |
      | uuid-r1 | R1        | 10K   | Resistor_SMD:R_0603  | 0603    | Device:R |
    When I run jbom command "audit ."
    Then the command should succeed
    And the output should contain "Missing attributes: Tolerance, Power"
    And the output should contain "5%"
    And the output should contain "100mW"
    And the output should not contain "Manufacturer"
    And the output should not contain "MFGPN"

  Scenario: --strict promotes WARN rows to failures
    Given a schematic that contains:
      | UUID    | Reference | Value | Footprint            | Package | LibID    |
      | uuid-r1 | R1        | 10K   | Resistor_SMD:R_0603  | 0603    | Device:R |
    When I run jbom command "audit . --strict"
    Then the command should fail
    And the exit code should be 1

  # ──────────────────────────────────────────────────────────────
  # Coverage checks (project mode + --inventory)
  # ──────────────────────────────────────────────────────────────

  Scenario: audit fails when component has no inventory match
    Given a schematic that contains:
      | UUID    | Reference | Value | Footprint            | Package | LibID    |
      | uuid-r1 | R1        | 10K   | Resistor_SMD:R_0603  | 0603    | Device:R |
    And an inventory file "catalog.csv" that contains:
      | RowType | IPN      | Category | Value | Package | Priority |
      | ITEM    | C-100N   | CAP      | 100nF | 0603    | 1        |
    When I run jbom command "audit . --inventory catalog.csv"
    Then the command should fail
    And the exit code should be 1
    And the output should contain "R1"

  Scenario: No COVERAGE_GAP when every component matches inventory
    Given a schematic that contains:
      | UUID    | Reference | Value | Footprint            | Package | LibID    |
      | uuid-r1 | R1        | 10K   | Resistor_SMD:R_0603  | 0603    | Device:R |
    And an inventory file "catalog.csv" that contains:
      | RowType | IPN      | Category | Value | Package | Priority |
      | ITEM    | R-10K    | RES      | 10K   | 0603    | 1        |
    When I run jbom command "audit . --inventory catalog.csv"
    Then the command should succeed
    And the output should not contain "COVERAGE_GAP"

  # ──────────────────────────────────────────────────────────────
  # Report output
  # ──────────────────────────────────────────────────────────────

  Scenario: Audit writes report CSV when -o is given
    Given a schematic that contains:
      | UUID    | Reference | Value | Footprint            | Package | LibID    |
      | uuid-r1 | R1        | 10K   | Resistor_SMD:R_0603  | 0603    | Device:R |
    When I run jbom command "audit . -o report.csv"
    Then the command should succeed
    And a file named "report.csv" should exist
    And the file "report.csv" should contain "RowType"

  Scenario: Audit-generated QUOTE_ALL report.csv is consumable by annotate without error
    Given a schematic that contains:
      | UUID    | Reference | Value | Footprint            | Package | LibID    |
      | uuid-r1 | R1        | 10K   | Resistor_SMD:R_0603  | 0603    | Device:R |
    When I run jbom command "audit . -o report.csv"
    Then the command should succeed
    And a file named "report.csv" should exist
    When I run jbom command "annotate . --repairs report.csv --dry-run"
    Then the command should succeed
    And the output should contain "failed 0"
