# Inventory field semantics
This document defines the current v7 semantics for inventory cell values used by `jbom annotate` and related CSV workflows.

## Two-state value model
Each inventory cell is interpreted as one of two states:

- blank (or schematic `~`)
  - meaning: designer chose not to constrain this attribute
  - annotate behavior: do not write this field to the schematic
  - matching behavior: match any inventory item on this attribute (no filter applied)
- explicit non-blank value
  - meaning: designer-provided requirement/value
  - annotate behavior: write the value to the schematic property
  - matching behavior: must match this value in the inventory

### How `~` is interpreted
KiCad uses `~` as a legacy format-level placeholder for empty fields. jBOM does not
assign custom sentinel semantics to `~`.

- Matching semantics: component-side `~` is treated as blank/no-constraint.
- Annotate semantics: non-blank CSV cells are written literally, including `~`.
- Export/round-trip semantics: `inventory --no-aggregate` preserves literal field values,
  and `annotate` writes user-edited non-blank values as provided.

### Why blank is unambiguous
The design workflow is: create project → audit (B1) → optional repair (B2) → fab.
After B1/B2 the designer has reviewed every blank field and chosen to leave it blank.
That choice is the data. jBOM trusts the workflow — no sentinel is needed to encode
"designer chose generic."

## Annotate write-back rules
`jbom annotate` processes inventory rows by UUID and applies the following rules:

- rows with `Project = "Project"` are treated as header/sub-header sentinel rows and skipped
- data rows with blank cells skip write-back for those fields
- data rows with non-blank cells write values as-is
- if a data cell contains `~`, annotate writes `~` literally
- write-back mapping is direct column-to-property:
  - `Package` column writes `Package` property
  - `Footprint` column writes `Footprint` property
  - no `Package -> Footprint` mapping shim is applied in v7

Required field warnings during annotate:

- required fields are currently `Value` and `Package`
- annotate emits warnings when required fields are blank in data rows

## Triage behavior (`--triage`)
`jbom annotate --triage` reports data rows with required blanks:

- required fields checked: `Value`, `Package`
- rows with `Project = "Project"` are skipped
- output is focused on missing required fields only

## Sub-header row sentinel format
Inline sub-header rows are identified using:

- `Project` column value exactly equal to `"Project"`

This sentinel is used to skip both top-level header-like guide rows and per-category sub-header rows during annotate processing.

## `inventory --no-aggregate` (Scope C)
`jbom inventory --no-aggregate` emits one row per component instance for sparse-fix workflows.

Current schema prefix:

- `Project` (absolute project directory path)
- `UUID`
- `Category`
- `IPN`

Rows are sorted/grouped by `Category`, and each category group is preceded by a sentinel sub-header row.

Current minimal deterministic sub-header markers:

- `Project` -> `Project`
- `UUID` -> `UUID`
- `Category` -> `Category`
- `IPN` -> `(Optional)\nIPN`
- `Value` -> `Value`
- `Package` -> `Package`
- all other columns -> blank

## Scope note
Defaults-driven required/optional/recommended category semantics are intentionally deferred to the `--defaults` design thread. Current annotate triage and no-aggregate sub-header behavior remain minimal and explicit for Issue #127 Scope A/C.
