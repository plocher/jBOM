# ADR 0008: Unified jBOM Configuration Schema
Date: 2026-05-11
Status: Proposed
Related: #250, #251, ADR 0007

## Context

jBOM currently has four separate configuration file types living in four separate
subdirectories under `src/jbom/config/`:

| Type | Directory | File pattern | Python loader |
|---|---|---|---|
| Fabricator | `fabricators/` | `<name>.fab.yaml` | `config/fabricators.py` |
| Supplier | `suppliers/` | `<name>.supplier.yaml` | `config/suppliers.py` |
| Defaults | `defaults/` | `<name>.defaults.yaml` | `config/defaults.py` |
| Presets | `presets/` | *(no type suffix)* | *(no dedicated loader)* |

Each type has its own loader, its own schema, and its own inheritance semantics.
`defaults.py` implements `extends:` deep-merge (working well). `fabricators.py`
documents a `based_on:` key but does not implement it. `suppliers.py` has no
inheritance at all. `presets/common.yaml` has no suffix convention and no loader.

The fragmentation creates real user friction:
- A user customizing JLCPCB output must maintain three files (`jlc.fab.yaml`,
  `lcsc.supplier.yaml`, `generic.defaults.yaml`) to express a single coherent profile.
- Inheritance is only available for `*.defaults.yaml`; fabricator and supplier
  overrides require full-file copies.
- Extending with org-wide or project-specific settings has no consistent mechanism.
- The `profile_search.py` unified search path is good but is called three times
  with three different suffixes, producing three separate resolution chains.
- There is no way to express "this value is mandatory and cannot be overridden
  by a lower-priority config."

Issue #250 identifies the naming inconsistency. Issue #251 calls for a unified
schema. This ADR records the design decision for both.

## Decision Drivers

- **Simplicity for the common case.** `jbom bom --jlc` should work with one
  config file that expresses everything JLC-specific.
- **Partial override without full-file copy.** A user who wants to change one
  column in JLC's BOM format should not have to copy and maintain the entire
  `jlc.fab.yaml`.
- **Org/team standards that compose with any fabricator.** Tolerance floors,
  mandatory columns, and search defaults must be expressible at an org level
  and apply regardless of which fabricator flag the user chooses.
- **Consistent semantics.** One inheritance model, one merge strategy, one
  search path mechanism — not one per config type.
- **Command-scoped consumption.** Each `jbom <cmd>` knows which stanzas it
  needs; config files may contain multiple stanzas but each command only
  consumes what is relevant.
- **Clean break.** Nothing has shipped externally; legacy file types and
  prefixes are retired atomically with no shim and no major-version requirement.
- **Atomic delivery.** The loader, built-in file migration, and legacy file
  removal land in a single feature branch — no intermediate broken state.

## User Stories

These are the concrete scenarios that drove the design. Each one is validated
against the decision below.

**Story A — Project 4-layer override**
A board has inner copper layers. The user wants JLC's full profile plus
`gerbers.layers` overridden with the 4-layer set. Copying and maintaining the
full `jlc.jbom.yaml` to change one list is unacceptable.

**Story B — Org-wide tolerance standard**
An org mandates 0.1% resistors. Every project under `$JBOM_PROFILE_PATH`
inherits that floor regardless of which fabricator flag the user chooses.
No per-project configuration should be required.

**Story C — Personal extra column**
A developer always wants an `IPN` column in their BOMs. Their `~/.jbom/`
config adds the column without duplicating the rest of the fabricator profile.

**Story D — Single-file fabricator profile**
One `jlc.jbom.yaml` expresses the JLC column format, LCSC as the preferred
supplier, and JLC-appropriate parametric search defaults — without maintaining
three separate files.

**Story E — Corporate fork of JLC**
`acme-jlc.jbom.yaml` extends `jlc`, overriding only the delta fields. New
hires get the team's format automatically by running `jbom bom --acme-jlc`
from the checked-in repo root.

**Story F — Column deletion**
A team's JLC profile should be `jlc` minus the `Surface Mount` column plus
an `IPN` column. Without a deletion mechanism, the user must copy and maintain
the full `bom_columns` dict.

**Story G — CI / headless determinism**
`jbom bom --jlc` in CI must produce identical output regardless of the
developer's `~/.jbom/` contents. Explicit flags (`--jlc`) select specific
named configs; the `generic` profile is the implicit fallback when no flag
is given. CI tests that probe edge cases use explicit flags; tests of generic
behavior rely on the implied `generic` profile.

## Options Considered

