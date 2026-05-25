# jBOM configuration semantics

jBOM's configuration system is built around a unified `*.jbom.yaml` profile
format. This document records the invariants that govern how profiles are
discovered, composed, and interpreted — the durable axioms that future changes
must honor. For the enumerable stanza reference, see
[`../reference/configuration.md`](../reference/configuration.md). The
architectural decisions that formalized this system are
[ADR 0008](../architecture/adr/0008-unified-jbom-config-schema.md) (unified
schema) and
[ADR 0009](../architecture/adr/0009-field-reference-system-and-value-expressions.md)
(field reference system).

## Profile resolution order

Named profiles are located by `load_unified(<name>)` using a fixed search path,
listed here from highest priority to lowest:

1. `<cwd>/.jbom/`
2. `<repo_root>/.jbom/`
3. Each entry in `$JBOM_PROFILE_PATH` (colon-separated, left-to-right)
4. `~/.jbom/`
5. Platform system directory
6. Built-in package config directory

Two distinct behaviors govern this search, and their asymmetry is a design
invariant:

**Named profile files** (`<name>.jbom.yaml`) resolve on **first match wins**.
The file found at the highest-priority level is loaded in full; lower-priority
levels are not consulted for that name. A `jlc.jbom.yaml` placed in
`<cwd>/.jbom/` completely replaces the built-in `jlc.jbom.yaml` for that
working directory — unless the project file declares `extends: jlc` explicitly
to inherit from it.

**`common.jbom.yaml`** behaves differently. Every search level that contains a
`common.jbom.yaml` contributes: all such files are deep-merged cumulatively,
from lowest priority (built-in) up to highest (cwd). The merged result forms an
ambient base that any named profile is then applied on top of. This
cumulative-for-common, first-match-for-named asymmetry is intentional and
must be preserved when modifying the loader.

The `generic.jbom.yaml` profile serves as the implicit fallback when no named
profile flag is given to a command. It is resolved like any other named profile
(first-match-wins), so a repo-level `<repo_root>/.jbom/generic.jbom.yaml`
overrides the built-in for that repo's no-flag invocations without affecting
`--jlc` or any other explicitly named profile.

## Inheritance and merge semantics

A profile may inherit from another by declaring:

```yaml
extends: <parent-profile-name>
```

The parent profile is resolved through the same search path and fully merged
before the child's stanzas are applied. The merge rules are applied recursively
per stanza:

- **Dict + dict**: deep merge. Child keys override parent keys; omitted parent
  keys are inherited unchanged at every nesting level.
- **List + list**: child **replaces** the parent list entirely. There is no
  list-append syntax in v1; providing a list in the child means providing the
  complete replacement, not a delta.
- **Scalar**: child value replaces parent value.
- **`null` value**: the key is **deleted** from the merged result. `null` is
  the only deletion mechanism; set a key to `null` to remove an inherited entry
  rather than setting it to an empty string or zero.

Circular `extends:` chains are unconditionally rejected at load time. There is
no partial loading on circular detection; the entire config load fails with an
error.

These semantics extend the `extends:` deep-merge machinery already present in
`defaults.py` to cover all stanza types uniformly. The unified loader reuses
the same merge engine rather than introducing a second one.

## Field reference namespace

All field references in jBOM configuration follow the
`namespace:field` syntax established by
[ADR 0009](../architecture/adr/0009-field-reference-system-and-value-expressions.md).
The colon (`:`) separates namespace from field name and means exactly one thing
throughout the config language: namespace separator.

Four source namespaces are defined:

- `sch:<field>` — schematic properties from the `.kicad_sch` file. Replaces
  the legacy `c:` single-character prefix.
- `pcb:<field>` — placement attributes from the `.kicad_pcb` file. Replaces
  the legacy `p:` prefix.
- `inv:<field>` — column values from the matched inventory file. Replaces the
  legacy `i:` prefix.
- `a:<field>` — values written by the `jbom annotate` workflow. Also accepts
  `ann:` and `annotation:` as aliases.

Source fields are discovered at runtime from the actual data. jBOM cannot
enumerate `sch:*` or `inv:*` ahead of time because their vocabulary depends on
what the schematic properties and inventory column headers contain in a
particular project.

jBOM-computed fields use the `jbom:` prefix. The currently registered computed
fields are `jbom:quantity`, `jbom:fabricator_part_number`, and `jbom:smd`. No
bare shorthand is provided — the `jbom:` prefix is mandatory and unambiguous
even when an inventory CSV column happens to share the name `quantity`.

Unqualified bare names (such as `value`, `reference`, `footprint`) resolve to
the source that contains that name. When the same bare name appears in multiple
sources simultaneously, `field_precedence_policy` in `common.jbom.yaml`
determines which source wins. This policy is ambient — it is loaded from the
`common.jbom.yaml` chain and applies regardless of which named profile is
active.

