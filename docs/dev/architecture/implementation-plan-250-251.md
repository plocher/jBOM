# Implementation Plan: Config System Rewrite (#250, #251)
Branch: feat/config-unified-schema
Session role: supervisor/reviewer
Sub-agent role: implementation

## Context
ADRs 0008, 0009, 0010 and the schema audit (`config-schema-audit.md`) are complete
and committed on this branch. This document is the ordered action list for
implementation. The supervising session retains context of the design decisions
and serves as the reviewer for each phase.

Key principle from ADR 0008 D8: **atomic delivery**. All five phases below land
in this branch before merge. No intermediate broken state.

## What's already done
- ADR 0008, 0009, 0010 committed
- `docs/dev/architecture/config-schema-audit.md` committed
- Feature branch `feat/config-unified-schema` pushed, PR #267 open

---

## Phase 1a — Pydantic Migration (ADR 0010)

**Objective**: Replace all config `@dataclass` classes with Pydantic v2 `BaseModel`.
The class definition IS the schema. `from_yaml_dict()` methods are eliminated.

**Driving decisions**: ADR 0010 D1–D5

### Tasks

**1a-1** Add `pydantic>=2.0` to `pyproject.toml` required dependencies.
Add `pydantic` to PCM vendoring list in `pyproject.toml` package-data or build script.
Verify: `pip install pydantic` in the test environment; import succeeds.

**1a-2** Migrate supporting leaf types first (no dependencies on other config classes):
- `FieldSynonym` (in `fabricators.py`, `defaults.py`, `suppliers.py`) →
  unified `FieldSynonym(BaseModel)` in new `src/jbom/config/field_synonyms.py`
  (resolves smell S1 partial — one definition, one parser; see 1a-5 for full unification)
- `TierCondition(BaseModel)` with `TierOperator` enum replacing string DSL
- `TierRule(BaseModel)`
- `SearchProviderConfig(BaseModel)` — note `extra` field stays as `Dict[str, Any]`
  with `model_config = ConfigDict(extra='allow')` for provider-specific keys
- `EnrichmentCategoryConfig(BaseModel)`
- `InventorySchemaConfig(BaseModel)`

**1a-3** Migrate `FabricatorConfig` to `BaseModel`:
- Field names must match YAML keys (see schema audit for current mismatches)
- `tier_rules` → `@computed_field` derived from `tier_overrides`
- `cpl_rotation_range` constraint → `@field_validator`
- `model_config = ConfigDict(extra='ignore')`
- Remove `from_yaml_dict()` method; replace call sites with `model_validate()`
- Verify: `FabricatorConfig.model_json_schema()` produces a JSON Schema

**1a-4** Migrate `SupplierConfig` and `DefaultsConfig` to `BaseModel` following
same pattern as 1a-3.

**1a-5** Implement unified `parse_field_synonyms()` in `src/jbom/config/field_synonyms.py`
replacing the three divergent parsers (`_parse_field_synonyms` in fabricators.py,
`_parse_field_synonym_configs` in defaults.py, supplier parser). Wire into the
three models. (Resolves smell S1.)

**1a-6** Update all consuming code:
- Run `git grep -rn "\.tier_rules\|\.field_synonyms\|from_yaml_dict"` to find callsites
- Update attribute references wherever a rename occurred
- All `from_yaml_dict()` call sites → `model_validate()`

**Acceptance criteria**:
- All existing tests pass
- `FabricatorConfig.model_json_schema()` is stable (schema regression test)
- No `from_yaml_dict()` method exists in any config class
- No `Field(alias=...)` exists anywhere in the codebase
- `git grep "from_yaml_dict"` returns zero results

---

## Phase 1b — Unified Config Loader (ADR 0008)

**Objective**: Implement the unified `.jbom.yaml` loading machinery.

**Driving decisions**: ADR 0008 D1–D8, ADR 0009 D1

### Tasks

**1b-1** Implement `src/jbom/config/unified.py`:
```python
def load_unified(name: str, *, cwd: Path | None = None) -> dict:
    """Resolve the full stack: common chain + named profile + extends chain.
    Returns raw merged dict ready for stanza extraction."""

def fab_stanza(merged: dict) -> FabricatorConfig: ...
def supplier_stanza(merged: dict) -> SupplierConfig: ...
def defaults_stanza(merged: dict) -> DefaultsConfig: ...
```
The merge engine: dicts deep-merge, lists replace, `null` values delete keys.
Circular `extends:` detection (raise ValueError on second visit to same name).
`common.jbom.yaml` files at all search-path levels are merged cumulatively
(lowest-priority first); named profile files use first-match-wins.
`policy.jbom.yaml` files are detected and logged as NOTICE (enforcement deferred per ADR 0008 D6).

**1b-2** Update `profile_search.py` to recognize `*.jbom.yaml` only.
Remove legacy `*.fab.yaml` / `*.supplier.yaml` / `*.defaults.yaml` suffix support.