### Option 1 — Status quo: four separate file types (rejected)
Continue with `*.fab.yaml`, `*.supplier.yaml`, `*.defaults.yaml`, `*.yaml`
(presets). Low migration cost. Does not address any of the user stories;
partial-override and cross-stanza composition remain impossible.

### Option 2 — Unified format, dimension flags for stanza selection (rejected)
Introduce `--fabricator NAME`, `--defaults NAME`, `--supplier NAME` as
explicit dimension-selecting CLI flags. Each flag extracts only its named
stanza from the loaded file. Conflicting stanzas from multiple loaded files
are resolved by flag precedence.

Rejected because: the combinatorics are complex (a 3-file × 3-stanza matrix
with non-obvious precedence rules); the cross-cutting use case (org tolerance
floor) requires an additional flag every time; the `common.jbom.yaml` mechanism
(D5) addresses the same use cases with zero new flags.

### Option 3 — Unified format, no multi-stanza files (rejected)
Allow `.jbom.yaml` suffix but require each file to contain exactly one stanza.
Renames `jlc.fab.yaml` to `jlc.jbom.yaml` with `fab:` stanza, etc. Eliminates
stanza ambiguity.

Rejected because: it does not address Story D (single composite profile per
fabricator) and does not simplify anything over the current 4-type system
except the naming convention.

### Option 4 — Unified format, command-scoped stanza selection (accepted — this ADR)
Described in Decision Details below (D1–D8).

## Decision

Adopt the unified `*.jbom.yaml` schema as described in D1–D8.

Key properties of the accepted design:
- One file suffix, one inheritance model, one search path, one merge engine.
- Command provides stanza scope; no dimension-specific CLI flags in v1.
- `common.jbom.yaml` per search-path level provides composable ambient defaults.
- `policy.jbom.yaml` per search-path level provides mandate enforcement (deferred).
- `extends:` + deep-merge + list-replace + `null`-delete enables partial override.
- `generic.jbom.yaml` consolidates all current generic config files.
- Legacy file types and prefixes retired atomically with the new loader — no shim.

### Decision Details

### D1. Unified `*.jbom.yaml` file format

All configuration files use the `.jbom.yaml` suffix. A file may contain one
or more top-level stanzas:

```yaml
fab:        # Fabricator output format (bom columns, pos columns, gerbers, etc.)
supplier:   # Supplier API connection (URL, auth, rate limits, search providers)
defaults:   # General jBOM-wide defaults (electrical defaults, search config,
            # enrichment attributes, component ID policy, field precedence)
presets:    # Named field-set collections (global, shared across contexts)
```

A file that contains only a `fab:` stanza is a pure fabricator profile. A file
that contains all four stanzas is a complete composite profile. Either is valid.

The `defaults:` stanza is the general cross-cutting stanza for settings that
are not tied to any specific fabricator or supplier — electrical attribute
defaults, parametric search configuration, enrichment classification, and
component ID field policies.

### D2. Command-scoped stanza consumption

Each `jbom <cmd>` consumes only the stanzas relevant to its function:

| Command | Stanzas consumed |
|---|---|
| `bom` | `fab:`, `defaults:` |
| `pos` | `fab:` |
| `fab` | `fab:`, `defaults:` |
| `gerbers` | `fab:` (gerbers section) |
| `search` | `supplier:`, `defaults:` |
| `annotate` | `defaults:` |

A unified file loaded for `jbom bom --jlc` will have its `supplier:` stanza
loaded but not consumed. The stanza is inert for that command; it does not
produce errors or warnings.

### D3. One CLI flag per named profile — no dimension qualifiers in v1

The CLI accepts `--<configname>` where `<configname>` is derived from the
profile's `id` field (same auto-generation as today). A single flag loads
the entire named `.jbom.yaml` file; the command determines which stanzas
it uses.

```
jbom bom --jlc          # loads jlc.jbom.yaml; bom command uses fab: stanza
jbom search --lcsc      # loads jlc.jbom.yaml; search command uses supplier: stanza
jbom bom                # no flag → generic.jbom.yaml (same as today's --generic)
```

**Per-stanza `id:` override**: a file-level `id:` is the default for all
stanzas, but each stanza may declare its own `id:` to control which CLI flag
reaches it for that command type:

```yaml
# jlc.jbom.yaml
id: jlc          # file-level default

fab:             # inherits id: jlc  →  jbom bom --jlc resolves here
  ...

supplier:
  id: lcsc       # overrides for this stanza  →  jbom search --lcsc resolves here
  ...
```

