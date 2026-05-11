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
- The old `i:`, `p:`, `c:`, `k:` notation is retired with no shim. Nothing
  has shipped externally; a clean break requires no major version bump.

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

`k:` is not a namespace — it is replaced by the expression mechanism in D2.
The old single-character prefixes (`c:`, `p:`, `i:`, `k:`) are retired;
no shim or deprecation warning is provided.

### D2. Value expressions — field references and Python expressions

A `bom_columns` value (or any config value that accepts a field reference) is
one of two forms. `:` means exactly one thing throughout: namespace separator.

**A plain field reference** — resolved directly:
```yaml
bom_columns:
  "Designator": "reference"        # canonical computed field (no namespace)
  "Package":    "inv:package"      # inventory namespace
  "Footprint":  "pcb:footprint"    # PCB namespace
```

**A Python expression containing field references** — evaluated to produce the
output value:
```yaml
bom_columns:
  # Strip KiCad library prefix (replaces "p:k:footprint")
  "Footprint": "kicad_strip_library_prefix(pcb:footprint)"

  # Combine two fields
  "Label":     "f'{reference} ({inv:manufacturer})'"

  # Arbitrary regex
  "PN":        "re.sub(r'\\s+', '-', inv:manufacturer_part).upper()"

  # User-defined named transform (see D7)
  "Footprint": "strip_lib_prefix(pcb:footprint)"
```

**Why no `${}` decoration:** in Python expression context, `word:word`
(namespace-qualified field references) is syntactically invalid Python. The
preprocessor identifies and binds these unambiguously without additional
decoration. Canonical field names are valid Python identifiers and are bound
directly in the eval namespace.

**Expression evaluation contract:**

1. Scan the expression string for `word:word` patterns. Each `namespace:field`
   token is syntactically invalid Python and is unambiguously a field reference.
   Resolve each to its string value and bind as `namespace_field` in the local
   variable namespace.

2. Canonical field names referenced in the expression are bound by name in the
   local namespace (e.g., `reference` → the resolved reference value).

3. Replace `namespace:field` tokens in the expression string with their
   `namespace_field` variable names. The result is a valid Python expression.

4. Parse with `ast.parse(expr, mode='eval')`. This rejects statements, loop
   constructs, function definitions, and `import` statements at the grammar
   level — before any evaluation.

