Feature: Promote supplier export inventory
  As a jBOM user
  I want jbom promote to materialize supplier export CSV files into canonical inventory rows
  So that I can run downstream inventory and BOM workflows with semantic content

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

  Scenario: Promote writes CSV to stdout under the implicit generic context
    Given an inventory file "supplier-export.csv" that contains:
      | JLC Part # | Description |
      | C2286      | 1uF 0603   |
    When I run "jbom promote supplier-export.csv -o -"
    Then the command should succeed
    And the output should contain "SupplierContext"
    And the output should contain "generic"

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

  Scenario: Promote emits canonical inventory schema for JLC exports
    Given an inventory file "jlc-export.csv" that contains:
      | Category    | JLC Part # | MFR Part #         | Footprint | Description                  |
      | Capacitors  | C2286      | CC0603KRX7R9BB104  | 0603      | 0.1uF 50V X7R 10% 0603       |
    When I run "jbom promote jlc-export.csv -o -"
    Then the command should succeed
    And the output should contain "RowType"
    And the output should contain "Category"
    And the output should contain "Value"
    And the output should contain "Package"
    And the output should contain "Tolerance"
    And the output should contain "Capacitance"
    And the output should contain "SupplierContext"

  Scenario: Promote extracts EM semantics from JLC capacitor descriptions
    Given an inventory file "jlc-cap.csv" that contains:
      | Category    | JLC Part # | MFR Part #         | Footprint | Description                  |
      | Capacitors  | C2286      | CC0603KRX7R9BB104  | 0603      | 0.1uF 50V X7R 10% 0603       |
    When I run "jbom promote jlc-cap.csv -o promoted.csv"
    Then the command should succeed
    And the file "promoted.csv" should contain "CAP"
    And the file "promoted.csv" should contain "0603"
    And the file "promoted.csv" should contain "X7R"
    And the file "promoted.csv" should contain "50V"
    And the file "promoted.csv" should contain "10%"
    And the file "promoted.csv" should contain "C2286"