Both `--jlc` and `--lcsc` resolve to the same file; each command consumes
its own stanza. The file is named for its primary purpose (the fabricator);
the supplier stanza self-identifies as `lcsc` because that is the supplier
name users naturally think in.

For fabricators without a tightly coupled supplier (e.g. PCBWay), the
`supplier:` stanza may be absent. `jbom search --pcbway` searches using the
ordered `fab.suppliers:` list from the PCBWay config, falling back to the
ambient supplier config from the `common.jbom.yaml` chain.

Dimension-specific flags (`--fabricator`, `--defaults`, `--supplier`) are not
introduced in v1. The `common.jbom.yaml` ambient mechanism (D5) addresses the
cross-cutting composition use case without needing explicit dimension flags.

Flag auto-generation per command: a command only exposes `--<id>` for profiles
whose `.jbom.yaml` contains at least one stanza that command consumes, using
the effective `id:` for that stanza.

### D4. Explicit `extends:` inheritance with consistent merge semantics

Inheritance is always explicit via the top-level `extends:` key, which names
a profile to inherit from:

```yaml
# acme-jlc.jbom.yaml
extends: jlc

fab:
  bom_columns:
    "IPN": "internal_ipn"    # additive: adds this column
    "Surface Mount": null    # deletion: removes inherited column
```

Merge semantics (applied recursively per stanza, consistent with `defaults.py`):

- **Dicts**: deep-merged. Child keys override parent keys; omitted parent keys
  are inherited unchanged.
- **Lists**: child replaces parent entirely. To inherit a list you must include
  it explicitly. There is no list-append syntax in v1.
- **Scalars**: child replaces parent.
- **`null` value**: deletes the key from the merged result. This is the deletion
  mechanism for Story F.

`extends:` applies at the file level: the entire parent file is loaded and
merged before the child's stanzas are applied. Circular `extends:` chains are
an error.

### D5. `common.jbom.yaml` — ambient defaults at each search path level

A file named `common.jbom.yaml` found at any search path level is automatically
deep-merged as ambient defaults at that level. It is not a named profile and
cannot be selected with `--common`.

The effective config resolution for `jbom bom --jlc` (named profile) is:

```
policy.jbom.yaml         (all levels, mandates — applied post-resolution; see D6)
─────────────────────────────────────────────────────────
jlc.jbom.yaml            (first found in search path — named selection)
─────────────────────────────────────────────────────────
common.jbom.yaml         (cwd/.jbom/   — if present)
common.jbom.yaml         (repo/.jbom/  — if present)
common.jbom.yaml         ($JBOM_PROFILE_PATH — if present)
common.jbom.yaml         (~/.jbom/     — if present)
common.jbom.yaml         (system dir   — if present)
```

The effective config resolution for `jbom bom` (no flag) is:

```
policy.jbom.yaml         (all levels, mandates — applied post-resolution; see D6)
─────────────────────────────────────────────────────────
generic.jbom.yaml        (first found in search path — implicit fallback)
─────────────────────────────────────────────────────────
common.jbom.yaml         (cwd/.jbom/   — if present)
common.jbom.yaml         (repo/.jbom/  — if present)
common.jbom.yaml         ($JBOM_PROFILE_PATH — if present)
common.jbom.yaml         (~/.jbom/     — if present)
common.jbom.yaml         (system dir   — if present)
─────────────────────────────────────────────────────────
generic.jbom.yaml        (built-in package — floor, always present)
```

Note that in the no-flag case `generic.jbom.yaml` is searched like any other named
profile (first match in search path wins), so a `generic.jbom.yaml` in `$REPO_ROOT/.jbom/`
overrides the built-in generic for that repo's no-flag invocations.

All `common.jbom.yaml` files are deep-merged in search-path priority order
(cwd highest, built-in lowest). The named profile (`jlc.jbom.yaml`) is then
applied on top of the merged common base.

`common.jbom.yaml` files in the search path are cumulative; named profile files
use first-match-wins (same as today's `profile_search.py` behavior for named
configs). This means a `jlc.jbom.yaml` in `cwd/.jbom/` fully replaces the
built-in `jlc.jbom.yaml` unless `extends:` is used.

The existing `presets/common.yaml` content migrates into a `presets:` stanza
in `generic.jbom.yaml` (or into a built-in `common.jbom.yaml`).

This mechanism addresses Stories B and C without any new CLI flags: org-wide
tolerance floors go in `$JBOM_PROFILE_PATH/common.jbom.yaml`; they activate
for every command, regardless of which named profile is selected.

### D6. `policy.jbom.yaml` — mandatory overrides (v1: reserved, enforcement deferred)

