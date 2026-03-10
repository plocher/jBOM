Feature: Annotate command core behavior
  As a hardware designer
  I want audit report changes written back to schematic properties by UUID
  So that I can apply approved field fixes safely

  Background:
    Given a schematic that contains:
      | UUID    | Reference | Value | Footprint | Package | LibID    |
      | uuid-r1 | R1        | 10K   | R_0603    | 0603    | Device:R |

  Scenario: Annotate writes approved values for matching UUID rows
    Given an inventory file "report.csv" that contains:
      | UUID    | RefDes | Field     | ApprovedValue | Action |
      | uuid-r1 | R1     | Value     | 11K           | SET    |
      | uuid-r1 | R1     | Package   | 0805          | SET    |
      | uuid-r1 | R1     | Footprint | R_0805        | SET    |
      | uuid-r1 | R1     | LCSC      | C9999         | SET    |
    When I run jbom command "annotate . --repairs report.csv"
    Then the command should succeed
    And the file "project.kicad_sch" should contain "\"Value\" \"11K\""
    And the file "project.kicad_sch" should contain "\"Package\" \"0805\""
    And the file "project.kicad_sch" should contain "\"Footprint\" \"R_0805\""
    And the file "project.kicad_sch" should contain "\"LCSC\" \"C9999\""

  Scenario: Annotate skips rows with blank ApprovedValue and preserves existing values
    Given an inventory file "report.csv" that contains:
      | UUID    | RefDes | Field   | ApprovedValue | Action |
      | uuid-r1 | R1     | Value   |               | SET    |
      | uuid-r1 | R1     | Package |               | SET    |
    When I run jbom command "annotate . --repairs report.csv"
    Then the command should succeed
    And the file "project.kicad_sch" should contain "\"Value\" \"10K\""
    And the file "project.kicad_sch" should contain "\"Package\" \"0603\""

  Scenario: Annotate writes tilde literal when ApprovedValue is tilde
    Given an inventory file "report.csv" that contains:
      | UUID    | RefDes | Field   | ApprovedValue | Action |
      | uuid-r1 | R1     | Package | ~             | SET    |
    When I run jbom command "annotate . --repairs report.csv"
    Then the command should succeed
    And the file "project.kicad_sch" should contain "\"Package\" \"~\""

  Scenario: Annotate skips rows where Action is not SET
    Given an inventory file "report.csv" that contains:
      | UUID    | RefDes | Field | ApprovedValue    | Action |
      | uuid-r1 | R1     | Value | SHOULD_NOT_APPLY | SKIP   |
      | uuid-r1 | R1     | Value | SHOULD_NOT_APPLY | IGNORE |
      | uuid-r1 | R1     | Value | SHOULD_NOT_APPLY |        |
    When I run jbom command "annotate . --repairs report.csv"
    Then the command should succeed
    And the file "project.kicad_sch" should contain "\"Value\" \"10K\""

  Scenario: Annotate dry-run reports changes without writing schematic
    Given an inventory file "report.csv" that contains:
      | UUID    | RefDes | Field | ApprovedValue | Action |
      | uuid-r1 | R1     | Value | 22K           | SET    |
    When I run jbom command "annotate . --repairs report.csv --dry-run"
    Then the command should succeed
    And the output should contain "would apply"
    And the file "project.kicad_sch" should contain "\"Value\" \"10K\""

  Scenario: Annotate exits non-zero when UUID not found in schematic
    Given an inventory file "report.csv" that contains:
      | UUID         | RefDes | Field | ApprovedValue | Action |
      | uuid-missing | X99    | Value | 22K           | SET    |
    When I run jbom command "annotate . --repairs report.csv"
    Then the command should fail
    And the output should contain "uuid-missing"
