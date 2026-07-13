<!-- Hand-curated reference. Candidate for replacement when the jbom config --docs
     generator lands in issue #269. Until then, keep this file honest with the
     Pydantic schemas in src/jbom/config/ and flag divergences as findings. -->

# jBOM configuration reference

This file is the enumerable lookup reference for jBOM's `*.jbom.yaml` profile
format. For the durable axioms governing resolution order, merge semantics, and
the field reference namespace, see
[`../design/configuration-semantics.md`](../design/configuration-semantics.md).
The architectural decisions that formalized this system are
[ADR 0008](../architecture/adr/0008-unified-jbom-config-schema.md) (unified
schema) and
[ADR 0009](../architecture/adr/0009-field-reference-system-and-value-expressions.md)
(field reference system).

## Profile search path

Profiles are searched in this order (highest priority first):

| Priority | Location |
|---|---|
| 1 (highest) | `<cwd>/.jbom/` |
| 2 | `<repo_root>/.jbom/` |
| 3 | Each entry in `$JBOM_PROFILE_PATH` (colon-separated, left-to-right) |
| 4 | `~/.jbom/` |
| 5 | Platform system directory |
| 6 (lowest) | Built-in package config directory |

Named profiles (`<name>.jbom.yaml`) use first-match-wins across this table.
`common.jbom.yaml` is loaded from every level that contains one and
merged cumulatively (lowest-to-highest priority). See
[`../design/configuration-semantics.md`](../design/configuration-semantics.md)
for the full resolution semantics.

## Top-level keys

A `*.jbom.yaml` file may contain the following top-level keys. All are
optional; a file may contain any combination.

| Key | Purpose |
|---|---|
| `id:` | File-level profile identifier (overridable per stanza) |
| `extends:` | Parent profile name to inherit from |
| `fab:` | Fabricator output format (BOM columns, POS columns, Gerbers, etc.) |
| `supplier:` | Supplier API connection settings |
| `defaults:` | Cross-cutting jBOM-wide defaults |
| `presets:` | Named field-set collections |
| `transforms:` | User-defined expression callables |

## `fab:` stanza

Controls fabricator output format. Consumed by `jbom bom`, `jbom pos`,
`jbom fab`, and `jbom gerbers`.

Key fields:

- `id:` — stanza-level profile identifier (overrides file-level `id:`)
- `bom_columns:` — ordered mapping of output column name to field reference or
  expression
- `pos_columns:` — ordered mapping of POS output column name to field reference
- `gerbers.layers:` — list of KiCad layer names to include in Gerber output

### Example: single-fabricator project override

Place in `<project>/.jbom/jlc.jbom.yaml`:

```yaml
extends: jlc
fab:
  bom_columns:
    "Designator": "reference"
    "Quantity":   "jbom:quantity"
    "LCSC":       "jbom:fabricator_part_number"
```

### Example: 4-layer Gerber override

List replacement means the full layer list must be provided:

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

### Example: per-stanza `id:` override

One file serving two CLI flags:

```yaml
# jlc.jbom.yaml
id: jlc

fab:
  id: jlc     # jbom bom --jlc resolves here
  bom_columns:
    ...

supplier:
  id: lcsc    # jbom search --lcsc resolves here
  ...
```

## `supplier:` stanza

Controls supplier API connection and search provider behavior. Consumed by
`jbom search`.

Key fields:

- `id:` — stanza-level profile identifier
- `providers:` — ordered list of search provider names to try
- Connection settings (URL, auth, rate limits) per provider

### Example

```yaml
supplier:
  id: lcsc
  providers:
    - lcsc
```

## `defaults:` stanza

Cross-cutting jBOM-wide defaults. Consumed by `jbom bom`, `jbom fab`,
`jbom search`, and `jbom annotate`. Not tied to any specific fabricator or
supplier.

Key fields:

- `domain_defaults:` — per-category electrical attribute defaults (tolerance,
  voltage, wattage, etc.)
- `enrichment_attributes:` — list of attributes to populate from inventory
- `field_precedence_policy:` — controls how bare (unqualified) field names
  resolve when ambiguous across sources

### Example: org-wide tolerance standard

Place in `$JBOM_PROFILE_PATH/common.jbom.yaml` to apply to every invocation
in that environment:

```yaml
defaults:
  domain_defaults:
    resistor:
      tolerance: "1%"
```

Activate by setting:

```bash
export JBOM_PROFILE_PATH=/shared/jbom
```

### `datasheet_staging:` sub-stanza (jBOM#355)

Governs the always-on staging fetch that rides `jbom search` and `jbom
inventory --supplier`: whenever an Item's Datasheet URL is encountered, it
is fetched into a gitignored `staging/` directory for later human review via
`jbom inventory admit`. See `docs/reference/cli.md` for the full behavioral
write-up (idempotency, `file(1)`-style PDF verification, HTML-impostor
flagging).

Key fields:

- `staging_dir:` — target directory for staged downloads. This is a
  **user-machine binding**: it names a local checkout of the
  SPCoast-inventory repo, which lives at a different path on every
  machine. The shipped `generic.jbom.yaml` deliberately never declares a
  value for it (there is no sensible one to ship). **With no `staging_dir`
  configured, the staging fetch is inert** — a silent no-op, not a warning
  — so nothing changes for any invocation until a user opts in. Set it once
  in your own `~/.jbom/common.jbom.yaml` (see example below) to enable
  staging for every invocation on that machine.
