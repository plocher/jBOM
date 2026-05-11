# ADR 0010: Pydantic BaseModel as Config Schema Binding Mechanism
Date: 2026-05-11
Status: Proposed
Related: ADR 0008, ADR 0009, docs/dev/architecture/config-schema-audit.md

## Context

ADR 0009 established the design lens criterion:

> *Every YAML key should correspond to a named Python attribute; any key whose
> meaning requires reading Python to understand is a schema design smell.*

The current config loading system violates this principle systematically. All
three loaders (`fabricators.py`, `suppliers.py`, `defaults.py`) hand-write
`from_yaml_dict()` methods that extract YAML keys as raw string literals:

```python
pid = data.get("id", default_id)
tier_overrides = data.get("tier_overrides")   # YAML key
# ...
return FabricatorConfig(
    tier_rules=_derive_tier_rules(tier_overrides),  # Python attr: different name
```

The schema audit (`config-schema-audit.md`) found 15 smells in the current
vocabulary, including `tier_overrides` (YAML) → `tier_rules` (Python) as a
representative example of the name-divergence anti-pattern. The root cause is
that there is **no formal binding mechanism** between YAML keys and Python
types — the correspondence is maintained by convention and reading code.

The question crystallized during design review: *how are config data models
tagged as "exported for use in config files", and how is that relationship
enforced?*

## Decision Drivers

- The Python class definition should BE the schema — not a separate spec that
  can drift from the implementation.
- Every field visible in a `.jbom.yaml` file should correspond to a named
  Python attribute with no translation layer.
- Computed/derived Python attributes that do NOT correspond to YAML keys must
  be structurally distinguished from YAML-facing fields, not just by convention.
- The schema should be machine-readable without running jBOM — for IDE
  completion, validation tooling, and documentation generation.
- `from_yaml_dict()` methods (130+ lines in `fabricators.py` alone) should not
  exist; parsing should be derived from the type definition.

## Options Considered

### Option 1 — Naming convention + generic reflection-based loader (rejected)

Enforce that all Python attribute names match YAML keys by convention. Write a
single generic `from_yaml_dict()` base that iterates `dataclasses.fields()` and
calls `data.get(field.name)`. The contract is enforced at runtime (mismatches
produce silently missing data; tests catch this).

Rejected because: convention is not enforcement. The discrepancy between
`tier_overrides` and `tier_rules` existed as a named convention violation for
years without being caught. A structural mechanism is needed, not a better
convention.

### Option 2 — Dataclass field metadata annotations (rejected)

Add `field(metadata={"yaml_key": "tier_overrides"})` to allow Python attribute
names to differ from YAML keys while maintaining an explicit mapping.

Rejected because: this perpetuates the dual-naming problem in annotated form.
The audit (S11, `enrichment_bindings` → Python attribute names) shows exactly
the kind of confusion this produces. Allowing divergence — even explicitly —
means config authors must still learn both names.

### Option 3 — Pydantic v2 `BaseModel` (accepted — this ADR)

Replace all config `@dataclass` classes with Pydantic `BaseModel`. The model
field name IS the YAML key by definition. `model_validate(yaml_dict)` replaces
all `from_yaml_dict()` methods. See Decision Details below.

## Decision

**Adopt Pydantic v2 `BaseModel` for all config schema classes.**

The formal answer to "how are data models tagged for export": **they are Pydantic
fields**. That is the complete, unambiguous tag. `@computed_field` is the only
way to have a Python attribute that is NOT a YAML key. There is no other
distinction to maintain.

Key properties:
- Python field name = YAML key name. No exceptions, no aliases except for
  explicitly temporary legacy transitions (see Decision Details).
- `@computed_field` for derived values — structurally excluded from YAML parsing.
- `model_validate(yaml_dict)` replaces every `from_yaml_dict()` method.
- `model_json_schema()` provides machine-readable schema for free — directly
  feeds the planned `jbom config --schema` command.
