# ADR 0015: Config Schema Vocabulary Audit
Date: 2026-02-25
Status: Accepted

## Context
Generated: 2026-05-11
Branch: feat/config-unified-schema
Status: Working document — feeds step 2.5 (design analysis) before Phase 1 implementation

Mechanical extraction of every YAML key name parsed by the three config loaders
(`fabricators.py`, `suppliers.py`, `defaults.py`) and present in the current
built-in YAML files. Basis for identifying schema smells before the Phase 1
built-in file migration.

The design lens criterion from ADR 0009: *every YAML key should correspond to
a named Python attribute; any key whose meaning requires reading Python to
understand is a smell.*

See also issue #269, which tracks the config unified schema redesign that this audit feeds.

## Decision

## Complete Key Inventory

### File-level (meta-directives, apply before stanzas are processed)

| Key | Type | Defined in | Notes |
|---|---|---|---|
| `extends:` | string | ADR 0008 D4 | Loads named parent; deep-merge before this file's content |
| `id:` | string | ADR 0008 D3 | Default CLI flag name for all stanzas in this file |

### `fab:` stanza

**Identity / metadata**

| Key | Python attr | Type | Notes |
|---|---|---|---|
| `id:` | `FabricatorConfig.id` | string | Stanza-level override of file `id:` |
| `name:` | `FabricatorConfig.name` | string | Human-readable display name |
| `description:` | `FabricatorConfig.description` | string | |
| `website:` | `FabricatorConfig.website` | string | |
| `dynamic_name:` | *(no Python attr — parsed ad-hoc in jbom.py legacy)* | bool | Signals "use manufacturer field as name" for Generic fab |
| `name_source:` | *(same)* | string | Which field to use when `dynamic_name` is true |

**Output format**

| Key | Python attr | Type | Notes |
|---|---|---|---|
| `bom_columns:` | `FabricatorConfig.bom_columns` | dict: header → field_ref | Output column header maps to field reference |
| `pos_columns:` | `FabricatorConfig.pos_columns` | dict: header → field_ref | Same for placement/CPL output |
| `pos_additive_default_fields:` | `FabricatorConfig.pos_additive_default_fields` | list of field_ref | Fields included when user says `--fields +foo` |
| `cpl_rotation_range:` | `FabricatorConfig.cpl_rotation_range` | [lo, hi] | Folds CPL angles into this 360° window; magic constraint: hi−lo==360 |
| `generate_designators:` | `FabricatorConfig.generate_designators` | bool | Whether `fab` run produces designators.csv |
| `gerbers:` | `FabricatorConfig.gerbers` | nested dict | See gerbers sub-keys below |

**Gerbers sub-keys**

| Key path | Type | Notes |
|---|---|---|
| `gerbers.layers:` | list of KiCad layer name strings | KiCad layer naming vocabulary; no connection to field reference system |
| `gerbers.naming.protel_extensions:` | bool | Whether to use Protel-style file extensions |
| `gerbers.drill.split_plated_holes:` | bool | |
| `gerbers.drill.map_format:` | string (`"gerber"`) | Undocumented vocabulary |

**Supplier / part number policy**

| Key | Python attr | Type | Notes |
|---|---|---|---|
| `suppliers:` | `FabricatorConfig.suppliers` | list of supplier ID strings | Ordered; position = priority |
| `part_number:` | `FabricatorConfig.part_number` | dict | Only key used: `header:` (the output BOM column header for the part number) |
| `field_synonyms:` | `FabricatorConfig.field_synonyms` | dict: canonical → {display_name, synonyms} | Three canonical keys: `fab_pn`, `supplier_pn`, `mpn` |
| `tier_overrides:` | `FabricatorConfig.tier_rules` | list of {conditions: [{field, operator, value?}]} | Mini DSL; operator values: `exists`, `truthy`, `not_empty`, `equals` |

**Presets / CLI**

| Key | Python attr | Type | Notes |
|---|---|---|---|
| `presets:` | `FabricatorConfig.presets` | dict: name → {description, fields: [field_ref]} | **COLLISION** with top-level `presets:` stanza |
| `cli_aliases:` | `FabricatorConfig.cli_aliases` | dict: {flags: [str], presets: [str]} | Auto-generates `--<id>` flag and `+<id>` preset |

**Manufacturing info (informational, not used in output logic)**

| Key | Python attr | Type | Notes |
|---|---|---|---|
| `pcb_manufacturing:` | `FabricatorConfig.pcb_manufacturing` | dict: {website, kicad_dru, gerbers} | Website + DRC file URL; unvalidated |
| `pcb_assembly:` | `FabricatorConfig.pcb_assembly` | dict: {website} | |

---

### `supplier:` stanza

**Identity / metadata**

