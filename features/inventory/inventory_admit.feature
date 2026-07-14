Feature: Datasheet library admission gate (jbom inventory admit)
  As a hardware developer curating the SPCoast-inventory datasheet library
  I want jbom inventory admit to propose a manifest from staged PDFs, let me
  edit it, and then apply it into the library
  So that documents only enter the library through one reviewed gate and a
  published document name is never silently renamed or overwritten

  Background:
    Given a staging directory

  Scenario: propose and apply admit a single new document
    Given an inventory file "library.csv" that contains:
      | IPN      | Category | Value  | Description | Package | Manufacturer | MFGPN  | Datasheet                           | Datasheet Name |
      | IC_LM358 | IC       | LM358D | Dual Op-Amp  | SOIC-8  | TI           | LM358D | https://example.com/docs/lm358.pdf  |                |
    And the staging directory already has a verified PDF staged for "https://example.com/docs/lm358.pdf"
    When I run jbom command "inventory admit --inventory library.csv --manifest manifest.csv"
    Then the command should succeed
    And the file "manifest.csv" contains "ADMIT"
    And the file "manifest.csv" contains "IC_LM358"
    When I run jbom command "inventory admit --apply --manifest manifest.csv -o paste.csv"
    Then the command should succeed
    And the library contains a published document named "IC-TI-LM358D"
    And the file "paste.csv" contains "IC_LM358"
    And the file "paste.csv" contains "IC-TI-LM358D"

  Scenario: apply refuses to rename or overwrite an already-published document
    Given an inventory file "library.csv" that contains:
      | IPN      | Category | Value  | Description | Package | Manufacturer | MFGPN  | Datasheet                           | Datasheet Name |
      | IC_LM358 | IC       | LM358D | Dual Op-Amp  | SOIC-8  | TI           | LM358D | https://example.com/docs/lm358.pdf  |                |
    And the staging directory already has a verified PDF staged for "https://example.com/docs/lm358.pdf"
    And the library already contains "IC-TI-LM358D" published with different content
    When I run jbom command "inventory admit --inventory library.csv --manifest manifest.csv"
    Then the command should succeed
    And the file "manifest.csv" contains "collision"
    When I edit the manifest "manifest.csv" to set Action "ADMIT" for staged file matching "https://example.com/docs/lm358.pdf"
    And I run jbom command "inventory admit --apply --manifest manifest.csv -o paste.csv"
    Then the command should fail
    And the output should contain "Never-rename"
    And the published document "IC-TI-LM358D" still has its original content

  Scenario: apply refuses a path-traversal ProposedName and writes nothing outside the library
    Given an inventory file "library.csv" that contains:
      | IPN      | Category | Value  | Description | Package | Manufacturer | MFGPN  | Datasheet                           | Datasheet Name |
      | IC_LM358 | IC       | LM358D | Dual Op-Amp  | SOIC-8  | TI           | LM358D | https://example.com/docs/lm358.pdf  |                |
    And the staging directory already has a verified PDF staged for "https://example.com/docs/lm358.pdf"
    When I run jbom command "inventory admit --inventory library.csv --manifest manifest.csv"
    Then the command should succeed
    When I edit the manifest "manifest.csv" to set ProposedName "../../evil" for staged file matching "https://example.com/docs/lm358.pdf"
    And I run jbom command "inventory admit --apply --manifest manifest.csv -o paste.csv"
    Then the command should fail
    And the output should contain "ProposedName"
    And nothing named "evil.pdf" exists outside the library directory
    And the library contains exactly 0 published documents

  Scenario: one family document names every member Item
    Given an inventory file "library.csv" that contains:
      | IPN      | Category | Value | Description       | Package | Manufacturer | MFGPN          | Datasheet                                    | Datasheet Name |
      | RES_0331 | RES      | 10K   | Thick Film Resistor | 0603    | Uniroyal     | 0603WAJ0331T5E | https://example.com/docs/0603waj-series.pdf  |                |
      | RES_0332 | RES      | 22K   | Thick Film Resistor | 0603    | Uniroyal     | 0603WAJ0332T5E | https://example.com/docs/0603waj-series.pdf  |                |
      | RES_0333 | RES      | 33K   | Thick Film Resistor | 0603    | Uniroyal     | 0603WAJ0333T5E | https://example.com/docs/0603waj-series.pdf  |                |
    And the staging directory already has a verified PDF staged for "https://example.com/docs/0603waj-series.pdf"
    When I run jbom command "inventory admit --inventory library.csv --manifest manifest.csv"
    Then the command should succeed
    And the file "manifest.csv" contains exactly 1 admit candidate row
    And the file "manifest.csv" contains "RES_0331"
    And the file "manifest.csv" contains "RES_0332"
    And the file "manifest.csv" contains "RES_0333"
    When I run jbom command "inventory admit --apply --manifest manifest.csv -o paste.csv"
    Then the command should succeed
    And the library contains exactly 1 published document
    And the file "paste.csv" contains exactly 3 data rows
    And the file "paste.csv" contains "RES_0331"
    And the file "paste.csv" contains "RES_0332"
    And the file "paste.csv" contains "RES_0333"