- `model_fields_set` tracks which fields were explicitly provided vs. defaulted
  — useful for diagnostic output (which config level set which value).

### Decision Details

#### D1. Python field name = YAML key name

```python
class FabricatorConfig(BaseModel):
    id: str
    name: str
    bom_columns: Dict[str, str] = {}
    # Renamed from Python 'tier_rules' to match YAML 'tier_overrides'
    tier_overrides: List[TierOverride] = []
    cpl_rotation_range: Optional[Tuple[float, float]] = None
    generate_designators: bool = False
```

No `data.get("tier_overrides")` string literal anywhere. The field name IS the
contract.

#### D2. `@computed_field` for non-YAML Python attributes

Any Python attribute that should NOT appear in the YAML is explicitly declared
as a computed field. The design lens violation becomes structurally impossible:

```python
class FabricatorConfig(BaseModel):
    tier_overrides: List[TierOverride] = []

    @computed_field
    @cached_property
    def tier_rules(self) -> List[TierRule]:
        """Derived from tier_overrides at construction time. Not a YAML key."""
        return _derive_tier_rules(self.tier_overrides)
```

`@computed_field` is self-documenting: this is NOT in the YAML. No comment
needed to explain the discrepancy.

#### D3. `model_validate()` replaces `from_yaml_dict()`

```python
# Before
config = FabricatorConfig.from_yaml_dict(data, default_id=fid)

# After
config = FabricatorConfig.model_validate(data)
```

Custom validation logic that currently lives in `from_yaml_dict()` migrates to
`@field_validator` and `@model_validator`:

```python
@field_validator("cpl_rotation_range")
@classmethod
def validate_rotation_range(cls, v):
    if v is not None and v[1] - v[0] != 360:
        raise ValueError("cpl_rotation_range must span exactly 360°")
    return v
```

The constraint is now visible in the class definition, not buried in a method.

#### D4. `Field(alias=...)` for transitional legacy key renames

When a YAML key cannot be renamed immediately (e.g., `tier_overrides` was the
YAML key and Python used `tier_rules`), `Field(alias=...)` makes the discrepancy
explicit and temporary:

```python
# Transitional only — must have a cleanup issue filed
tier_overrides: List[TierOverride] = Field(
    default=[],
    alias="tier_overrides",   # legacy YAML key; Python attr must be renamed next
)
```

No silent divergence. No "read Python to understand YAML" mystery.

#### D5. `model_json_schema()` as the authoritative schema

```python
import json
print(json.dumps(FabricatorConfig.model_json_schema(), indent=2))
```

This output feeds:
- IDE completion for `.jbom.yaml` files (JSON Schema → VS Code yaml extension)
- The planned `jbom config --schema` command (ADR 0008 Deferred 5)
- Config documentation generation

The schema is not a separate file to maintain — it is generated from the model.

## Consequences

### Positive
- The design lens criterion is structurally enforced, not merely stated.
- Adding a new YAML config key requires only adding a Python field — no
  separate string literal, no `from_yaml_dict()` edit, no hand-written
  validation unless the validation is complex.
- `@computed_field` makes the YAML-vs-computed distinction explicit in the
  code at the point of definition.
- `model_json_schema()` is free — enables IDE support, `jbom config --schema`,
  documentation generation.
- All `from_yaml_dict()` methods (130+ lines in fabricators.py alone) collapse
  to `model_validate()` plus field validators.
- `model_fields_set` provides diagnostic visibility into which config level
  contributed each value.
- Schema audit smells S11 (`enrichment_bindings` → Python attr names) and all
  `tier_overrides`-style mismatches are structurally eliminated.

### Negative / Tradeoffs
- Pydantic v2 becomes a required runtime dependency. Currently jBOM requires
  only `sexpdata` and `PyYAML`. Adding Pydantic adds ~3 MB; it is pure Python
  with optional Rust acceleration (pydantic-core) and widely available on PyPI.
