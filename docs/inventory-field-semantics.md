# Inventory field semantics
This document defines the current v7 semantics for inventory cell values used by `jbom annotate` and related CSV workflows.

## Three-state value model
Each inventory cell is interpreted as one of three states:

- blank (`""`)
  - meaning: not yet determined by the designer
  - annotate behavior: do not write this field to the schematic
- `~`
  - meaning: explicit don't-care decision by the designer
  - annotate behavior: write literal `~` to the schematic property
- explicit non-blank value
  - meaning: designer-provided requirement/value
  - annotate behavior: write the value to the schematic property

## Annotate write-back rules
`jbom annotate` processes inventory rows by UUID and applies the following rules:

- rows with `Project = "Project"` are treated as header/sub-header sentinel rows and skipped
- data rows with blank cells skip write-back for those fields
- data rows with non-blank cells write values as-is (including `~`)
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

## Scope note
Defaults-driven required/optional/recommended category semantics are intentionally deferred to the `--defaults` design thread. Current triage/reporting behavior remains minimal and explicit for Issue #127 Scope A.