A file named `policy.jbom.yaml` found at any search path level declares
mandatory values. Policy is applied **after** the full user-config resolution
(common chain + named selection + extends chain) and enforces values downward
from the level at which the policy file was found.

A `policy.jbom.yaml` at `$JBOM_PROFILE_PATH` overrides anything in `~/.jbom/`
or `cwd/.jbom/`. A `policy.jbom.yaml` at `~/.jbom/` overrides only `cwd/.jbom/`.

This is the mechanism for Story B's "1% tolerance floor that a user's personal
config cannot override."

The `!final` YAML tag is reserved for per-value mandate marking at the point
of declaration (analogous to CSS `!important`). YAML's `!` introduces a type
tag, so this requires a custom tag registered as `!final`:

```yaml
# $JBOM_PROFILE_PATH/policy.jbom.yaml
defaults:
  domain_defaults:
    resistor:
      tolerance: !final "1%"
```

**v1 scope**: The `policy.jbom.yaml` filename is reserved and must not be used
for other purposes. The enforcement mechanism (post-resolution overlay and
`!final` tag processing) is deferred to a follow-on issue. v1 loads and ignores
`policy.jbom.yaml` with a logged warning so users who place such a file in the
search path are informed the feature is not yet active.

### D7. `generic.jbom.yaml` — fallback for the no-flag case only

The built-in `generic.jbom.yaml` consolidates the content of all current
built-in generic config files:
- `config/fabricators/generic.fab.yaml` → `fab:` stanza
- `config/defaults/generic.defaults.yaml` → `defaults:` stanza
- `config/suppliers/generic.supplier.yaml` → `supplier:` stanza
- `config/presets/common.yaml` → `presets:` stanza

`generic.jbom.yaml` is loaded **only** in the no-flag case (`jbom bom` with
no named profile). Selecting a named profile (`jbom bom --jlc`) disengages
implicit generic inheritance entirely: you get exactly what the named profile
defines, plus any `extends:` chain it declares explicitly, plus the
`common.jbom.yaml` ambient layer.

If a named profile wants generic content, it must say so explicitly:
```yaml
# jlc.jbom.yaml
extends: generic   # explicit — not implied
```

This preserves the principle of least astonishment: specifying a named
profile is a declaration of intent; silently mixing in generic defaults
would violate that.

The built-in `generic.jbom.yaml` is intentionally minimal — it provides
a reproducible, testable foundation rather than production-quality defaults.
Orgs that want a customized "no-flag" default across a repository can place
a `generic.jbom.yaml` in `$REPO_ROOT/.jbom/`. This file is found by
`profile_search.py` at the repo-root level and becomes the effective floor
for any `jbom` invocation in that repo that specifies no named profile —
without affecting `--jlc` or any other named profile unless those profiles
explicitly `extends: generic`.

### D8. Migration — atomic, no shim

Nothing has shipped externally. The legacy file types (`*.fab.yaml`,
`*.supplier.yaml`, `*.defaults.yaml`) and the legacy field prefix notation
(`c:`, `p:`, `i:`, `k:`) are retired in the same commit set that introduces
the new loader. There is no intermediate state with the old files and the new
loader coexisting, and no deprecation shim.

Built-in config files are converted to `.jbom.yaml` format and the legacy
subdirectories (`fabricators/`, `suppliers/`, `defaults/`, `presets/`) are
removed as part of this feature branch — not deferred to a follow-on.

`pyproject.toml` `[tool.hatch.build.targets.wheel] include` patterns are
updated to `*.jbom.yaml` in the same commit.

## Consequences

### Positive
- Stories A–G are all addressable within this design.
- Config system complexity drops: one loader, one merge engine, one search path call.
- Org-level standards (`$JBOM_PROFILE_PATH/common.jbom.yaml`) activate for every
  command with no per-project or per-user configuration.
- `defaults.py`'s existing `_deep_merge` and `extends:` machinery is reused and
  extended rather than replaced.
- The file naming convention is now unambiguous and self-documenting.
- Flag generation per command is now driven by stanza presence, not file suffix.

### Negative / Tradeoffs
- Migration work: all built-in config files must be converted to `.jbom.yaml`.
- `pyproject.toml` package-data declarations must be updated (affects PCM
  archive build per ADR 0007).
- The atomic migration (no shim) means the entire built-in config file set
  must be converted in one branch — no cherry-picking partial migrations.
- `common.jbom.yaml` files are merged cumulatively (not first-match-wins), which
  is a different behavior from named profile files. This asymmetry must be
  clearly documented.