| Key | Python attr | Type | Notes |
|---|---|---|---|
| `id:` | `SupplierConfig.id` | string | |
| `name:` | `SupplierConfig.name` | string | |
| `description:` | `SupplierConfig.description` | string | |
| `website:` | `SupplierConfig.website` | string | |

**Part number / URL**

| Key | Python attr | Type | Notes |
|---|---|---|---|
| `part_number:` | `SupplierConfig.part_number_pattern/example` | dict: {pattern, example} | **DIFFERENT STRUCTURE** from `fab.part_number` |
| `url_template:` | `SupplierConfig.url_template` | string with `{pn}` placeholder | |
| `search_url_template:` | `SupplierConfig.search_url_template` | string with `{query}` placeholder | |

**Field synonyms**

| Key | Python attr | Type | Notes |
|---|---|---|---|
| `field_synonyms:` | `SupplierConfig.field_synonyms` | dict: canonical → {display_name, synonyms} | Only `supplier_pn` in practice; **SAME STRUCTURE** as `fab.field_synonyms` but different scope |

**Search configuration**

| Key path | Python attr | Type | Notes |
|---|---|---|---|
| `search:` | (multiple attrs) | nested dict | **DIFFERENT STRUCTURE** from `defaults.search:` |
| `search.cache.ttl_hours:` | `SupplierConfig.search_cache_ttl_hours` | float | |
| `search.api.timeout_seconds:` | `SupplierConfig.search_timeout_seconds` | float | |
| `search.api.max_retries:` | `SupplierConfig.search_max_retries` | int | |
| `search.api.retry_delay_seconds:` | `SupplierConfig.search_retry_delay_seconds` | float | |
| `search.providers:` | `SupplierConfig.search_providers` | list of {type, ...extra} | `type` values: `mouser_api`, `jlcpcb_api`, `null_api` — hardcoded registry; `extra` is completely untyped |
| `search.fields:` | `SupplierConfig.search_fields` | list of strings | Output display fields for search results; **NOT field references** (ADR 0009 sense) — names like `supplier_part_number`, `price`, `stock_quantity` are ungrounded |
| `search.type_query_keywords:` | `SupplierConfig.search_type_query_keywords` | dict: category_token → keyword_str | Category tokens (RES, CAP...) map to search query keywords |

---

### `defaults:` stanza

**Component electrical defaults**

| Key | Python attr | Type | Notes |
|---|---|---|---|
| `domain_defaults:` | `DefaultsConfig.domain_defaults` | dict: category → {attribute: value} | e.g., `resistor.tolerance: "5%"` |
| `package_power:` | `DefaultsConfig.package_power` | dict: package_size → wattage_str | e.g., `"0402": "63mW"` — value strings untyped |
| `package_voltage:` | `DefaultsConfig.package_voltage` | dict: package_size → voltage_str | Same — value strings untyped |

**Parametric search**

| Key | Python attr | Type | Notes |
|---|---|---|---|
| `parametric_query_fields:` | `DefaultsConfig.parametric_query_fields` | dict: category → [field_names] | Field names are bare strings; not grounded in ADR 0009 field reference system |
| `category_route_rules:` | `DefaultsConfig.category_route_rules` | dict: category → {first_sort, second_sort_*} | **JLCPCB/LCSC internal catalog taxonomy strings** embedded in generic defaults |
| `search_excluded_categories:` | `DefaultsConfig.search_excluded_categories` | frozenset of category token strings | |

**Field synonym definitions**

| Key | Python attr | Type | Notes |
|---|---|---|---|
| `field_synonyms:` | `DefaultsConfig.field_synonyms` | dict: canonical → {display_name, synonyms} | General field names; **SAME KEY** third occurrence |

**Inventory schema contract**

| Key path | Python attr | Type | Notes |
|---|---|---|---|
| `inventory_schema:` | `DefaultsConfig.inventory_schema` | nested dict | Schema-within-a-stanza |
| `inventory_schema.canonical_fields:` | `InventorySchemaConfig.canonical_fields` | list of strings | |
| `inventory_schema.field_synonyms:` | `InventorySchemaConfig.field_synonyms` | dict: canonical → {display_name, synonyms} | **SAME KEY** fourth occurrence; inventory-specific scope |
| `inventory_schema.enrichment_bindings:` | `InventorySchemaConfig.enrichment_bindings` | dict: canonical → source_attr | Maps canonical key to Python InventoryItem attribute name; magic sentinel `__resolved_fabricator_part_number__` being retired |

**Search output configuration**

| Key path | Python attr | Type | Notes |
|---|---|---|---|
| `search:` | (multiple attrs) | nested dict | **DIFFERENT STRUCTURE** from `supplier.search:` |
| `search.output_fields.default:` | `DefaultsConfig.search_output_fields_default` | list of field names | Output fields for `jbom search` display — not clearly field references |
| `search.package_tokens:` | `DefaultsConfig.search_package_tokens` | list of package size strings | Used for package intent matching in search heuristics |

