# ADR 0009: Field Reference System and Value Expressions
Date: 2026-05-11
Status: Proposed
Related: #250, #251, ADR 0008

## Context

ADR 0008 establishes the unified `*.jbom.yaml` container format. This ADR
addresses the content within that container: the language used to reference
fields and express field value transformations.

The current system grew organically and has accumulated several compounding
problems.

### The `i:/p:/c:/k:` prefix system

The field prefix notation (`i:package`, `p:k:footprint`, `c:tolerance`)
originated in the `--fields` CLI argument parser and was copied into
`bom_columns` config because both express the same concept. The config schema
borrowed a CLI convention rather than defining its own.

More critically, the notation conflates three orthogonal concepts in a single
opaque string:

```
p  : k  : footprint
│    │    └─ field name
│    └─── transformation (strip KiCad library prefix)
└──────── source namespace (PCB/placement data)
```

`k:` is not a namespace qualifier — it is a value transformation. The notation
has no schema definition, no discoverable vocabulary, and no way for users to
express new transformations without a jBOM release.

### Magic sentinels

`enrichment_bindings` in `generic.defaults.yaml` contains
`"__resolved_fabricator_part_number__"` — a Python-internal implementation
detail serialized as a YAML string with no meaning to a config author.

### Triplicated `field_synonyms` structure

The `field_synonyms` mapping appears in `fab:`, `defaults:`, and `supplier:`
stanzas with structural drift between them, despite all three mapping to the
same Python type (`FieldSynonym`). The YAML structure is not isomorphic to the
data model.

### CLI / config syntax divergence

The `--fields` CLI argument and `bom_columns` config values express the same
concept (field selection) but are parsed by separate code with diverging
conventions. A user must learn two syntaxes that should be one.

### The design lens

A useful test for any proposed fix: *if this config were a Python expression
constructing jBOM dataclass instances directly, what would it look like? Does
the YAML schema reflect that clearly?* Any YAML key or value that requires
explanation to translate to its Python equivalent is a schema design smell.

## Decision Drivers

- Field references must separate **source**, **name**, and **transformation**
  into independently named, composable concepts.
- Users must be able to express value transformations without a jBOM release.
- The `--fields` CLI syntax and `bom_columns` config values must share one
  canonical field reference language — defined in the config spec, consumed by
  the CLI parser.
- Transformation expressions must be safe (expressions only, no imports, no
  side effects) and require no new parser infrastructure beyond Python's own
  `ast` module.
- The YAML schema should be isomorphic to the Python data model it serializes.
- Backward compatibility with `i:`, `p:`, `c:`, `k:` notation is provided by
  a deprecation shim shared with ADR 0008's migration period.

## Design Decisions

### D1. Source namespace vocabulary

Field references from non-canonical sources carry an explicit namespace prefix.
Three namespaces are defined:

| Prefix | Source | Description |
|---|---|---|
| `sch:` | Schematic | Component properties from `.kicad_sch` (replaces `c:`) |
| `pcb:` | PCB / placement | Component data from `.kicad_pcb` (replaces `p:`) |
| `inv:` | Inventory | Fields from matched inventory CSV rows (replaces `i:`) |

Canonical jBOM-computed fields (`reference`, `quantity`, `value`, `description`,
`footprint`, `package`, `manufacturer`, `fabricator_part_number`, `smd`, `x`,
`y`, `rotation`, `side`, etc.) carry **no namespace prefix**. They are resolved
by jBOM from whichever source is authoritative and need no source qualifier from
the config author.

Migration shim: `c:` → `sch:`, `p:` → `pcb:`, `i:` → `inv:` are accepted with
a deprecation log warning during the ADR 0008 shim period. `k:` is replaced by
the expression mechanism (D2).

### D2. Value expressions via `${token}` interpolation

A `bom_columns` value (or any config value that accepts a field reference) may
be either:

**A plain field reference** — resolved directly:
```yaml
bom_columns:
  "Designator": "reference"          # canonical computed field
  "Package":    "inv:package"        # inventory namespace
  "Footprint":  "pcb:footprint"      # PCB namespace
```

**A Python expression with `${field_ref}` interpolation** — evaluated to produce
the output value:
```yaml
bom_columns:
  # Strip KiCad library prefix from footprint (replaces "p:k:footprint")
  "Footprint": "kicad_strip_library_prefix(${pcb:footprint})"

  # Combine two fields
  "Label":     "f'{${sch:reference}} ({${inv:manufacturer}})'"

  # Arbitrary regex
  "PN":        "re.sub(r'\\s+', '-', ${inv:manufacturer_part}).upper()"
```

**Expression evaluation contract:**

1. All `${namespace:field}` and `${canonical_field}` tokens are extracted and
   resolved to string values. Each is bound as a local variable in the
   evaluation namespace (`:` replaced by `_` in the variable name, e.g.
   `${pcb:footprint}` → `pcb_footprint`).

2. The token references in the expression string are replaced with the
   corresponding variable names.