- List-replace semantics (not list-append) means Story A's 4-layer override
  requires specifying all 9 layers, not just the 2 new ones. Acceptable for v1;
  a `_append:` list modifier could be added later.

### Risks and Mitigations
- **Risk**: Circular `extends:` chains produce infinite loops.
  **Mitigation**: track seen profile names during resolution; raise `ValueError`
  on the second visit to the same name.
- **Risk**: `null`-delete semantics surprise users who set a value to `null`
  intending "no value" rather than "delete inherited value."
  **Mitigation**: document prominently; consider a `_unset:` explicit keyword
  in a future revision.
- **Risk**: `policy.jbom.yaml` reserved name collision with existing user files.
  **Mitigation**: The loader rejects `policy.jbom.yaml` as a selectable named
  profile and logs an error if a user attempts to load it with `--policy`.

## Deferred Items

The following are explicitly out of scope for the initial implementation but
are recorded here to prevent loss:

1. **`policy.jbom.yaml` enforcement** — the file is reserved; enforcement logic
   (post-resolution overlay, per-level downward scope) is a follow-on issue.
2. **`!final` tag processing** — reserved tag name; parser registration and
   merge-engine enforcement are deferred with policy enforcement.
3. **Dimension flags (`--fabricator`, `--defaults`, `--supplier`)** — may be
   introduced in v2 as power-user escape hatches once the common/policy
   mechanism is validated in practice.
4. **List-append modifier (`_append:`)** — would allow additive layer overrides
   for lists (e.g., Story A with only the new layers, not the full list).
5. **`jbom config show --jlc`** — diagnostic command to print the fully-resolved
   effective config (Story K). Requires the merge engine to be serializable
   back to YAML.
6. **`defaults.inventory` path** — the `defaults:` stanza could declare a default
   inventory file path (or list of paths), enabling a `$REPO_ROOT/.jbom/common.jbom.yaml`
   to specify a corporate or project-family inventory without requiring a
   `--inventory` CLI flag on every invocation. Follows the same search-path layering
   as all other `defaults:` content. Deferred to a follow-on issue.
7. **`import X as Y`** — stanza-level renaming for aliasing an imported profile
   under a local name. Deferred until concrete use cases emerge.

## Implementation Phases

**Phase 1 (this feature branch, issues #250 + #251) — atomic delivery**
- Land this ADR and ADR 0009.
- Implement the unified loader in `src/jbom/config/unified.py`:
  - `load_unified(name, cwd)` → resolves the full stack (common chain + named
    profile + extends chain + per-stanza id resolution) and returns a raw merged dict.
  - Stanza extractors: `fab_config_from_unified(dict)`, `supplier_config_from_unified(dict)`,
    `defaults_config_from_unified(dict)`.
  - Dispatch to `FabricatorConfig.from_yaml_dict`, `SupplierConfig.from_yaml_dict`,
    `DefaultsConfig.from_yaml_dict` with the extracted stanza dict.
- Update `profile_search.py` to recognize `*.jbom.yaml` only; remove legacy suffix handling.
- Migrate all built-in config files to `.jbom.yaml` format (including
  `generic.jbom.yaml` consolidation). Remove legacy subdirectories
  (`fabricators/`, `suppliers/`, `defaults/`, `presets/`) and legacy files in the same commit.
- Update `pyproject.toml` package-data for `*.jbom.yaml`; remove legacy patterns.
- Wire the new loader into `fabricators.py`, `suppliers.py`, `defaults.py` as
  the sole loading path (no legacy shim).
- Update `docs/README.configuration.md` to document the new convention (#250
  acceptance criteria).
- Unit tests for: `_deep_merge`, `null`-delete, `extends:` chain resolution,
  circular-extends detection, `common.jbom.yaml` cumulative merge, per-stanza id.
- Functional tests for Stories A–E (Stories F, G already covered by existing
  CI design).

**Phase 2 (future issue)**
- `policy.jbom.yaml` enforcement + `!final` tag.
- `jbom config show` diagnostic command.
- `defaults.inventory` path configuration.

## References
- Issue #250: naming convention normalization
- Issue #251: unified schema design (this ADR records the outcome of that design work)
- `src/jbom/config/profile_search.py`: existing search path implementation
- `src/jbom/config/defaults.py`: existing `extends:` deep-merge (reused in Phase 1)
- `src/jbom/config/fabricators.py`: `FabricatorConfig.from_yaml_dict` (reused)
- `src/jbom/config/suppliers.py`: `SupplierConfig.from_yaml_dict` (reused)
- ADR 0007: PCM packaging — `pyproject.toml` package-data changes affect PCM archive build