**Enrichment / Mode A classification**

| Key path | Python attr | Type | Notes |
|---|---|---|---|
| `enrichment_attributes:` | `DefaultsConfig.enrichment_attributes` | dict: category → {show_in_mode_a, suppress} | |
| `enrichment_attributes.<cat>.show_in_mode_a:` | `EnrichmentCategoryConfig.show_in_mode_a` | list of attribute names | **jBOM-internal concept** ("Mode A") leaked into config vocabulary |
| `enrichment_attributes.<cat>.suppress:` | `EnrichmentCategoryConfig.suppress` | list of attribute names | |

**Component identity**

| Key | Python attr | Type | Notes |
|---|---|---|---|
| `component_id_fields:` | `DefaultsConfig.component_id_fields` | dict: category → [field_names] | Optional fields contributing to ComponentID hash |
| `field_precedence_policy:` | `DefaultsConfig.field_precedence_policy` | dict: policy_key → [field_names] | Resolve ambiguous bare names; policy keys: `schematic_biased`, `pcb_biased`, `inventory_biased` |

---

### `presets:` top-level stanza

| Structure | Notes |
|---|---|
| dict: preset_name → {description, fields: [field_ref]} | Global presets; currently in `presets/common.yaml` wrapping a `presets:` key — a stanza wrapping a key with the same name |

### `transforms:` top-level stanza (new, ADR 0009)

| Structure | Notes |
|---|---|
| dict: transform_name → {expr, doc} | `expr` is a Python expression string; `doc` is human-readable |

---

## Smell Catalogue

### S1 — `field_synonyms:` in four contexts with one name

Appears in: `fab:`, `supplier:`, `defaults:`, `defaults.inventory_schema`

Same YAML structure `{canonical: {display_name, synonyms}}` but the "canonical
key" means something different in each context:
- `fab:` — fabricator role names (`fab_pn`, `supplier_pn`, `mpn`) for part number field resolution
- `supplier:` — supplier role name (`supplier_pn`) for this supplier's part number
- `defaults:` — general component/inventory field names (`manufacturer`, `mpn`, etc.)
- `defaults.inventory_schema:` — inventory CSV column canonical names (`inventory_ipn`, `manufacturer_part`, etc.)

**Severity: structural** — four different semantic scopes that happen to share a structure.
The question for step 2.5: are these really one concept or four? If one concept, it belongs in
one place in the unified schema. If four, they should have four distinct key names.

### S2 — `part_number:` with two incompatible structures

- `fab.part_number:` → `{header: str}` — "what column header to use in the BOM output for the part number"
- `supplier.part_number:` → `{pattern: regex, example: str}` — "how to validate a part number string"

Same name, completely different structure and semantics.

