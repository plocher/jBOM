Feature: Audit datasheet document-library hygiene checks
  As a hardware developer curating the shared SPCoast-inventory datasheet
  document library
  I want jbom audit to run read-only hygiene checks against the inventory's
  Datasheet / Datasheet Name columns and the library's datasheets/ directory
  So that I can catch naming, provenance, and file-presence problems before
  they reach CI (jBOM#357)

  # ──────────────────────────────────────────────────────────────
  # Clean pass
  # ──────────────────────────────────────────────────────────────

  Scenario: A fully curated catalog produces no datasheet findings
    Given a datasheet library directory "library" containing:
      | Filename                                    |
      | Resistor-ThickFilm-Yageo-RC0805-series.pdf  |
    And an inventory file "catalog.csv" that contains:
      | RowType | IPN | Category | Manufacturer | Datasheet                       | Datasheet Name                              |
      | ITEM    | R1  | RES      | Yageo        | https://example.com/rc0805.pdf | Resistor-ThickFilm-Yageo-RC0805-series      |
      | ITEM    | R2  | RES      | Yageo        |                                 | Resistor-ThickFilm-Yageo-RC0805-series      |
    When I run "jbom audit catalog.csv --datasheet-library library"
    Then the command should succeed
    And the output should not contain "DATASHEET_"

  # ──────────────────────────────────────────────────────────────
  # Bullet 5: structural backlog (URL populated, Name empty)
  # ──────────────────────────────────────────────────────────────

  Scenario: DATASHEET_BACKLOG emitted for a URL-only row
    Given an inventory file "catalog.csv" that contains:
      | RowType | IPN | Category | Datasheet                    | Datasheet Name |
      | ITEM    | R1  | RES      | https://example.com/rc0805.pdf |                |
    When I run "jbom audit catalog.csv"
    Then the command should succeed
    And the output should contain "DATASHEET_BACKLOG"
    And the output should contain "R1"

  # ──────────────────────────────────────────────────────────────
  # Bullet 1: Name -> URL consistency (one-URL-per-Name provenance)
  # ──────────────────────────────────────────────────────────────

  Scenario: DATASHEET_PROVENANCE_MISSING emitted when no row in the group carries a URL
    Given an inventory file "catalog.csv" that contains:
      | RowType | IPN | Category | Datasheet | Datasheet Name |
      | ITEM    | R1  | RES      |           | shared-doc     |
      | ITEM    | R2  | RES      |           | shared-doc     |
    When I run "jbom audit catalog.csv"
    Then the command should succeed
    And the output should contain "DATASHEET_PROVENANCE_MISSING"
    And the output should contain "shared-doc"

  Scenario: DATASHEET_PROVENANCE_CONFLICT emitted when more than one row carries a URL
    Given an inventory file "catalog.csv" that contains:
      | RowType | IPN | Category | Datasheet          | Datasheet Name |
      | ITEM    | R1  | RES      | https://example.com/a.pdf | shared-doc     |
      | ITEM    | R2  | RES      | https://example.com/b.pdf | shared-doc     |
    When I run "jbom audit catalog.csv"
    Then the command should fail
    And the output should contain "DATASHEET_PROVENANCE_CONFLICT"

  # ──────────────────────────────────────────────────────────────
  # Bullet 2: case-insensitive uniqueness + near-collisions
  # ──────────────────────────────────────────────────────────────

  Scenario: DATASHEET_NAME_CASE_MISMATCH emitted for inconsistent casing of the same name
    Given an inventory file "catalog.csv" that contains:
      | RowType | IPN | Category | Datasheet                  | Datasheet Name |
      | ITEM    | R1  | RES      | https://example.com/a.pdf | Foo-Series     |
      | ITEM    | R2  | RES      |                            | foo-series     |
    When I run "jbom audit catalog.csv"
    Then the command should fail
    And the output should contain "DATASHEET_NAME_CASE_MISMATCH"

  Scenario: DATASHEET_NAME_NEAR_COLLISION emitted for suspiciously similar names
    Given an inventory file "catalog.csv" that contains:
      | RowType | IPN | Category | Datasheet                  | Datasheet Name                              |
      | ITEM    | R1  | RES      | https://example.com/a.pdf | Resistor-ThickFilm-Uniroyal-0603WAJ-series  |
      | ITEM    | R2  | RES      | https://example.com/b.pdf | Resistor-ThickFilm-Univoyal-0603WAJ-series  |
    When I run "jbom audit catalog.csv"
    Then the command should succeed
    And the output should contain "DATASHEET_NAME_NEAR_COLLISION"

  # ──────────────────────────────────────────────────────────────
  # Bullet 3: file presence (requires --datasheet-library)
  # ──────────────────────────────────────────────────────────────

  Scenario: DATASHEET_FILE_MISSING emitted when a curated Name has no library PDF
    Given a datasheet library directory "library" containing:
      | Filename |
    And an inventory file "catalog.csv" that contains:
      | RowType | IPN | Category | Datasheet                  | Datasheet Name |
      | ITEM    | R1  | RES      | https://example.com/a.pdf | missing-doc    |
    When I run "jbom audit catalog.csv --datasheet-library library"
    Then the command should fail
    And the output should contain "DATASHEET_FILE_MISSING"
    And the output should contain "R1"

  Scenario: DATASHEET_ORPHAN_FILE emitted for a library PDF with no referencing Item
    Given a datasheet library directory "library" containing:
      | Filename        |
      | orphan-doc.pdf   |
    And an inventory file "catalog.csv" that contains:
      | RowType | IPN | Category | Datasheet | Datasheet Name |
      | ITEM    | R1  | RES      |           |                |
    When I run "jbom audit catalog.csv --datasheet-library library"
    Then the command should succeed
    And the output should contain "DATASHEET_ORPHAN_FILE"
    And the output should contain "orphan-doc"

  Scenario: File-presence checks do not run without --datasheet-library
    Given an inventory file "catalog.csv" that contains:
      | RowType | IPN | Category | Datasheet                  | Datasheet Name |
      | ITEM    | R1  | RES      | https://example.com/a.pdf | missing-doc    |
    When I run "jbom audit catalog.csv"
    Then the command should succeed
    And the output should not contain "DATASHEET_FILE_MISSING"
    And the output should not contain "DATASHEET_ORPHAN_FILE"

  Scenario: --datasheet-library is rejected in project mode
    Given a schematic that contains:
      | UUID    | Reference | Value | Footprint            | Package | LibID    |
      | uuid-r1 | R1        | 10K   | Resistor_SMD:R_0603  | 0603    | Device:R |
    When I run jbom command "audit . --datasheet-library library"
    Then the command should fail
    And the output should contain "only valid in inventory mode"

  # ──────────────────────────────────────────────────────────────
  # Bullet 4: manufacturer/tech token normalization
  # ──────────────────────────────────────────────────────────────

  Scenario: DATASHEET_TOKEN_MISMATCH emitted for manufacturer spelling drift
    Given an inventory file "catalog.csv" that contains:
      | RowType | IPN | Category | Manufacturer |
      | ITEM    | R1  | RES      | Uniroyal     |
      | ITEM    | R2  | RES      | Uniroyal     |
      | ITEM    | R3  | RES      | UNI-ROYAL    |
    When I run "jbom audit catalog.csv"
    Then the command should succeed
    And the output should contain "DATASHEET_TOKEN_MISMATCH"
    And the output should contain "UNI-ROYAL"
    And the output should contain "Uniroyal"
