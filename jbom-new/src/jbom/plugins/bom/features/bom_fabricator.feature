Feature: BOM Fabricator Support
  As a hardware developer
  I want to generate fabricator-specific BOMs with proper part numbers and column headers
  So that I can submit accurate BOMs for PCB assembly

  Background:
    Given I have a test schematic with components containing fabricator part numbers

  Scenario: Generate JLCPCB BOM with LCSC part numbers
    Given the schematic contains components with LCSC part numbers:
      | Reference | Value | Footprint | LCSC   | MPN      | Manufacturer    |
      | R1        | 10K   | R_0805    | C17414 | RC0805FR | Yageo           |
      | R2        | 10K   | R_0805    | C17414 | RC0805FR | Yageo           |
      | C1        | 100nF | C_0603    | C14663 | C0603X7R | Samsung Electro |
    When I run "jbom bom test-project.kicad_sch --fabricator jlc -o console"
    Then the BOM should contain JLCPCB-formatted entries:
      | Designator | Value | Footprint | Quantity | LCSC Part# | Manufacturer Part# | Manufacturer    |
      | R1,R2      | 10K   | R_0805    | 2        | C17414     | RC0805FR           | Yageo           |
      | C1         | 100nF | C_0603    | 1        | C14663     | C0603X7R           | Samsung Electro |

  Scenario: Generate JLCPCB BOM using --jlc shorthand
    Given the schematic contains components with LCSC part numbers
    When I run "jbom bom test-project.kicad_sch --jlc -o console"
    Then the BOM should use JLCPCB column headers
    And the BOM should include LCSC part numbers

  Scenario: Generate PCBWay BOM with distributor part numbers
    Given the schematic contains components with distributor part numbers:
      | Reference | Value | Footprint | Mouser        | MPN      | Manufacturer    |
      | R1        | 10K   | R_0805    | 603-RC0805FR  | RC0805FR | Yageo           |
      | R2        | 10K   | R_0805    | 603-RC0805FR  | RC0805FR | Yageo           |
      | C1        | 100nF | C_0603    | 187-CL10B104K | CL10B104 | Samsung Electro |
    When I run "jbom bom test-project.kicad_sch --fabricator pcbway -o console"
    Then the BOM should contain PCBWay-formatted entries:
      | Designator | Value | Package | Quantity | Distributor Part Number |
      | R1,R2      | 10K   | R_0805  | 2        | 603-RC0805FR            |
      | C1         | 100nF | C_0603  | 1        | 187-CL10B104K           |

  Scenario: Handle missing fabricator part numbers gracefully
    Given the schematic contains components without fabricator part numbers:
      | Reference | Value | Footprint | MPN      | Manufacturer |
      | R1        | 10K   | R_0805    | RC0805FR | Yageo        |
      | C1        | 100nF | C_0603    | CL10B104 | Samsung      |
    When I run "jbom bom test-project.kicad_sch --fabricator jlc -o console"
    Then the BOM should contain entries with empty LCSC Part# fields:
      | Designator | Value | Footprint | Quantity | LCSC Part# | Manufacturer Part# |
      | R1         | 10K   | R_0805    | 1        |            | RC0805FR           |
      | C1         | 100nF | C_0603    | 1        |            | CL10B104           |

  Scenario: Use custom field list with fabricator
    Given the schematic contains components with fabricator part numbers
    When I run "jbom bom test-project.kicad_sch --fabricator jlc --fields references,value,quantity,fabricator_part_number -o console"
    Then the BOM should contain only the specified fields:
      | Designator | Value | Quantity | LCSC Part# |
      | R1,R2      | 10K   | 2        | C17414     |
      | C1         | 100nF | 1        | C14663     |

  Scenario: Fallback to manufacturer part numbers when fabricator part missing
    Given the schematic contains components with mixed part number availability:
      | Reference | Value | Footprint | LCSC   | MPN      | Manufacturer |
      | R1        | 10K   | R_0805    | C17414 | RC0805FR | Yageo        |
      | R2        | 1K    | R_0805    |        | RC0805JR | Yageo        |
    When I run "jbom bom test-project.kicad_sch --fabricator jlc -o console"
    Then the BOM should show LCSC numbers when available and blank when not:
      | Designator | Value | Footprint | Quantity | LCSC Part# | Manufacturer Part# |
      | R1         | 10K   | R_0805    | 1        | C17414     | RC0805FR           |
      | R2         | 1K    | R_0805    | 1        |            | RC0805JR           |
