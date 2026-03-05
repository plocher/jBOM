Feature: Annotate command core behavior
  As a hardware designer
  I want inventory CSV edits written back to schematic properties by UUID
  So that I can run the KLC compliance loop safely

  Background:
    Given a schematic that contains:
      | UUID    | Reference | Value | Footprint | Package | LibID    |
      | uuid-r1 | R1        | 10K   | R_0603    | 0603    | Device:R |

  Scenario: Annotate writes explicit values for matching UUID rows
    Given an inventory file "fixit.csv" that contains:
      | Project   | UUID    | Value | Package | Footprint | LCSC  |
      | /tmp/demo | uuid-r1 | 11K   | 0805    | R_0805    | C9999 |
    When I run jbom command "annotate -i fixit.csv"
    Then the command should succeed
    And the file "project.kicad_sch" should contain "\"Value\" \"11K\""
    And the file "project.kicad_sch" should contain "\"Package\" \"0805\""
    And the file "project.kicad_sch" should contain "\"Footprint\" \"R_0805\""
    And the file "project.kicad_sch" should contain "\"LCSC\" \"C9999\""

  Scenario: Annotate skips blank cells and preserves existing values
    Given an inventory file "fixit.csv" that contains:
      | Project   | UUID    | Value | Package | Footprint | LCSC |
      | /tmp/demo | uuid-r1 |       |         |           |      |
    When I run jbom command "annotate -i fixit.csv"
    Then the command should succeed
    And the file "project.kicad_sch" should contain "\"Value\" \"10K\""
    And the file "project.kicad_sch" should contain "\"Package\" \"0603\""
    And the file "project.kicad_sch" should contain "\"Footprint\" \"R_0603\""

  Scenario: Annotate writes tilde literal for non-blank fields
    Given an inventory file "fixit.csv" that contains:
      | Project   | UUID    | Value | Package | Footprint | LCSC |
      | /tmp/demo | uuid-r1 |       | ~       |           |      |
    When I run jbom command "annotate -i fixit.csv"
    Then the command should succeed
    And the file "project.kicad_sch" should contain "\"Package\" \"~\""

  Scenario: Annotate skips sub-header rows identified by Project sentinel
    Given an inventory file "fixit.csv" that contains:
      | Project | UUID    | Value             | Package           | Footprint         | LCSC             |
      | Project | uuid-r1 | SHOULD_NOT_APPLY | SHOULD_NOT_APPLY | SHOULD_NOT_APPLY | SHOULD_NOT_APPLY |
    When I run jbom command "annotate -i fixit.csv"
    Then the command should succeed
    And the file "project.kicad_sch" should contain "\"Value\" \"10K\""
    And the file "project.kicad_sch" should contain "\"Package\" \"0603\""
    And the file "project.kicad_sch" should contain "\"Footprint\" \"R_0603\""

  Scenario: Annotate dry-run reports changes without writing schematic
    Given an inventory file "fixit.csv" that contains:
      | Project   | UUID    | Value | Package | Footprint | LCSC  |
      | /tmp/demo | uuid-r1 | 22K   | 1206    | R_1206    | C7777 |
    When I run jbom command "annotate -i fixit.csv --dry-run"
    Then the command should succeed
    And the output should contain "Dry run complete."
    And the file "project.kicad_sch" should contain "\"Value\" \"10K\""
    And the file "project.kicad_sch" should contain "\"Package\" \"0603\""
    And the file "project.kicad_sch" should contain "\"Footprint\" \"R_0603\""

  Scenario: Annotate triage reports required blanks for Value and Package
    Given an inventory file "fixit.csv" that contains:
      | Project   | UUID    | Value | Package | Footprint |
      | /tmp/demo | uuid-r1 |       | 0603    | R_0603    |
      | /tmp/demo | uuid-r2 | 10K   |         | R_0603    |
    When I run jbom command "annotate -i fixit.csv --triage"
    Then the command should succeed
    And the output should contain "Triage report"
    And the output should contain "missing Value"
    And the output should contain "missing Package"