- `max_fetches_per_run:` — maximum number of real network fetches one
  `jbom search` or `jbom inventory --supplier` invocation will attempt.
  Shipped in `generic.jbom.yaml` (currently `20`), since this is a generic,
  non-machine-specific tuning knob.
- `fetch_time_budget_seconds:` — wall-clock budget for real fetches in one
  invocation. Shipped in `generic.jbom.yaml` (currently `30`). Once either
  limit is hit, remaining Datasheet URLs are skipped for that run with a
  one-line stderr summary; nothing else about the command fails.

> **Overriding `max_fetches_per_run`/`fetch_time_budget_seconds`**: because
> the builtin `generic.jbom.yaml` declares concrete values for these two
> keys, a `common.jbom.yaml` override of them is clobbered by the builtin
> (the named-profile chain always wins over the `common.jbom.yaml` chain
> during merge for any key both declare — the same behavior every other
> `generic.jbom.yaml`-declared default has, e.g. `domain_defaults`).
> Override them the same way you would any other `generic.jbom.yaml` value:
> via a project- or user-level `.jbom/generic.jbom.yaml` that shadows the
> builtin file. `staging_dir` has no such caveat, since the builtin never
> declares it.

### Example: enable staging for every invocation on this machine

Place in `~/.jbom/common.jbom.yaml`:

```yaml
defaults:
  datasheet_staging:
    staging_dir: "/Users/you/checkouts/SPCoast-inventory/staging"
```

## `presets:` stanza

Named field-set collections shared across profiles. Consumed wherever preset
names are referenced in `bom_columns` or enrichment rules.

### Example

```yaml
presets:
  basic_bom_fields:
    - "reference"
    - "value"
    - "inv:package"
```

## `transforms:` stanza

User-defined named single-argument callables available in field expressions.
Transforms defined here are available in `bom_columns` values and any other
field expression in the same config chain. See
[`../design/configuration-semantics.md`](../design/configuration-semantics.md#transforms-stanza-semantics)
for the full transform semantics.

Each entry requires:

- `expr:` — a Python expression string; `value` is the implicit single argument
- `doc:` — (recommended) human-readable description

Names must be lowercase snake_case, stable across profiles, and must contain
the word `value` to make the argument role explicit.

### Example

```yaml
transforms:
  strip_kicad_library_prefix_from_value:
    expr: "re.sub(r'^[^:]+:', '', value)"
    doc:  "Remove KiCad library nickname prefix. 'Capacitors_SMD:C_0402' → 'C_0402'"
```

This transform is pre-defined in jBOM's built-in `common.jbom.yaml`; you do
not need to copy it unless you want to override the definition.

## Field reference syntax

Field references appear as values in `bom_columns`, `pos_columns`, and
anywhere an expression is accepted. Two forms:

**Plain field reference** — resolved directly:

```yaml
bom_columns:
  "Designator": "reference"      # unqualified source-data name
  "Package":    "inv:package"    # inventory namespace (canonical form)
  "Footprint":  "pcb:footprint"  # PCB namespace
  "Quantity":   "jbom:quantity"  # jBOM-computed field
```

**Python expression** — evaluated with transform and `re` in scope:

```yaml
bom_columns:
  "Footprint": "strip_kicad_library_prefix_from_value(pcb:footprint)"
  "Label":     "f'{reference} ({inv:manufacturer})'"
  "PN":        "re.sub(r'\\s+', '-', inv:manufacturer_part).upper()"
```

Canonical namespace prefixes per [ADR 0009](../architecture/adr/0009-field-reference-system-and-value-expressions.md):

| Namespace | Source | Replaces |
|---|---|---|
| `sch:<field>` | Schematic symbol properties | legacy `c:` |
| `pcb:<field>` | PCB/placement attributes | legacy `p:` |
| `inv:<field>` | Inventory CSV column values | legacy `i:` |
| `a:<field>` | Annotation workflow values | legacy `a:` (unchanged) |
| `jbom:<field>` | jBOM-computed fields | — |

> **Legacy prefix note**: existing configuration files may still use the older
> single-character prefixes (`i:package`, `p:footprint`, `c:value`, `k:…`).
> These are not conformant with ADR 0009. Both forms are recognized by the
> current loader, but the migration to canonical namespace prefixes is in
> progress and tracked by
> [#282](https://github.com/jplocher/jBOM/issues/282).
> New configuration should use the canonical `inv:`, `pcb:`, `sch:` forms.

## Complete composite example

```yaml
# $REPO_ROOT/.jbom/acme-jlc.jbom.yaml — corporate JLC fork
extends: jlc

transforms:
  normalize_component_value:
    expr: "re.sub(r'\\s+', '', value).upper()"
    doc:  "Normalize value strings: '10 K' → '10K'"

fab:
  bom_columns:
    "Surface Mount": null                                        # delete inherited column
    "Footprint":     "strip_kicad_library_prefix_from_value(pcb:footprint)"
    "Value":         "normalize_component_value(sch:value)"
    "IPN":           "inv:IPN"                                   # plain field ref
    "Status":        "inv:PART_STATUS"                           # custom schematic attribute
```
