Feature: POS main CLI flags
  As a user
  I want to use --stdout and --layer with the main CLI

  Background:
    Given a clean test environment
    And a KiCad project named "FlagsProject"
    And the PCB is populated with components:
      | Reference | Value | Package | Rotation | X   | Y   | Layer  | Footprint         |
      | U1        | MCU   | QFN48   | 0        | 0.0 | 0.0 | Top    | QFN-48_7x7mm      |
      | J1        | HDR   | HDR2    | 0        | 5.0 | 8.0 | Bottom | PinHeader_1x02    |

  Scenario: --stdout writes CSV to stdout
    When I run "python -m jbom.cli.main pos --stdout" in the project directory
    Then the command exits with code 0
    And stdout contains "Designator,Val,Package,Mid X,Mid Y,Rotation,Layer"
    And stderr contains ""

  Scenario: --layer TOP filters to top components
    When I run "python -m jbom.cli.main pos --stdout --layer TOP" in the project directory
    Then the command exits with code 0
    And stdout contains "U1"
    And stdout does not contain "J1"

  Scenario: --fabricator jlc uses JLCPCB column headers
    When I run "python -m jbom.cli.main pos --stdout --fabricator jlc" in the project directory
    Then the command exits with code 0
    And stdout contains "Designator,Side,Mid X,Mid Y,Rotation,Package,Comment"
    And stderr contains ""

  Scenario: --jlc shorthand uses JLCPCB column headers
    When I run "python -m jbom.cli.main pos --stdout --jlc" in the project directory
    Then the command exits with code 0
    And stdout contains "Designator,Side,Mid X,Mid Y,Rotation,Package,Comment"
    And stderr contains ""

  Scenario: --fields with --fabricator merges fields correctly
    When I run "python -m jbom.cli.main pos --stdout --fabricator jlc --fields reference,footprint" in the project directory
    Then the command exits with code 0
    And stdout contains "Designator,Footprint,Side,Mid X,Mid Y,Rotation,Package,Comment"
    And stderr contains ""