5. Evaluate in a restricted namespace containing:
   - The resolved field variables
   - `re` (Python's standard `re` module)
   - The jBOM expression stdlib and user-defined transforms (see D3, D7)
   - No `__builtins__`

6. The return value is coerced to `str`. Exceptions surface as a
   `FieldExpressionError` with the offending expression and field values.

**Detection:** a value is an expression if it is not a plain field reference —
i.e., it contains characters outside `(namespace:)?fieldname` (parentheses,
quotes, operators, etc.). Plain field references are always tried first.

### D3. jBOM expression stdlib

A small set of jBOM-curated helper functions is available in every expression
evaluation namespace. These are regular Python functions (not magic syntax),
documented, and versioned with jBOM.

v1 stdlib:
```
kicad_strip_library_prefix(s)   → re.sub(r'^[^:]+:', '', s)
    Removes the KiCad library nickname from a symbol or footprint name.
    "Capacitors_SMD:C_0402" → "C_0402"
```

Users are not limited to the stdlib — `re.sub`, `str` methods, and other
Python expression constructs work directly. The stdlib is an additive
convenience layer, not a replacement vocabulary. Users who need a named
transform not in the stdlib can define it in their own config (see D7)
without waiting for a jBOM release.

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

### D7. User-defined named transforms via `transforms:` stanza

Any `.jbom.yaml` file may define named single-argument transform functions in a
top-level `transforms:` stanza:

```yaml
# common.jbom.yaml — team-wide named transforms
transforms:
  strip_lib_prefix:
    expr: "re.sub(r'^[^:]+:', '', value)"
    doc:  "Remove KiCad library nickname prefix from symbol or footprint"

  normalize_pn:
    expr: "value.replace(' ', '-').upper()"
    doc:  "Normalize part number to hyphenated uppercase"
```

`value` is the implicit single argument. `expr` is validated with
`ast.parse(mode='eval')` at config load time — malformed transform expressions
fail early, not at BOM generation time.

Each defined transform is compiled to a single-argument callable and added to
the expression evaluation namespace alongside the jBOM stdlib (D3). From the
evaluator's perspective, user-defined and jBOM-stdlib transforms are
indistinguishable — they are the same kind of thing.

`transforms:` follows the same inheritance rules as all other config content:
`extends:` chains propagate parent transforms to child profiles; a
`common.jbom.yaml` at each search-path level contributes ambient transforms
available to all configs at that level and below. Transform names must not
collide with jBOM stdlib names (validated at load time with a warning).

This allows `--fields` CLI arguments and config `bom_columns` values to
reference org-defined transforms by name, enabling a team's `common.jbom.yaml`
to publish a shared transform library without requiring a jBOM release.

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
surface area — than field value expression requires. The `namespace:field`
preprocessing + `ast.parse(mode='eval')` approach provides the needed expression
power without the baggage, and without a new dependency.

### Option 3 — Pipe model for chained transforms (deferred)
`"Footprint": "pcb:footprint | strip_kicad_library_prefix | upper"` — a
Unix-pipeline syntax chaining field read and named transforms.

Not adopted as the primary mechanism; a pipeline model could be layered on top
of the expression mechanism in a future ADR if use cases emerge. The expression
mechanism (D2) handles multi-step transforms natively.

### Option 3b — `transform:namespace:field` shorthand syntax (rejected)
`"Footprint": "strip_lib_prefix:pcb:footprint"` — a compact positional syntax
for applying a named transform to a single field reference.

Rejected because: this overloads `:` with two meanings simultaneously —
namespace separator AND "apply transform to field". `pcb:` is a namespace
qualifier; is `strip_lib_prefix:` also a "transform qualifier"? The parser
would need external knowledge (the namespace vocabulary) to disambiguate,
reintroducing exactly the kind of implicit magic this ADR is designed to
eliminate. Function call syntax `strip_lib_prefix(pcb:footprint)` is
unambiguous, already covered by the expression mechanism, and reads as
standard Python.

### Option 4 — `namespace:field` preprocessing + `ast.parse(mode='eval')` (accepted — this ADR)
Described in D1–D7 above.

## Decision

Adopt the field reference system and value expression mechanism as described
in D1–D7.

Key properties:
- Three explicit source namespaces (`sch:`, `pcb:`, `inv:`) replace opaque
  single-character prefixes. `:` means exactly one thing: namespace separator.
- Canonical computed fields carry no namespace prefix and are defined in a
  single authoritative registry.
- `namespace:field` tokens are syntactically invalid Python and are
  unambiguously preprocessed before `ast.parse(mode='eval')`. No `${}` decoration.
- A jBOM expression stdlib provides named convenience functions; users extend
  it via the `transforms:` stanza in any `.jbom.yaml` without a jBOM release.
- `field_synonyms` is unified to one structure and one parser across all stanzas.
- CLI `--fields` and config `bom_columns` share one field reference language.

## Consequences

### Positive
- `p:k:footprint` becomes `kicad_strip_library_prefix(pcb:footprint)` —
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
- The `transforms:` stanza adds a new user-facing config concept that must be
  validated, documented, and handled by the merge engine (inherited via
  `extends:` and `common.jbom.yaml`).

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
- **Non-risk**: The old single-character prefixes (`c:`, `p:`, `i:`, `k:`) are
  not supported. No user files exist to break; nothing has shipped externally.

## Deferred Items

1. **Value type contracts** — percentage strings (`"5%"`), voltage strings
   (`"10V"`), wattage strings (`"63mW"`) have no schema-level type contract or
   normalization rule. These are out of scope here; a follow-on ADR or
   enhancement tracks them.
2. **Category token vocabulary** — canonical casing and normalization rules for
   component category tokens (`RES`, `res`, `resistor`) are out of scope here.
3. **Pipe-chained transforms** — reserved for future consideration once
   expression usage patterns are observed in practice.

## Implementation Phases

**Phase 1 (this feature branch, alongside ADR 0008 Phase 1)**
- `src/jbom/config/fields.py` — canonical field name registry as a typed enum
  or frozenset; source namespace constants.
- `src/jbom/config/field_ref.py` — `FieldRef` dataclass (namespace, name,
  expression); `FieldRefResolver.resolve(ref, context)` → value.
- `src/jbom/config/field_expr.py` — `FieldExpressionEvaluator`:
  - `namespace:field` token scanning and local variable binding
  - `ast.parse(mode='eval')` + restricted eval
  - jBOM expression stdlib registration
  - `transforms:` stanza parsing: validate `expr` at load time, compile to
    callable, add to eval namespace
- `src/jbom/config/field_synonyms.py` — single shared `parse_field_synonyms()`
  replacing the three divergent parsers.
- Update `fabricators.py`, `defaults.py`, `suppliers.py` to use shared parser.
- Update `bom_workflow.py` / CLI `--fields` parser to use `FieldRefResolver`.
- Built-in config files using old prefixes are migrated in Phase 2; no shim.
- Unit tests: namespace resolution, expression evaluation, statement rejection,
  `kicad_strip_library_prefix`, error surfacing, transform compilation.

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
