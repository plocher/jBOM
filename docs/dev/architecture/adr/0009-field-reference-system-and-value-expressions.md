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

### Option 2b — `${token}` interpolation in expression strings (rejected)
Instead of preprocessing `word:word` tokens, require users to wrap field
references in `${}` markers: `"re.sub(r'^[^:]+:', '', ${pcb:footprint})"`.

Rejected because: in Python expression context, `word:word` is already
syntactically invalid — the `:` creates a syntax error outside subscript or
dict literal positions. The preprocessor can unambiguously identify field
references without any decoration. `${...}` solves a problem that doesn't exist
and creates visual noise with no semantic value.

### Option 3 — Pipe model for chained transforms (rejected)
`"Footprint": "pcb:footprint | strip_kicad_library_prefix | upper"` — a
Unix-pipeline syntax chaining a field read and named transforms.

Rejected because: this is a solution in search of a problem. The expression
mechanism already handles multi-step transforms natively using standard Python
function call composition. A pipe DSL adds new syntax to learn for no capability
gain. The expression `upper(strip_kicad_library_prefix(pcb:footprint))` is
clearer and already works.

### Option 3b — `transform:namespace:field` shorthand syntax (rejected)
`"Footprint": "strip_kicad_library_prefix:pcb:footprint"` — a compact positional syntax
for applying a named transform to a single field reference.

Rejected because: this overloads `:` with two meanings simultaneously —
namespace separator AND "apply transform to field". `pcb:` is a namespace
qualifier; is `strip_lib_prefix:` also a "transform qualifier"? The parser
would need external knowledge (the namespace vocabulary) to disambiguate,
reintroducing exactly the kind of implicit magic this ADR is designed to
eliminate. Function call syntax `strip_lib_prefix(pcb:footprint)` is
unambiguous, already covered by the expression mechanism, and reads as
standard Python.

### Option 4 — `namespace:field` preprocessing + `ast.parse(mode='eval')` (accepted)

A two-part system:

1. **Field references** use an explicit `namespace:field` syntax (`pcb:footprint`,
   `inv:IPN`). In Python expression context, `word:word` is already syntactically
   invalid — the preprocessor exploits this as an unambiguous signal without
   requiring any decoration (`${...}` is unnecessary).

2. **Value expressions** are Python expressions evaluated with
   `ast.parse(mode='eval')` in a restricted namespace: `re` plus all
   config-defined transforms. No imports, no side effects.

3. **Transforms** are single-argument functions defined in any `.jbom.yaml` via
   a `transforms:` stanza. The same config that creates a transformation
   requirement also defines how to satisfy it, with no jBOM release needed.
   Built-in transforms ship in `common.jbom.yaml`.

### D1. Source namespace vocabulary

Field references from non-canonical sources carry an explicit namespace prefix.
Three namespaces are defined:

| Prefix | Source | Description |
|---|---|---|
| `sch:` | Schematic | Component properties from `.kicad_sch` (replaces `c:`) |
| `pcb:` | PCB / placement | Component data from `.kicad_pcb` (replaces `p:`) |
| `inv:` | Inventory | Fields from matched inventory CSV rows (replaces `i:`) |

Bare names without a namespace prefix are either jBOM-computed fields (a small
set: `quantity`, `fabricator_part_number`, `smd`) or convenience aliases
(`value`, `reference`, `footprint`, etc.) that resolve to the appropriate source
namespace via the active `field_precedence_policy` in `defaults:`. The full
taxonomy is described in D4.

`k:` is not a namespace — it is replaced by the expression mechanism in D2.
The old single-character prefixes (`c:`, `p:`, `i:`, `k:`) are retired;
no shim or deprecation warning is provided.

### D2. Value expressions — field references and Python expressions

A `bom_columns` value (or any config value that accepts a field reference) is
one of two forms. `:` means exactly one thing throughout: namespace separator.

**A plain field reference** — resolved directly:
```yaml
bom_columns:
  "Designator": "reference"        # convenience alias (resolves via field_precedence_policy)
  "Package":    "inv:package"      # inventory namespace
  "Footprint":  "pcb:footprint"    # PCB namespace
```