3. The resulting string is parsed with `ast.parse(expr, mode='eval')`. This
   rejects statements, loop constructs, function definitions, and `import`
   statements at the grammar level — before any evaluation.

4. The compiled expression is evaluated in a restricted namespace containing:
   - The resolved token variables
   - `re` (Python's standard `re` module)
   - The jBOM expression stdlib (see D3)
   - No `__builtins__`

5. The return value is coerced to `str`. Exceptions during evaluation surface as
   a `FieldExpressionError` with the offending expression and token values in
   the message.

Expressions are detected by the presence of `${...}` in the value string.
Values without `${...}` are treated as plain field references regardless of
content.

### D3. jBOM expression stdlib

A small set of jBOM-curated helper functions is available in every expression
evaluation namespace. These are regular Python functions (not magic syntax),
documented, and versioned with jBOM. They provide convenience for common
jBOM-specific transformations without requiring users to write raw regex.

v1 stdlib:
```
kicad_strip_library_prefix(s)   → re.sub(r'^[^:]+:', '', s)
    Removes the KiCad library nickname from a symbol or footprint name.
    "Capacitors_SMD:C_0402" → "C_0402"
```

Users are not limited to the stdlib — `re.sub`, `str` methods, and other
Python expression constructs work directly. The stdlib is an additive
convenience layer, not a replacement vocabulary.

New stdlib functions are added as part of jBOM releases. Users who need a
transformation not in the stdlib can express it directly in the expression
without waiting for a release.

### D4. Canonical field name registry

All valid canonical (no-namespace) field names are defined in a single
authoritative registry in `src/jbom/config/fields.py`. Config values and CLI
`--fields` arguments are validated against this registry. Unknown bare names
produce a warning with the list of valid names.

The registry replaces scattered string constants and serves as the definitive
documentation of what computed fields jBOM produces.

Initial registry (non-exhaustive — full list in `fields.py`):

| Name | Description |
|---|---|
| `reference` | Component designator (R1, C2, U1) |
| `quantity` | Grouped component count |
| `value` | Component value |
| `description` | Component description |
| `footprint` | Resolved footprint name (normalized) |
| `package` | Package size / footprint shorthand |
| `manufacturer` | Manufacturer name |
| `fabricator_part_number` | Resolved fabricator / supplier part number |
| `smd` | Surface-mount flag (Y/N) |
| `x`, `y` | Placement coordinates |
| `rotation` | Placement rotation |
| `side` | Board side (F / B) |

`__resolved_fabricator_part_number__` is retired. Its role is expressed by the
canonical field name `fabricator_part_number`.

### D5. Unified `field_synonyms` structure

The `field_synonyms` stanza structure is identical across `fab:`, `defaults:`,
and `supplier:` stanzas. One canonical YAML structure, one Python type, one
parser:

```yaml
field_synonyms:
  <canonical_key>:
    display_name: "<output header string>"
    synonyms:
      - "<accepted input variant>"
      - "<accepted input variant>"
```

The per-stanza parsers (`_parse_field_synonyms` in `fabricators.py`,
`_parse_field_synonym_configs` in `defaults.py`, and the supplier parser)
are replaced by a single shared function in `src/jbom/config/field_synonyms.py`.

### D6. CLI `--fields` alignment

The `--fields` CLI argument accepts the same field reference syntax as
`bom_columns`: plain canonical names, namespaced references (`inv:package`),
and expression strings (`"re.sub(...)"`). The CLI parser delegates to the
same `FieldRefResolver` used by the config loader.

This makes the CLI and config syntaxes a single documented language rather than
two diverging conventions.

## Options Considered

### Option 1 — Named transform vocabulary (rejected)
Define a curated set of named transforms: `strip_kicad_library_prefix`,
`normalize_value`, etc. Users select from this vocabulary in config.

Rejected because: extending the vocabulary requires a jBOM release. It is
"more magic" — just relocated from special characters to a developer-maintained
list. The expression mechanism (D2) provides a strict superset of this
capability at no additional security cost.

### Option 2 — Jinja2 template engine (rejected)
Use Jinja2's expression syntax (`{{ field | filter }}`) for field value
transforms. Jinja2 provides a sandboxed eval environment and custom filter
registration.

Rejected because: Jinja2 solves document templating (with looping constructs,
block inheritance, macros). That is more capability — and more cognitive
surface area — than field value expression requires. The `${token}` +
`ast.parse(mode='eval')` approach provides the needed expression power without
the baggage, and without a new dependency.

### Option 3 — Pipe model for chained transforms (deferred)
`"Footprint": "pcb:footprint | strip_kicad_library_prefix | upper"` — a
Unix-pipeline syntax chaining field read and named transforms.

Not adopted as the primary mechanism; a pipeline model could be layered on top
of the expression mechanism in a future ADR if use cases emerge. The expression
mechanism (D2) handles multi-step transforms natively.

### Option 4 — `${token}` + `ast.parse(mode='eval')` (accepted — this ADR)
Described in D1–D6 above.

## Decision

Adopt the field reference system and value expression mechanism as described
in D1–D6.

Key properties:
- Three explicit source namespaces (`sch:`, `pcb:`, `inv:`) replace opaque
  single-character prefixes.
- Canonical computed fields carry no namespace prefix and are defined in a
  single authoritative registry.
- `${token}` interpolation + `ast.parse(mode='eval')` provides safe, user-
  extensible field value transformation without requiring jBOM releases for
  common string manipulation needs.
- A small jBOM expression stdlib provides named convenience functions without
  replacing the general expression mechanism.
- `field_synonyms` is unified to one structure and one parser across all stanzas.
- CLI `--fields` and config `bom_columns` share one field reference language.

## Consequences

### Positive
- `p:k:footprint` becomes `kicad_strip_library_prefix(${pcb:footprint})` —
  self-documenting, no magic characters, extensible to any regex the user needs.
- Users can combine fields, apply regex, and format output values without waiting
  for jBOM releases.
- `__resolved_fabricator_part_number__` is gone; `fabricator_part_number` is in
  the canonical registry with a clear definition.
- `field_synonyms` triplication eliminated; one parser to test and maintain.
- CLI and config field references are one language; documentation collapses to
  one section.

### Negative / Tradeoffs
- Expressions in config are harder to read for non-developers than simple field
  references. Plain field references remain the common case; expressions are
  opt-in for transformation needs.
- The `ast.parse` + restricted-eval path adds complexity to the field resolver.
  This complexity is bounded and testable (expression rejection, namespace
  restriction, error surfacing).
- The jBOM expression stdlib must be documented, versioned, and not broken
  across jBOM releases (same API stability bar as the rest of the config API).

### Risks and Mitigations
- **Risk**: A future Python version changes `ast.parse` expression grammar or
  `compile/eval` semantics.
  **Mitigation**: expression evaluation is isolated in `FieldExpressionEvaluator`;
  one class to update if Python internals shift.
- **Risk**: Users write expressions that are technically valid but produce empty
  strings or exceptions at runtime due to missing field values.
  **Mitigation**: `FieldExpressionError` surfaces expression + context at the
  point of failure; a future `jbom config show` command (ADR 0008, Deferred 5)
  would allow pre-flight validation.
- **Risk**: Namespace renames (`c:` → `sch:`) break existing user `.jbom/` files.
  **Mitigation**: the legacy prefix shim (shared with ADR 0008 migration) accepts
  and translates old prefixes with a deprecation warning.

## Deferred Items

1. **Value type contracts** — percentage strings (`"5%"`), voltage strings
   (`"10V"`), wattage strings (`"63mW"`) have no schema-level type contract or
   normalization rule. These are out of scope here; a follow-on ADR or
   enhancement tracks them.
2. **Category token vocabulary** — canonical casing and normalization rules for
   component category tokens (`RES`, `res`, `resistor`) are out of scope here.
3. **Pipe-chained transforms** — reserved for future consideration once
   expression usage patterns are observed in practice.
4. **User-registerable stdlib extensions** — allowing `common.jbom.yaml` to
   register named helper functions into the expression stdlib. Deferred until
   concrete use cases emerge beyond what raw `re` expressions cover.

## Implementation Phases

**Phase 1 (this feature branch, alongside ADR 0008 Phase 1)**
- `src/jbom/config/fields.py` — canonical field name registry as a typed enum
  or frozenset; source namespace constants.
- `src/jbom/config/field_ref.py` — `FieldRef` dataclass (namespace, name,
  expression); `FieldRefResolver.resolve(ref, context)` → value.
- `src/jbom/config/field_expr.py` — `FieldExpressionEvaluator`:
  - `${token}` extraction and local variable binding
  - `ast.parse(mode='eval')` + restricted eval
  - jBOM expression stdlib registration
- `src/jbom/config/field_synonyms.py` — single shared `parse_field_synonyms()`
  replacing the three divergent parsers.
- Update `fabricators.py`, `defaults.py`, `suppliers.py` to use shared parser.
- Update `bom_workflow.py` / CLI `--fields` parser to use `FieldRefResolver`.
- Deprecation shim: accept `c:`, `p:`, `i:`, `k:` with warnings.
- Unit tests: namespace resolution, expression evaluation, statement rejection,
  `kicad_strip_library_prefix`, error surfacing, legacy prefix shim.

**Phase 2 (alongside ADR 0008 Phase 1b — built-in file migration)**
- Migrate built-in config files: `"p:k:footprint"` → expression form.
- Retire `__resolved_fabricator_part_number__` sentinel from defaults YAML.
- Migrate `field_synonyms` structures in all built-in files to unified form.

## References
- ADR 0008: unified `*.jbom.yaml` container format
- `src/jbom/config/fabricators.py`: `_parse_field_synonyms` (to be replaced)
- `src/jbom/config/defaults.py`: `_parse_field_synonym_configs` (to be replaced)
- `src/jbom/config/suppliers.py`: supplier field_synonyms parser (to be replaced)
- `src/jbom/common/fields.py`: existing field handling (context for registry work)
- Python `ast` module — expression-mode parsing and safe eval pattern
