# jBOM configuration system

## Overview

jBOM now uses a unified profile format: `*.jbom.yaml`.
A profile can include one or more stanzas:

- `fab:` for BOM/CPL output behavior
- `supplier:` for supplier search/provider behavior
- `defaults:` for enrichment/search defaults
- `presets:` for reusable field presets
- `transforms:` for expression helpers

Legacy built-in profile suffixes (`*.fab.yaml`, `*.supplier.yaml`, `*.defaults.yaml`) are retired.

## Profile resolution

Named profiles are resolved by `load_unified(<name>)` using this search path (highest priority first):

1. `<cwd>/.jbom/`
2. `<repo_root>/.jbom/`
3. `$JBOM_PROFILE_PATH` entries
4. `~/.jbom/`
5. platform system directory
6. built-in package config directory

Two important behaviors:

- Named profile files (`<name>.jbom.yaml`) use **first match wins**.
- `common.jbom.yaml` is loaded from **every** search level and merged cumulatively (low priority first, high priority last).

## Inheritance and merge semantics

Profiles can inherit via:

```yaml
extends: generic
```

Merge semantics are:

- dict + dict: deep merge
- list + list: child replaces parent
- scalar: child replaces parent
- `null`: deletes inherited key

Circular `extends:` chains are rejected.

## field_synonyms mechanism
`field_synonyms` defines canonical field intents and accepted aliases in unified profiles.
At runtime, synonyms are matched case-insensitively and normalized to canonical keys (for example `fab_pn`, `supplier_pn`, `mpn`), while CSV output headers use the configured `display_name`.
This allows CLI field arguments, config field references, schematic/PCB properties, and inventory headers to accept legacy or vendor-specific naming without changing internal semantics.
`fab.field_synonyms` controls fabrication output semantics; `supplier.field_synonyms` controls supplier ID/part-number mapping for supplier workflows.
Profiles should keep only fabricator/supplier-specific rationale inline and defer mechanism details to this section.

## Field reference language

Field references in config expressions and field lists follow ADR 0009:

- `sch:<field>` schematic namespace
- `pcb:<field>` PCB namespace
- `inv:<field>` inventory namespace
- `a:<field>` annotation namespace
- `jbom:<field>` computed namespace

Canonical computed field references are:

- `jbom:quantity`
- `jbom:smd`
- `jbom:fabricator_part_number`

Bare shorthand for computed fields is intentionally avoided in `*.jbom.yaml`.

Expressions are supported, for example:

```yaml
bom_columns:
  "Footprint": "strip_kicad_library_prefix_from_value(pcb:footprint)"
```

## `transforms:` stanza

`transforms:` defines reusable expression callables.
Names should be lowercase snake_case and stable across profiles.

```yaml
transforms:
  strip_kicad_library_prefix_from_value:
    expr: "re.sub(r'^[^:]+:', '', value)"
    doc: "Remove KiCad library nickname prefix from footprint values."
```

This is typically placed in `common.jbom.yaml` so every named profile can use it.

## Per-stanza `id:` overrides

A single profile can expose different IDs per stanza.
For example, one file can provide `fab.id: jlc` and `supplier.id: lcsc`.

```yaml
fab:
  id: jlc
supplier:
  id: lcsc
```

This lets fabrication and supplier selection resolve from one physical file while preserving separate logical IDs.

## Examples

### 1) Single-fabricator project override

`<project>/.jbom/jlc.jbom.yaml`

```yaml
extends: jlc
fab:
  bom_columns:
    "Designator": "reference"
    "Quantity": "jbom:quantity"
    "LCSC": "jbom:fabricator_part_number"
```

### 2) Corporate baseline via `common.jbom.yaml`

`/shared/jbom/common.jbom.yaml`

```yaml
defaults:
  domain_defaults:
    resistor:
      tolerance: "1%"
```

Set:

```bash
export JBOM_PROFILE_PATH=/shared/jbom
```

### 3) Story A: 4-layer gerber override

List replacement means you provide the full layer list:

```yaml
extends: generic
fab:
  gerbers:
    layers:
      - "F.Cu"
      - "In1.Cu"
      - "In2.Cu"
      - "B.Cu"
      - "F.Mask"
      - "B.Mask"
      - "F.Paste"
      - "B.Paste"
      - "F.Silkscreen"
      - "B.Silkscreen"
      - "Edge.Cuts"
```

## Schema reference

Use:

```bash
jbom config --schema
```

This currently prints `FabricatorConfig.model_json_schema()` as a command stub for schema discovery workflows.

## SEE ALSO

- [README.md](../README.md)
- [README.man1.md](README.man1.md)
- [README.man3.md](README.man3.md)
- [docs/dev/architecture/adr/0008-unified-jbom-config-schema.md](dev/architecture/adr/0008-unified-jbom-config-schema.md)
- [docs/dev/architecture/adr/0009-field-reference-system-and-value-expressions.md](dev/architecture/adr/0009-field-reference-system-and-value-expressions.md)