**1b-3** Wire unified loader into existing public API:
- `fabricators.py:load_fabricator(fid)` → `unified.load_unified(fid)` → `fab_stanza()`
- `suppliers.py:load_supplier(sid)` → `unified.load_unified(sid)` → `supplier_stanza()`
- `defaults.py:load_defaults(name)` → `unified.load_unified(name)` → `defaults_stanza()`
The external API (`load_fabricator`, `load_supplier`, `load_defaults`) stays unchanged.
Internal callers transparently pick up the new loader.

**1b-4** Implement per-stanza `id:` override (ADR 0008 D3): a stanza-level `id:` key
overrides the file-level `id:` for CLI flag generation for that stanza type.
Update flag auto-generation to use stanza effective id.

**Acceptance criteria**:
- `load_fabricator("jlc")` resolves `jlc.jbom.yaml` (once that file exists — see 1d)
- `load_supplier("lcsc")` resolves `jlc.jbom.yaml` (via supplier stanza `id: lcsc`)
- `extends:` chain resolves correctly; circular chain raises ValueError
- `common.jbom.yaml` at multiple levels are all merged
- All existing tests pass (they still use legacy files until Phase 1d)

---

## Phase 1c — Field Reference System (ADR 0009)

**Objective**: Implement the canonical field reference language for `bom_columns`
and `--fields`.

**Driving decisions**: ADR 0009 D1–D7

### Tasks

**1c-1** Implement `src/jbom/config/fields.py`:
- `JBOM_NAMESPACE = "jbom"` and constants `SCH`, `PCB`, `INV`, `JBOM`
- Registry of jBOM-computed field names: `jbom:quantity`, `jbom:fabricator_part_number`,
  `jbom:smd`
- `is_jbom_computed(ref: str) -> bool`

**1c-2** Implement `src/jbom/config/field_ref.py`:
- `FieldRef` dataclass (namespace, field_name, raw_expression)
- `FieldRefResolver.resolve(ref: str, context: FieldContext) -> str`
  where `FieldContext` contains the current component/inventory/PCB field values
- Handles: plain field refs, `namespace:field` refs, `jbom:field` refs, expressions