**A Python expression containing field references** — evaluated to produce the
output value:
```yaml
bom_columns:
  # Strip KiCad library prefix (replaces "p:k:footprint"; transform from D3/D7)
  "Footprint": "strip_kicad_library_prefix_from_value(pcb:footprint)"

  # Combine two source fields
  "Label":     "f'{reference} ({inv:manufacturer})'"

  # Arbitrary regex inline (no named transform needed)
  "PN":        "re.sub(r'\\s+', '-', inv:manufacturer_part).upper()"
```

**Expression evaluation contract:**

1. Scan the expression string for `word:word` patterns. Each `namespace:field`
   token is syntactically invalid Python and is unambiguously a field reference.
   Resolve each to its string value and bind as `namespace_field` in the local
   variable namespace.

2. Convenience alias names referenced in the expression are resolved via the
   active `field_precedence_policy` and bound by name in the local namespace
   (e.g., `value` → whichever source namespace the policy designates as
   authoritative for `value`).

3. Replace `namespace:field` tokens in the expression string with their
   `namespace_field` variable names. The result is a valid Python expression.

4. Parse with `ast.parse(expr, mode='eval')`. This rejects statements, loop
   constructs, function definitions, and `import` statements at the grammar
   level — before any evaluation.

5. Evaluate in a restricted namespace containing:
   - The resolved field variables
   - `re` (Python's standard `re` module, see D3)
   - All compiled transforms from the active config chain (D3, D7)
   - No `__builtins__`

6. The return value is coerced to `str`. Exceptions surface as a
   `FieldExpressionError` with the offending expression and field values.

**Detection:** a value is an expression if it is not a plain field reference —
i.e., it contains characters outside `(namespace:)?fieldname` (parentheses,
quotes, operators, etc.). Plain field references are always tried first.

### D3. Expression evaluation namespace

The expression evaluator provides `re` (Python's standard regex module) in the
evaluation namespace. No other Python modules or functions are pre-loaded.

Named transforms — including those shipped with jBOM — are config-defined (D7),
not Python-registered. This keeps the Python-side minimal and means even
jBOM-provided transforms can be inspected, overridden, or extended in config
without a jBOM release.

The built-in `common.jbom.yaml` shipped with jBOM pre-defines common transforms:

```yaml
# src/jbom/config/common.jbom.yaml (built-in, shipped with jBOM)
transforms:
  strip_kicad_library_prefix_from_value:
    expr: "re.sub(r'^[^:]+:', '', value)"
    doc:  "Remove KiCad library nickname. 'Capacitors_SMD:C_0402' → 'C_0402'"
```

A user can override a built-in transform by defining the same name in their
own `.jbom.yaml`.

### D4. Field categories — source, computed, and convenience aliases

Fields accessible in `bom_columns` values, `--fields` arguments, and expressions
fall into three distinct categories with different natures.

**Category 1: Source fields — not pre-registered; discovered at runtime**

Source fields carry an explicit namespace prefix and their availability is
determined by the actual data:
- `sch:*` — whatever symbol properties the KiCad schematic contains
  (`sch:Value`, `sch:Footprint`, `sch:Reference`, user-defined attributes such
  as `sch:LCSC`, `sch:PART_STATUS`, ...)
- `pcb:*` — placement attributes from the PCB file (`pcb:x`, `pcb:y`,
  `pcb:rotation`, `pcb:side`)
- `inv:*` — whatever column headers the matched inventory CSV provides
  (`inv:IPN`, `inv:Supplier`, `inv:SPN`, `inv:MPN`, `inv:Package`, ...)

jBOM cannot enumerate these ahead of time. A user's schematic may have a
custom `PART_STATUS` attribute; their inventory may use bespoke column names.
These fields are discovered at evaluation time from the actual data sources.

**Category 2: jBOM-computed fields — a small Python-registered set**

A small set of field names are produced by jBOM's internal processing logic,
not passed through from any source:

| Name | Computed by |
|---|---|
| `quantity` | Grouping logic (count of identical components) |
| `fabricator_part_number` | Part number resolution from matched inventory item |
| `smd` | Calculated from PCB placement type |

These are the only fields registered in `src/jbom/config/fields.py`. The earlier
draft of this ADR incorrectly listed source fields (`reference`, `value`, etc.)
as "canonical jBOM-computed fields" — they are source fields, accessed via
namespace prefix or convenience alias (Category 3).

`__resolved_fabricator_part_number__` is retired; replaced by `fabricator_part_number`.

**Category 3: Convenience aliases — config-defined bare names**

Bare names without a namespace prefix (`value`, `footprint`, `reference`) are
convenience aliases. They resolve to the appropriate source namespace field
according to the `field_precedence_policy` defined in the active `defaults:`
stanza:

```yaml
# common.jbom.yaml (ambient — applied at every search-path level)
field_precedence_policy:
  schematic_biased:
    - value
    - tolerance
    - footprint
    ...
  pcb_biased:
    - x
    - y
    - rotation
    ...
```

This policy lives in `common.jbom.yaml`, not `generic.jbom.yaml`, because it
controls how bare field names resolve for every command regardless of which
named profile is active — exactly what `common.jbom.yaml` is for. An org can
override or extend the policy in their own `common.jbom.yaml`.

The `field_precedence_policy` content currently in `generic.defaults.yaml`
migrates to `common.jbom.yaml` as part of the built-in file migration in Phase 1.

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
top-level `transforms:` stanza. The built-in `strip_kicad_library_prefix_from_value`
ships this way in `common.jbom.yaml` (see D3). Org-level and project-level
`common.jbom.yaml` files extend the transform set at their respective search-path
levels.

`common.jbom.yaml` files are automatically deep-merged as ambient defaults at
each search-path level — they are not named profiles. All `common.jbom.yaml`
files in the search path are cumulative (every level contributes); named profile
files use first-match-wins. The `policy.jbom.yaml` mandate mechanism (ADR 0008
D6) can enforce transforms that lower-level configs cannot remove. See ADR 0008
D5–D6 for the full `common.jbom.yaml` mechanics.

```yaml
  # src/jbom/config/common.jbom.yaml — definition (ships with jBOM)
transforms:
  strip_kicad_library_prefix_from_value:
    expr: "re.sub(r'^[^:]+:', '', value)"
    doc:  "'Capacitors_SMD:C_0402' → 'C_0402'"

  # jlc.jbom.yaml — usage
fab:
  bom_columns:
    "Designator": "reference"
    "Quantity": "quantity"
    "Value": "value"
    "Footprint": "strip_kicad_library_prefix_from_value(pcb:footprint)"
    "LCSC": "fabricator_part_number"  # JLCPCB requires this column name in BOM
    "Surface Mount": "smd"
    "Comment": "description"
```

`value` is the implicit single argument in each `expr`. Naming convention:
the noun `value` must appear in the transform name — it maps directly to the
`value` parameter used in the `expr`. This makes the connection explicit to
anyone reading a config file without looking up the transform definition:

- `strip_kicad_library_prefix_from_value` → `re.sub(r'^[^:]+:', '', value)`
- `normalize_component_value` → `re.sub(r'\\s+', '', value).upper()`

Avoid generic names (`normalize`, `strip`) that omit what is being transformed.
Avoid names without the `value` noun: the reader needs to know the function
operates on a single string argument named `value`.

`expr` is validated with `ast.parse(mode='eval')` at config load time —
malformed transform expressions fail early, not at BOM generation time.

Each defined transform is compiled to a single-argument callable and added to
the expression evaluation namespace alongside `re` (D3). From the evaluator's
perspective, user-defined, org-defined, and built-in config transforms are
indistinguishable — they are all config-defined.

`transforms:` follows the same inheritance rules as all other config content:
`extends:` chains propagate parent transforms to child profiles; a
`common.jbom.yaml` at each search-path level contributes ambient transforms
available to all configs at that level and below.

jBOM validates transform names at config load time. When a user-defined name
matches a built-in from the shipped `common.jbom.yaml`, the user's definition
shadows the built-in (intentional override is supported) and jBOM logs a
`NOTICE`-level message so accidental shadows are detectable. Two user-defined
transforms with the same name in the same file are a load-time error.

This allows `--fields` CLI arguments and config `bom_columns` values to
reference org-defined transforms by name, enabling a team's `common.jbom.yaml`
to publish a shared transform library without requiring a jBOM release.


## Decision

**Option 4 is approved.** Rationale from the successive rejections:

**From Option 1**: a fixed Python vocabulary requires jBOM releases to extend.
The config that invents a transformation requirement should define how to satisfy
it — in the same file, without a release cycle.

**From Option 2**: Jinja2 is a document template engine. Python's `ast` module
provides the right capability (expression evaluation) without the baggage.

**From Option 2b**: `${...}` decoration is unnecessary. `word:word` in Python
expression context is already a syntax error — the preprocessor exploits this
as an unambiguous signal with no additional markers required.

**From Option 3**: a pipe DSL adds syntax to learn with no capability gain;
standard Python function call composition handles multi-step transforms.

**From Option 3b**: `:` must mean one thing. Using it as both namespace
separator and transform operator requires the parser to know the closed
namespace vocabulary — reintroducing the implicit magic this design eliminates.

Key properties:
- Three explicit source namespaces (`sch:`, `pcb:`, `inv:`) replace opaque
  single-character prefixes. `:` means exactly one thing: namespace separator.
- Source fields are runtime-discovered; only three jBOM-computed fields
  (`quantity`, `fabricator_part_number`, `smd`) are Python-registered.
- Bare convenience alias names resolve via `field_precedence_policy` in
  `defaults:` — config-owned, not hardcoded.
- `namespace:field` tokens are syntactically invalid Python and are
  unambiguously preprocessed before `ast.parse(mode='eval')`. No `${}` decoration.
- Named transforms (including built-in ones in `common.jbom.yaml`) are
  config-defined; expression eval provides only `re`. No Python stdlib.
- `field_synonyms` is unified to one structure and one parser across all stanzas.
- CLI `--fields` and config `bom_columns` share one field reference language.

## Consequences

### Positive
- The old `p:k:footprint` is no longer magic; it is completely visible in the config files.
  The transform can be inspected, overridden, or replaced without touching Python.
- Users can combine fields, apply regex, and format output values without waiting
  for jBOM releases.
- `__resolved_fabricator_part_number__` is gone; `fabricator_part_number` is a
  jBOM-computed field with a clear definition.
- Source field vocabulary (sch:/pcb:/inv:) is runtime-discovered, not a static
  Python registry that diverges from reality.
- `field_synonyms` triplication eliminated; one parser to test and maintain.
- CLI and config field references are one language; documentation collapses to
  one section.

### Negative / Tradeoffs
- Expressions in config are harder to read for non-developers than simple field
  references. Plain field references remain the common case; expressions are
  opt-in for transformation needs. A realistic composite config using both:

  ```yaml
  # $REPO_ROOT/.jbom/acme-jlc.jbom.yaml — corporate JLC fork
  extends: jlc

  transforms:
    normalize_component_value:
      expr: "re.sub(r'\\s+', '', value).upper()"
      doc:  "Normalize value strings: '10 K' → '10K'"

  fab:
    bom_columns:
      "Surface Mount": null                                   # delete inherited
      "Footprint":     "strip_kicad_library_prefix_from_value(pcb:footprint)"
      "Value":         "normalize_component_value(sch:Value)"
      "IPN":           "inv:IPN"                              # plain field ref
      "Status":        "inv:PART_STATUS"                      # custom sch attribute
  ```

  The plain `"inv:IPN"` and `"inv:PART_STATUS"` lines are readable to any
  engineer. The expression lines require understanding the transform mechanism.
  The comment on `normalize_component_value` is the recommended mitigation.
- The `ast.parse` + restricted-eval path adds complexity to the field resolver.
  This complexity is bounded and testable (expression rejection, namespace
  restriction, error surfacing).
- Built-in transforms in `common.jbom.yaml` must be documented, versioned, and
  not broken across releases (same bar as any other shipped config content).
- The `transforms:` stanza adds a new user-facing config concept that must be
  validated, documented, and handled by the merge engine (inherited via
  `extends:` and `common.jbom.yaml`).

### Risks and Mitigations
- **Risk**: A future Python version changes `ast.parse` expression grammar or
  `compile/eval` semantics.
  **Mitigation**: expression evaluation is isolated in `FieldExpressionEvaluator`;
  one class to update if Python internals shift.
- **Risk**: Users write expressions that produce wrong output silently (no
  exception, just an unexpected value) due to wrong field reference or transform.
  **Mitigation**: `FieldExpressionError` surfaces failures with expression +
  field values. The `jbom fields` diagnostic command (Deferred 4) will show
  which transforms are loaded and from which config file; a debug/verbose mode
  should trace transform input → output at evaluation time.
- **Non-risk**: The old single-character prefixes (`c:`, `p:`, `i:`, `k:`) are
  not supported. No user files exist to break; nothing has shipped externally.

## Deferred Items

1. **Value type contracts and normalize transforms** — Percentage strings
   (`"5%"`), voltage strings (`"10V"`), and wattage strings (`"63mW"`) are
   currently consumed opaquely by jBOM's heuristics engine. Whether these
   normalizations can be expressed as config-defined transforms (making component
   matching rules extensible without code changes) is worth exploring in a
   follow-on design. If feasible, the heuristics engine would become a consumer
   of config-defined normalizers rather than a holder of hardcoded string
   patterns.
2. **Category classification** — Component categories (`RES`, `CAP`, `IND`,
   etc.) are data-driven: they emerge from the component's content (value,
   footprint, symbol name), not from a fixed jBOM vocabulary. The heuristic
   classifier that maps content to category tokens is partly hardcoded in Python.
   Like value normalization (item 1), config-driven category classification would
   be the consistent direction. Out of scope here; tracked separately.
3. **`jbom fields` diagnostic command** — prints the discovered source field
   sets for the current project: `sch:*` attributes found in the schematic,
   `pcb:*` placement attributes, `inv:*` inventory column headers, and the
   three jBOM-computed fields; also lists all loaded transforms and which config
   file defined each. Complements `jbom config show` (ADR 0008, Deferred Item 5).

## Implementation Phases

**Phase 1 (this feature branch, alongside ADR 0008 Phase 1)**
- `src/jbom/config/fields.py` — jBOM-computed field registry (Category 2 only:
  `quantity`, `fabricator_part_number`, `smd`); source namespace constants
  (`SCH`, `PCB`, `INV`). Source field discovery is runtime, not pre-registered.
- `src/jbom/config/field_ref.py` — `FieldRef` dataclass (namespace, name,
  expression); `FieldRefResolver.resolve(ref, context)` → value.
- `src/jbom/config/field_expr.py` — `FieldExpressionEvaluator`:
  - `namespace:field` token scanning and local variable binding
  - `ast.parse(mode='eval')` + restricted eval
  - `transforms:` stanza parsing: validate `expr` at load time, compile to
    callable, add to eval namespace alongside `re`
- `src/jbom/config/field_synonyms.py` — single shared `parse_field_synonyms()`
  replacing the three divergent parsers.
- Update `fabricators.py`, `defaults.py`, `suppliers.py` to use shared parser.
- Update `bom_workflow.py` / CLI `--fields` parser to use `FieldRefResolver`.
- Built-in config files using old prefixes are migrated in Phase 2; no shim.
- Unit tests: namespace resolution, expression evaluation, statement rejection,
  `strip_kicad_library_prefix_from_value`, error surfacing, transform name
  shadowing (NOTICE logged), duplicate-name error.

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