**Severity: rename** — `fab.part_number:` could become `fab_pn_column:` or fold into `field_synonyms.fab_pn.display_name` (it's partially redundant with that); `supplier.part_number:` could become `supplier.part_number_format:` or `validation:`.

### S3 — `presets:` naming collision

- Top-level `presets:` stanza: global cross-fabricator presets
- `fab.presets:`: fabricator-specific presets

Same name, same structure, different scope. The top-level `presets:` in `presets/common.yaml`
is also currently wrapped in a `presets:` key — a file whose top-level content is `presets: {...}`.

**Severity: structural** — either unify them (fabricator presets inherit from global presets)
or differentiate them (rename one). The `presets/common.yaml` wrapper is also a smell.

### S4 — `search:` with two completely different structures

- `supplier.search:` — API runtime configuration (cache, api, providers, type_query_keywords, fields)
- `defaults.search:` — BOM/search output field configuration (output_fields, package_tokens)

**Severity: rename** — `defaults.search:` could become `defaults.search_output:` or
`defaults.catalog_search:`. The names should reflect what they configure, not just "search".

### S5 — `category_route_rules:` is supplier-specific content in `defaults:`

Contains JLCPCB/LCSC internal catalog taxonomy strings (`"Chip Resistor - Surface Mount"`, etc.).
This is supplier-specific knowledge and belongs in the `supplier:` stanza or a
supplier-specific `defaults:` extension, not in generic defaults.

**Severity: structural** — belongs in the LCSC supplier config, not in `generic.defaults.yaml`.

### S6 — `show_in_mode_a:` leaks an internal jBOM concept into config vocabulary

"Mode A" is a jBOM workflow implementation concept. Config authors should not need to know
what "Mode A" is. The key name is opaque without reading jBOM source.

**Severity: rename** — rename to something that describes the *behavior*, not the jBOM-internal
mode. e.g., `prompt_for_confirmation:` or `designer_review_attributes:`.

### S7 — `search.fields:` in supplier is not a field reference list

`generic.supplier.yaml` has `search.fields: [supplier_part_number, price, stock_quantity, ...]`.
These are not `namespace:field` references (ADR 0009); they're... search result display field names.
Not grounded in the field reference system.

**Severity: structural** — these field names need to be connected to the ADR 0009 field
reference language or given their own explicit vocabulary.

### S8 — `providers.extra` is a completely untyped bag

`search.providers[n].type` is a registered provider type string; everything else in a provider
config is `extra: dict[str, Any]` — the schema has no idea what's valid inside a provider config.

**Severity: structural** — each provider type could declare its own sub-schema, but currently
there's no mechanism for this.

### S9 — `dynamic_name:` + `name_source:` are special-casing for one fabricator

These exist only in `generic.fab.yaml` to handle the "Generic" fabricator's behavior of
using the matched manufacturer's name as its own display name. This is a one-off hack
embedded in the schema.

**Severity: design smell** — either generalize this concept (any fabricator can be named
dynamically from a field) or remove it and handle "Generic" behavior in Python directly.

### S10 — `cpl_rotation_range:` has a magic validation constraint in Python only

The constraint that `hi - lo == 360` is validated in `FabricatorConfig.from_yaml_dict()` but
not documented in any schema. A user who writes `[0, 180]` gets an error with no explanation
in the schema documentation.

**Severity: documentation** — the constraint should be in the schema spec, not just in Python.

### S11 — `enrichment_bindings:` in `inventory_schema:` maps to Python attribute names

Values like `"__resolved_fabricator_part_number__"` (being retired) and `"ipn"`, `"mfgpn"` are
Python `InventoryItem` attribute names. The YAML config directly references Python implementation
internals.

**Severity: structural** — these bindings should reference the ADR 0009 field reference system,
not Python attribute names.

### S12 — `gerbers.layers:` uses KiCad layer name strings with no validation schema

Values like `"F.Cu"`, `"B.Mask"` are from KiCad's internal layer naming convention. There is
no documented vocabulary of valid layer names in the schema.

**Severity: documentation** — needs a reference to valid KiCad layer names.

### S13 — `tier_overrides.conditions.operator:` is an undocumented mini-DSL

Valid values: `exists`, `truthy`, `not_empty`, `equals`. This vocabulary exists only in Python.

**Severity: documentation** — needs explicit schema documentation.

### S14 — Old field notation in built-in YAML files

`pcbway.fab.yaml` uses `i:package` (old prefix) in `bom_columns` and `presets.fields`.
This pre-dates ADR 0009 and must be migrated as part of Phase 1.

**Severity: migration** — mechanical fix during Phase 1 built-in file migration.

### S15 — `presets.fields:` values use pre-ADR 0009 notation throughout

All built-in `presets.fields:` lists use bare names like `"reference"`, `"quantity"`,
`"fabricator_part_number"` — which must now be `"sch:Reference"`, `"jbom:quantity"`,
`"jbom:fabricator_part_number"` under the ADR 0009 field reference system.

**Severity: migration** — mechanical update during Phase 1.

---

## Consequences

## Summary: Rename-only vs. Structural Smells

| Smell | Type | Notes |
|---|---|---|
| S2 `part_number:` collision | rename | two distinct concepts need two names |
| S4 `search:` collision | rename | `defaults.search:` → `search_output:` or similar |
| S6 `show_in_mode_a:` | rename | replace with behavior-describing name |
| S10 `cpl_rotation_range:` constraint | documentation | document the 360° constraint in schema spec |
| S12 `gerbers.layers:` | documentation | reference KiCad layer vocabulary |
| S13 `tier_overrides.conditions.operator:` | documentation | document operator vocabulary |
| S14, S15 old notation in YAML files | migration | mechanical Phase 1 work |
| S9 `dynamic_name:` + `name_source:` | design smell | generalize or remove |
| S1 `field_synonyms:` 4× | structural | clarify whether 1 concept or 4; unify if 1 |
| S3 `presets:` collision | structural | unify or differentiate scopes |
| S5 `category_route_rules:` placement | structural | move to supplier stanza |
| S7 `search.fields:` ungrounded | structural | connect to ADR 0009 field references |
| S8 `providers.extra` untyped | structural | per-provider sub-schema mechanism |
| S11 `enrichment_bindings:` Python attrs | structural | replace with field reference language |

The structural smells (bottom half of table) are the input to step 2.5 design analysis.
The rename/documentation/migration smells can be handled mechanically during Phase 1
without a new ADR.

## Provenance

Normalized into formal ADR format on 2026-05-25 under issue #300.
Source file(s):

- `docs/dev/architecture/config-schema-audit.md` (content preserved verbatim)