**1c-3** Implement `src/jbom/config/field_expr.py`:
- `FieldExpressionEvaluator`:
  - Scan for `word:word` patterns, bind as `namespace_field` local variables
  - Bind unqualified source-data names via `field_precedence_policy`
  - Replace tokens in expression string
  - `ast.parse(expr, mode='eval')` — expression-only gate
  - Evaluate in restricted namespace: `{re: re, **compiled_transforms, **field_vars}`
  - `transforms:` stanza parsing: validate `expr` at load time via `ast.parse`, compile
    to single-argument callable
  - Collision detection: `NOTICE`-level `Diagnostic` on shadow; ERROR on duplicate-name
    in same file (emitted via existing `Diagnostic` infrastructure from #245)

**1c-4** Update `bom_workflow.py` and CLI `--fields` parser to delegate to
`FieldRefResolver` instead of the current ad-hoc field parsing.

**Acceptance criteria**:
- `FieldRefResolver.resolve("jbom:quantity", ctx)` returns the computed quantity
- `FieldRefResolver.resolve("pcb:footprint", ctx)` returns the PCB footprint value
- `FieldRefResolver.resolve("strip_kicad_library_prefix_from_value(pcb:footprint)", ctx)`
  returns `"C_0402"` for input `"Capacitors_SMD:C_0402"`
- `ast.parse("import os", mode='eval')` raises SyntaxError (confirmed rejected)
- All existing `--fields` tests pass

---

## Phase 1d — Built-in Config File Migration (ADR 0008/0009/0010)

**Objective**: Convert all built-in config files to `.jbom.yaml` format.
Remove legacy files and directories. All field references use the new notation.

**Driving decisions**: ADR 0008 D7/D8, ADR 0009 D1/D4, config-schema-audit smells S14/S15

### Files to create

**1d-1** `src/jbom/config/common.jbom.yaml` (built-in, shipped with jBOM):
```yaml
# Ambient defaults at every search-path level

transforms:
  strip_kicad_library_prefix_from_value:
    expr: "re.sub(r'^[^:]+:', '', value)"
    doc: "Remove KiCad library nickname. 'Capacitors_SMD:C_0402' → 'C_0402'"

fab:
  gerbers:
    layer_sets:
      standard_2_layer:
        - "F.Cu"
        - "B.Cu"
        - "F.Mask"
        - "B.Mask"
        - "F.Paste"
        - "B.Paste"
        - "F.Silkscreen"
        - "B.Silkscreen"
        - "Edge.Cuts"

defaults:
  field_precedence_policy:
    schematic_biased: [value, tolerance, footprint, ...]
    pcb_biased: [x, y, rotation, side, ...]
    inventory_biased: [manufacturer, manufacturer_part, fabricator_part_number, ...]
```

**1d-2** `src/jbom/config/generic.jbom.yaml` (no-flag fallback):
Consolidates content of:
- `fabricators/generic.fab.yaml` → `fab:` stanza
- `defaults/generic.defaults.yaml` → `defaults:` stanza (minus `field_precedence_policy` → moves to common.jbom.yaml; minus `category_route_rules` → moves to lcsc.jbom.yaml)
- `suppliers/generic.supplier.yaml` → `supplier:` stanza
- `presets/common.yaml` → `presets:` stanza
All field refs updated to use new notation (`jbom:quantity`, `inv:package`, etc.)

**1d-3** `src/jbom/config/jlc.jbom.yaml`:
- `fab:` stanza from `fabricators/jlc.fab.yaml` (field refs updated)
- `supplier:` stanza with `id: lcsc` (from `suppliers/lcsc.supplier.yaml` content)
- `defaults:` stanza with LCSC-specific parametric query fields and `category_route_rules`
  (moved from generic.defaults.yaml per smell S5)

**1d-4** `src/jbom/config/pcbway.jbom.yaml`:
From `fabricators/pcbway.fab.yaml`, field refs updated.

**1d-5** `src/jbom/config/seeed.jbom.yaml`:
From `fabricators/seeed.fab.yaml` + `suppliers/seeed.supplier.yaml`.

**1d-6** `src/jbom/config/mouser.jbom.yaml`:
From `suppliers/mouser.supplier.yaml`.

**1d-7** Remaining supplier files: `digikey.jbom.yaml`, `farnell.jbom.yaml`,
`newark.jbom.yaml` from corresponding `*.supplier.yaml` files.

### Files to remove
- `src/jbom/config/fabricators/` (entire directory)
- `src/jbom/config/suppliers/` (entire directory)
- `src/jbom/config/defaults/` (entire directory)
- `src/jbom/config/presets/` (entire directory)

### pyproject.toml updates
- Remove `*.fab.yaml`, `*.supplier.yaml`, `*.defaults.yaml`, `common.yaml` from package-data
- Add `*.jbom.yaml` to package-data (all new files included)

**Acceptance criteria**:
- `load_fabricator("jlc")` succeeds using only `jlc.jbom.yaml`
- `load_supplier("lcsc")` succeeds via `jlc.jbom.yaml` supplier stanza (`id: lcsc`)
- `load_supplier("mouser")` succeeds using `mouser.jbom.yaml`
- No `*.fab.yaml`, `*.supplier.yaml`, `*.defaults.yaml` files remain
- No `i:`, `p:`, `c:`, `k:` prefixes in any YAML file
- All functional tests pass (BDD features pass)
- `git grep -r "i:package\|p:k:\|c:tolerance"` returns zero results in config files

---

## Phase 1e — Documentation (ADR 0008 acceptance criteria for #250)

**Objective**: Update `docs/README.configuration.md` to document the new convention.

**Driving decisions**: ADR 0008 acceptance criteria for issue #250

### Tasks

**1e-1** Rewrite `docs/README.configuration.md`:
- New file format (`.jbom.yaml`, stanzas)
- Search path and `common.jbom.yaml` behaviour
- `extends:` inheritance and merge semantics
- Field reference language (`sch:`, `pcb:`, `inv:`, `jbom:`, expressions)
- `transforms:` stanza and naming convention
- Per-stanza `id:` override (`--jlc` vs `--lcsc` example)
- Config examples: single-fabricator, corporate fork, 4-layer override (Story A)
- Schema reference: `jbom config --schema` stub mention (deferred)

**1e-2** Add `jbom config --schema` command stub that calls
`FabricatorConfig.model_json_schema()` (even if just prints to stdout).

**Acceptance criteria**:
- Issue #250 acceptance criteria met: convention documented in `docs/README.configuration.md`
- `jbom bom --help` and `jbom search --help` reflect the new flag vocabulary

---

## PR and Merge Checklist

Before requesting merge of PR #267:
- [ ] All five phases committed on this branch
- [ ] All existing tests pass
- [ ] All BDD/functional tests pass (including new Stories A–E from ADR 0008)
- [ ] No `from_yaml_dict()` method exists
- [ ] No `Field(alias=...)` exists
- [ ] No legacy prefix notation (`i:`, `p:`, `c:`, `k:`) in any config file
- [ ] No legacy config file types (`*.fab.yaml`, `*.supplier.yaml`, etc.) remain
- [ ] `docs/README.configuration.md` updated (closes #250)
- [ ] CI/CD pipeline passes
- [ ] PR description updated to reflect implementation

## Supervisor Notes for Review

Key things to verify during implementation review:
- **1b-1 merge engine**: test null-delete, list-replace, dict deep-merge, circular extends
- **1c-3 expression evaluator**: verify `ast.parse(mode='eval')` correctly rejects statements
- **1d-3 jlc.jbom.yaml**: verify `--jlc` (fab) and `--lcsc` (search) both resolve to it
- **S1 unification** (field_synonyms): ensure the four-scope problem is actually resolved,
  not just shuffled
- **Pydantic `model_json_schema()`**: run it on each config class and verify the output
  is human-readable and complete