- Migration of the three loader files is mechanical but non-trivial — each
  `@dataclass` becomes a `BaseModel`, each `from_yaml_dict()` is replaced with
  validators. Estimated scope: `fabricators.py`, `suppliers.py`, `defaults.py`
  plus their tests.
- `@computed_field` requires `cached_property` for fields that are expensive
  to compute or that reference other fields. This is idiomatic Pydantic v2 but
  requires understanding the model lifecycle.

### Risks and Mitigations
- **Risk**: Pydantic v2 breaks compatibility with KiCad's bundled Python
  (relevant for PCM plugin packaging per ADR 0007).
  **Mitigation**: Pydantic v2 supports Python 3.8+; KiCad 8/9 ships Python
  3.11+. Pydantic is pure Python (pydantic-core is optional but provides
  significant speedup). It can be vendored into the PCM archive alongside
  `sexpdata` and `PyYAML` per the ADR 0007 vendoring strategy.
- **Risk**: Pydantic's `model_validate()` behavior for extra/unknown fields.
  **Mitigation**: Set `model_config = ConfigDict(extra="ignore")` on all
  config models. Unknown YAML keys are silently ignored — same behavior as the
  current `data.get()` approach. A debug/verbose mode can warn on unknown keys.
- **Risk**: `@computed_field` order-of-operations issues during validation.
  **Mitigation**: Use `@model_validator(mode='after')` for fields that depend
  on other fields being validated first. This is standard Pydantic v2 practice.

## Schema Audit Smells Resolved

This ADR directly resolves the following smells from `config-schema-audit.md`:

| Smell | Resolution |
|---|---|
| `tier_overrides` (YAML) ≠ `tier_rules` (Python) | Python attr renamed to match YAML key |
| `from_yaml_dict()` string literals | Replaced by field names |
| `cpl_rotation_range` constraint undocumented | Moves to `@field_validator` |
| `tier_overrides.conditions.operator` undocumented DSL | Moves to `TierOperator` enum with Pydantic validation |
| `enrichment_bindings` references Python attr names (S11) | Replaced with field reference language in Phase 1b |
| Any future YAML key that diverges from Python attr name | Structurally impossible without `Field(alias=...)` |

## Implementation Phases

**Phase 1 (this feature branch, alongside ADR 0008/0009 Phase 1)**

- Add `pydantic>=2.0` to `pyproject.toml` dependencies and PCM vendoring list.
- Migrate `FabricatorConfig` → Pydantic `BaseModel`:
  - Rename `tier_rules` attr to `tier_overrides` (or keep computed as D2)
  - Move validation from `from_yaml_dict()` to `@field_validator` / `@model_validator`
  - Add `model_config = ConfigDict(extra="ignore")`
- Migrate `SupplierConfig` → Pydantic `BaseModel`
- Migrate `DefaultsConfig` → Pydantic `BaseModel`
- Migrate supporting types: `FieldSynonym`, `TierCondition`, `TierRule`,
  `SearchProviderConfig`, `InventorySchemaConfig`, `EnrichmentCategoryConfig`
- Introduce `TierOperator` enum (replaces undocumented string DSL)
- Update all call sites: `from_yaml_dict()` → `model_validate()`
- Unit tests: verify `model_json_schema()` output is stable (schema regression test)

**Phase 2 (alongside ADR 0008/0009 Phase 1b)**
- Update `docs/README.configuration.md` with generated schema reference.
- Wire `model_json_schema()` output to a `jbom config --schema` command stub.

## References
- ADR 0008: unified `*.jbom.yaml` container format
- ADR 0009: field reference system (design lens criterion)
- `docs/dev/architecture/config-schema-audit.md`: schema vocabulary audit
- `src/jbom/config/fabricators.py`: primary migration target
- `src/jbom/config/suppliers.py`: migration target
- `src/jbom/config/defaults.py`: migration target
- Pydantic v2 documentation: https://docs.pydantic.dev/latest/
- `pyproject.toml`: dependency declarations + PCM vendoring
