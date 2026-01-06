Feature: Schematic Loading
  As a PCB designer
  I want jBOM to correctly load KiCad schematics in various project structures
  So that I can use flexible project organization without issues

  Scenario: Load schematic when project directory matches schematic name
    Given a KiCad project named "StandardProject"
    And the project uses a schematic named "StandardProject"
    And the "StandardProject" schematic contains components:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10K   | R_0603_1608 | Device:R |
    When I generate a generic BOM for StandardProject
    Then the BOM file contains component R1

  Scenario: Load schematic when schematic name differs from project directory
    Given a KiCad project named "ProjectDir"
    And the project uses a schematic named "DifferentName"
    And the "DifferentName" schematic contains components:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10K   | R_0603_1608 | Device:R |
    When I generate a generic BOM for ProjectDir using schematic "DifferentName"
    Then the BOM file contains component R1

  Scenario: Load schematic directly by file path
    Given a standalone schematic file "DirectLoad.kicad_sch" with components:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10K   | R_0603_1608 | Device:R |
    When I generate a BOM from schematic file "DirectLoad.kicad_sch"
    Then the BOM file contains component R1

  Scenario: Handle multiple schematics in project directory
    Given a KiCad project named "MultiSchematic"
    And the project has schematics:
      | Schematic    | Purpose    |
      | MainBoard    | Primary    |
      | TestFixture  | Secondary  |
    And the "MainBoard" schematic contains components:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10K   | R_0603_1608 | Device:R |
    And the "TestFixture" schematic contains components:
      | Reference | Value | Footprint   | LibID    |
      | R2        | 1K    | R_0603_1608 | Device:R |
    When I generate a BOM from schematic "MultiSchematic/MainBoard.kicad_sch"
    Then the BOM file contains component R1
    And the BOM file does not contain component R2

  Scenario: Prefer explicit schematic path over default project schematic
    Given a KiCad project named "PreferenceTest"
    And the project has a default schematic "PreferenceTest.kicad_sch" with components:
      | Reference | Value | Footprint   | LibID    |
      | R1        | 10K   | R_0603_1608 | Device:R |
    And the project has a schematic "Alternative.kicad_sch" with components:
      | Reference | Value | Footprint   | LibID    |
      | R2        | 1K    | R_0603_1608 | Device:R |
    When I generate a BOM from schematic "PreferenceTest/Alternative.kicad_sch"
    Then the BOM file contains component R2
    And the BOM file does not contain component R1

  Scenario: Error on missing schematic file
    Given a KiCad project directory "EmptyProject" with no schematics
    When I attempt to generate a BOM for EmptyProject
    Then the command fails with exit code 1
    And the error message reports "No schematic file found"
    And the error message suggests checking the project directory

  Scenario: Error on ambiguous schematic selection
    Given a KiCad project named "AmbiguousProject"
    And the project has multiple schematics but no default:
      | Schematic    |
      | BoardA       |
      | BoardB       |
    When I attempt to generate a BOM for AmbiguousProject without specifying a schematic
    Then the command fails with exit code 1
    And the error message reports "Multiple schematics found"
    And the error message lists available schematics: "BoardA.kicad_sch, BoardB.kicad_sch"
    And the error message suggests specifying which schematic to use

  Scenario: Load hierarchical schematic with valid sub-sheets
    Given a hierarchical KiCad project named "HierarchicalBoard" with root schematic referencing sub-sheet "PowerSupply.kicad_sch"
    And the root schematic contains components:
      | Reference | Value | Footprint |
      | R1        | 10k   | R_0805    |
    And the sub-sheet "PowerSupply.kicad_sch" contains components:
      | Reference | Value | Footprint |
      | R2        | 100   | R_0805    |
    When I generate a generic BOM for HierarchicalBoard
    Then the BOM file contains component R1 from root schematic
    And the BOM file contains component R2 from sub-sheet
    And component quantities are correctly aggregated

  @wip
  Scenario: Handle hierarchical schematic with missing sub-sheet file
    Given a hierarchical KiCad project named "HierarchicalProject" with root schematic referencing sub-sheet "PowerSupply.kicad_sch"
    And the root schematic contains components:
      | Reference | Value | Footprint |
      | R1        | 10k   | R_0805    |
    And the sub-sheet file "PowerSupply.kicad_sch" does not exist
    And an inventory file "inventory.csv" containing components:
      | IPN | Category | Value | Package | Manufacturer | Description |
      | RES001 | Resistor | 10k | R_0805 | Generic | 10k ohm resistor |
    When I generate a generic BOM for HierarchicalProject using inventory.csv
    Then the BOM generation succeeds with exit code 0
    And the output contains warning "Sub-sheet not found: PowerSupply.kicad_sch - continuing with available components"
    And the BOM file contains component R1 from root schematic
    And the BOM file does not contain any components from the missing sub-sheet

  Scenario: Load hierarchical schematic with nested sub-sheets
    Given a hierarchical KiCad project named "NestedProject"
    And the root schematic "NestedProject.kicad_sch" references sub-sheet "PowerSection.kicad_sch"
    And the sub-sheet "PowerSection.kicad_sch" references sub-sheet "Regulators.kicad_sch"
    And each schematic contains components at its level
    When I generate a BOM for NestedProject
    Then the BOM contains components from all three hierarchical levels
    And component references are properly scoped by sheet path
