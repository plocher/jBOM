Feature: BOM exposes sch-vs-pcb divergence as a DRC debugging aid
  As a hardware developer
  I want a BOM run that explicitly shows the values KiCad ERC/DRC would flag
  So that I can spot schematic-vs-PCB drift without leaving the BOM workflow

  # Background:
  # The PCB-first BOM contract makes ``board.footprints`` the canonical row
  # set; the schematic is otherwise invisible to the BOM.  These scenarios
  # exercise the user-facing debugging aid: when the project has *both* a
  # schematic and a PCB and they disagree, the ``s:`` and ``p:`` field
  # namespaces remain available so the user can see the divergence side by
  # side without running ERC/DRC.

  Background:
    Given the generic fabricator is selected

  Scenario: BOM defaults to the PCB footprint, schematic stays visible via s:
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
    And a PCB that contains:
      | Reference | X | Y | Footprint   | Value |
      | R1        | 5 | 3 | R_0603_1608 | 10K   |
    When I run jbom command "bom -f reference,quantity,footprint,s:footprint,p:footprint -o -"
    Then the command should succeed
    And the CSV output has rows where:
      | Reference | Footprint   | S:Footprint | P:Footprint |
      | R1        | R_0603_1608 | R_0805_2012 | R_0603_1608 |

  Scenario: BOM only surfaces s:/p: namespaces when the user explicitly selects them
    # Same divergent project as above, but the default field set does not
    # expose `s:` / `p:` columns -- only `footprint` (PCB-biased) shows up.
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
    And a PCB that contains:
      | Reference | X | Y | Footprint   | Value |
      | R1        | 5 | 3 | R_0603_1608 | 10K   |
    When I run jbom command "bom -o -"
    Then the command should succeed
    And the output should contain "R_0603_1608"
    And the output should not contain "S:Footprint"
    And the output should not contain "P:Footprint"

  Scenario: Divergent values are visible side by side for DRC debugging
    Given a schematic that contains:
      | Reference | Value | Footprint   |
      | R1        | 10K   | R_0805_2012 |
    And a PCB that contains:
      | Reference | X | Y | Footprint   | Value |
      | R1        | 5 | 3 | R_0805_2012 | 9K99  |
    When I run jbom command "bom -f reference,quantity,value,s:value,p:value -o -"
    Then the command should succeed
    And the CSV output has rows where:
      | Reference | Value | S:Value | P:Value |
      | R1        | 9K99  | 10K     | 9K99    |
