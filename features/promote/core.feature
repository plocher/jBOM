Feature: Promote supplier export inventory
  As a jBOM user
  I want jbom promote to materialize supplier export CSV files into inventory-compatible output
  So that I can run downstream inventory and BOM workflows deterministically

  Scenario: Promote writes default output file with generic supplier context
    Given an inventory file "supplier-export.csv" that contains:
      | JLC Part # | Description |
      | C2286      | 1uF 0603   |
    When I run "jbom promote supplier-export.csv"
    Then the command should succeed
    And a file named "supplier-export.promoted.csv" should exist
    And the file "supplier-export.promoted.csv" should contain "SupplierContext"
    And the file "supplier-export.promoted.csv" should contain "generic"
    And the file "supplier-export.promoted.csv" contains exactly 1 data rows

  Scenario: Promote honors explicit supplier context in stdout output
    Given an inventory file "supplier-export.csv" that contains:
      | JLC Part # | Description |
      | C2286      | 1uF 0603   |
    When I run "jbom promote supplier-export.csv --supplier lcsc -o -"
    Then the command should succeed
    And the output should contain "SupplierContext"
    And the output should contain "lcsc"

  Scenario: Promote accepts matching supplier-scoped API key syntax
    Given an inventory file "supplier-export.csv" that contains:
      | JLC Part # | Description |
      | C2286      | 1uF 0603   |
    When I run "jbom promote supplier-export.csv --supplier lcsc --api-key lcsc=KEY123 -o -"
    Then the command should succeed
    And the output should contain "SupplierContext"
    And the output should contain "lcsc"

  Scenario: Promote rejects supplier-scoped API key for a different supplier context
    Given an inventory file "supplier-export.csv" that contains:
      | JLC Part # | Description |
      | C2286      | 1uF 0603   |
    When I run "jbom promote supplier-export.csv --supplier lcsc --api-key mouser=KEY999"
    Then the command should fail
    And the output should contain "not present in --supplier arguments"

  Scenario: Promote fails fast when --jlc overlaps with --supplier
    Given an inventory file "supplier-export.csv" that contains:
      | JLC Part # | Description |
      | C2286      | 1uF 0603   |
    When I run "jbom promote supplier-export.csv --jlc --supplier lcsc"
    Then the command should fail
    And the output should contain "tracked by #324"

  Scenario: Promote fails fast when multiple supplier contexts are requested
    Given an inventory file "supplier-export.csv" that contains:
      | JLC Part # | Description |
      | C2286      | 1uF 0603   |
    When I run "jbom promote supplier-export.csv --supplier lcsc --supplier mouser"
    Then the command should fail
    And the output should contain "tracked by #324"