> **Legacy prefix migration**: Configuration examples using the older
> single-character prefixes (`i:`, `p:`, `c:`, `k:`) are not conformant with
> ADR 0009. The migration to canonical namespace prefixes (`inv:`, `pcb:`,
> `sch:`) is tracked by
> [#282](https://github.com/jplocher/jBOM/issues/282).
> The reference doc at
> [`../reference/configuration.md`](../reference/configuration.md)
> notes both forms and the migration status.

## Per-stanza `id:` overrides

A `.jbom.yaml` file may declare a file-level `id:` that applies to all its
stanzas by default. Individual stanzas may override this with their own `id:`:

```yaml
# jlc.jbom.yaml
id: jlc        # file-level default; jbom bom --jlc resolves fab: here

fab:
  ...          # inherits id: jlc

supplier:
  id: lcsc     # overrides for this stanza; jbom search --lcsc resolves here
  ...
```

Both `--jlc` and `--lcsc` resolve to the same physical file; each jBOM command
consumes only the stanza relevant to its function. The CLI flag surface is
driven by stanza presence and effective `id:`: a command only exposes a
`--<id>` flag for profiles that contain at least one stanza that command
consumes, using that stanza's effective `id:` (see
[ADR 0008 D3](../architecture/adr/0008-unified-jbom-config-schema.md#d3-one-cli-flag-per-named-profile--no-dimension-qualifiers-in-v1)
for the command-to-stanza mapping).

This mechanism allows a single file to provide both a fabricator profile and a
supplier profile under logically distinct names, which is the common case for
fabricator/supplier pairs (such as JLCPCB and LCSC).

## `transforms:` stanza semantics

Any `.jbom.yaml` file may define reusable named single-argument transforms in a
top-level `transforms:` stanza:

```yaml
transforms:
  strip_kicad_library_prefix_from_value:
    expr: "re.sub(r'^[^:]+:', '', value)"
    doc:  "Remove KiCad library nickname prefix from footprint values."
```

Each transform is a single-argument callable where the implicit argument is
named `value`. By convention, the word `value` must appear in the transform
name to make the argument role explicit to anyone reading a config file without
looking up the transform definition. `expr` is a Python expression evaluated
via `ast.parse(mode='eval')` in a restricted namespace that provides `re` and
all other loaded transforms; statements, loops, imports, and side effects are
rejected at the grammar level. Malformed expressions are caught at config load
time, not deferred to BOM generation time.

A defined transform is invoked in `bom_columns` values or any other field
expression by calling it with the field reference as its argument:

```yaml
fab:
  bom_columns:
    "Footprint": "strip_kicad_library_prefix_from_value(pcb:footprint)"
```

Transforms follow the same inheritance rules as all other config content:
`extends:` chains propagate parent transforms to child profiles, and
`common.jbom.yaml` files at each search-path level contribute ambient
transforms available to all configs at that level and below. jBOM ships a
built-in set of transforms (including `strip_kicad_library_prefix_from_value`)
via the built-in `common.jbom.yaml`. A user definition that shadows a built-in
name is valid and intentional override is supported; jBOM emits a
`Diagnostic(severity=NOTICE)` through the standard diagnostic reporting
infrastructure so accidental shadows surface through normal output. Two
transforms sharing the same name within a single file are a load-time
`Diagnostic(severity=ERROR)` that aborts loading.

The `transforms:` stanza is most naturally placed in `common.jbom.yaml` so
every named profile in the search path can use the defined transforms without
per-profile repetition.

## `common.jbom.yaml` — ambient cumulative loading

`common.jbom.yaml` is the ambient configuration layer. It provides org-level,
repo-level, and user-level settings that apply across all profiles regardless
of which named profile is selected. It is not a named profile and cannot be
loaded with a `--common` CLI flag.

The core invariant: all `common.jbom.yaml` files found in the search path are
merged cumulatively, from lowest priority (built-in) to highest priority (cwd).
A corporate `common.jbom.yaml` in `$JBOM_PROFILE_PATH` and a project
`common.jbom.yaml` in `<cwd>/.jbom/` both take effect; the project-level
file overrides only the keys it specifies, leaving the rest of the corporate
baseline intact. This design makes org-wide standards expressible without
per-project configuration and without touching the named profile at all.

Content appropriate for `common.jbom.yaml` includes shared `transforms:`,
`field_precedence_policy` (controlling how bare field names resolve when
ambiguous), org-wide `defaults:` (electrical component tolerance floors,
enrichment classification rules), and any setting that should apply uniformly
regardless of which fabricator or supplier profile is selected.

For the full resolution diagram showing how `common.jbom.yaml` layers interact
with named profiles and `extends:` chains, see
[ADR 0008 D5](../architecture/adr/0008-unified-jbom-config-schema.md#d5-commonjbomyaml--ambient-defaults-at-each-search-path-level).
