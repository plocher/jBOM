# Phase 4: Inventory Schema + Enrichment Pipeline Fix

## Problem
The inventory CSV uses `Distributor + DPN` columns where DPN meaning varies by row (LCSC code vs Mouser code vs SPCoast code). This creates unsolvable ambiguity in the matching/enrichment pipeline — jBOM can't determine what a DPN means without conditional logic per-row.

The `_enrich_entry()` method also has attribute key mismatches (`lcsc_part` vs `lcsc`) and missing fields (`package`, `smd`, `fabricator_part_number`).

## Design Decision
**Replace `Distributor + DPN` with explicit per-distributor columns.** One row per IPN, all sourcing info visible:

```
IPN, ..., MPN, Manufacturer, LCSC, Mouser, DigiKey, ...
RES_330_0603, ..., 0603WAJ0331T5E, UNI-ROYAL, C25231, 303-xxx, , ...
```

This eliminates:
- DPN interpretation ambiguity
- Row duplication per IPN
- Need for `catalog_distributors` or affinity filter concepts
- Conditional DPN→fab_pn logic

Fabricator configs map directly to columns: JLC's `fab_pn` synonyms = ["LCSC"] → finds the LCSC column. PCBWay uses MPN. Tier rules work naturally.

## Design Principles
- **Tolerant synonym resolution**: Fab profiles ship with comprehensive supplier synonym lists (LCSC, Mouser, DigiKey, Arrow, Farnell, etc.). Missing inventory columns resolve to empty — no errors. Users never need to edit fab profiles for normal use.
- **Supplier profiles are separate entities**: Supplier-specific knowledge (URL templates, PN validation, catalog search) belongs in `*.supplier.yaml` profiles, not fabricator configs. Fabricator configs reference suppliers implicitly through field_synonyms. See parallel task: `PHASE_4S_PLAN.md`.

## Changes

### 1. Inventory CSV schema migration
**File**: `examples/SPCoast-INVENTORY.csv`

Replace columns `Distributor, DPN, DPNLink` with `LCSC, Mouser` (and optionally `DigiKey`).

Migration logic:
- Group rows by IPN
- For each IPN group: merge into single row, pivot DPN by Distributor
    - `Distributor=JLC, DPN=C25231` → `LCSC=C25231`
    - `Distributor=Mouser, DPN=303-xxx` → `Mouser=303-xxx`
    - `Distributor=SPCoast, DPN=EDG-104` → drop (SPCoast internal codes, not useful in BOM output)
- Keep one Priority per IPN (lowest/best from merged rows)
- Keep MPN, Manufacturer, and all component identity fields from either row

Expected result: ~105 rows collapses to ~75-80 unique IPNs (rough estimate based on duplicate IPNs with different distributors).

### 2. InventoryReader cleanup
**File**: `src/jbom/services/inventory_reader.py`

- Remove `"DPN"` from the `lcsc` fallback list (line 301) — `item.lcsc` now comes directly from the `LCSC` column
- Remove `Distributor` → `item.distributor` mapping (column no longer exists)
- Remove `"Distributor Part Number"` and related synonyms from `item.distributor_part_number` mapping
- `item.lcsc` maps from `["LCSC", "LCSC Part", "LCSC Part #"]` — no DPN fallback
- All per-distributor columns (LCSC, Mouser, etc.) survive into `raw_data` for field_synonym resolution

### 3. Fabricator config updates
**Files**: `src/jbom/config/fabricators/{jlc,pcbway,generic,seeed}.fab.yaml`

JLC (`jlc.fab.yaml`):
- `fab_pn` synonyms: remove "DPN" if present. Keep ["LCSC", "LCSC Part", "LCSC Part #", ...]
- `supplier_pn` synonyms: remove "DPN". Add ["Mouser", "Mouser Part Number", "DigiKey", "DigiKey Part Number", "Arrow", "Farnell", "Newark", "Stock Code"]
- Tier rules: unchanged (fab_pn → supplier_pn → mpn)

PCBWay (`pcbway.fab.yaml`):
- Remove `fab_pn` section (PCBWay has no catalog)
- `supplier_pn` synonyms: ["Mouser", "Mouser Part Number", "DigiKey", "DigiKey Part Number", "Arrow", "Farnell", "Newark", "Stock Code"]
- `mpn` synonyms: ["MPN", "MFGPN", "Manufacturer Part Number"]
- `bom_columns`: map "Manufacturer Part Number" → `fabricator_part_number` (PCBWay wants MPN, not DPN)

Generic (`generic.fab.yaml`):
- `supplier_pn` synonyms: remove "DPN". Add ["LCSC", "LCSC Part #", "Mouser", "Mouser Part Number", "DigiKey", "DigiKey Part Number", "Arrow", "Farnell", "Newark", "Part Number", "P/N", "Stock Code"] — generic uses any PN available
- Tier rules: unchanged

Seeed (`seeed.fab.yaml`):
- Similar pattern to JLC/PCBWay — remove DPN, add explicit distributor columns with comprehensive defaults

### 4. Enrichment pipeline fix
**File**: `src/jbom/services/inventory_matcher.py` — `_enrich_entry()`

Current `_enrich_entry()` uses hardcoded field names. Fix to:
- Resolve `fabricator_part_number` from matched item's `raw_data` via fabricator config field_synonyms. Walk canonical fields in tier order: `fab_pn` → `supplier_pn` → `mpn`. First non-empty value wins.
- This requires passing the fabricator config (or a resolver function) into `_enrich_entry()`.
- Fix attribute key: `"lcsc_part"` → `"lcsc"`
- Add missing attributes: `"package": item.package`, `"smd": item.smd`
- Add `"fabricator_part_number"` from resolved value above

**File**: `src/jbom/services/inventory_matcher.py` — `enhance_bom_with_inventory()`
- Thread the fabricator config through to `_enrich_entry()` (it's already loaded in `_filter_by_fabricator()`)

### 5. FabricatorInventorySelector cleanup
**File**: `src/jbom/services/fabricator_inventory_selector.py`

- Remove `_passes_fabricator_filter()` method (affinity filter on `item.fabricator`) — no longer needed with single-row-per-IPN model
- Or simplify to always return True
- `_normalized_raw_data()` and `_assign_tier()` work unchanged — field_synonyms now map directly to explicit columns

### 6. Delete stale tests
**Files to delete**:
- `tests/integration/test_workflows.py` — references non-existent `jbom.workflows.bom_workflows`
- `tests/integration/test_schematic_reader_integration.py` — wrong import paths, trivial assertions

### 7. Update/create tests
- Update `tests/services/matchers/test_inventory_matcher.py` for new `_enrich_entry()` signature
- Update `tests/integration/test_service_composition.py` — inventory fixtures need new column format
- Update `tests/integration/test_target_inventory_contract.py` — if it uses SPCoast-INVENTORY.csv
- Update BDD fixtures if any use Distributor/DPN columns
- Add test: JLC enrichment resolves LCSC code as fabricator_part_number
- Add test: PCBWay enrichment resolves MPN as fabricator_part_number
- Add test: same IPN row serves both JLC and PCBWay with different fabricator_part_number values

### 8. Retire ComponentInventoryMatcher
**File to delete**: `src/jbom/services/component_inventory_matcher.py`

- Verify no remaining imports (should only be `inventory.py` CLI after migrating it)
- Delete after `inventory` CLI is migrated to sophisticated pipeline

## Execution Order
1. Migrate inventory CSV (foundational — everything depends on this)
2. Update fabricator configs (remove DPN, add comprehensive supplier synonym lists)
3. Fix InventoryReader (remove DPN hack, Distributor mapping)
4. Fix enrichment pipeline (fabricator_part_number resolution, key names, package/smd)
5. Simplify FabricatorInventorySelector (remove affinity filter)
6. Delete stale tests + update test fixtures
7. Retire ComponentInventoryMatcher
8. Validate against real projects

**Parallel track**: Phase 4S (Supplier Profiles) — independent, no code dependencies on steps 1-8. See `PHASE_4S_PLAN.md`.

## Validation
```bash
# Core-wt32-eth0 with JLC: LCSC codes should appear
PYTHONPATH=src python -m jbom bom /Users/jplocher/Dropbox/KiCad/projects/Core-wt32-eth0 -o console --inventory /Users/jplocher/Dropbox/KiCad/jBOM/examples/SPCoast-INVENTORY.csv --fabricator jlc -v
# Same project with PCBWay: MPN should appear, no LCSC codes
PYTHONPATH=src python -m jbom bom /Users/jplocher/Dropbox/KiCad/projects/Core-wt32-eth0 -o console --inventory /Users/jplocher/Dropbox/KiCad/jBOM/examples/SPCoast-INVENTORY.csv --fabricator pcbway -v
# Generic: MPN or best available
PYTHONPATH=src python -m jbom bom /Users/jplocher/Dropbox/KiCad/projects/Core-wt32-eth0 -o console --inventory /Users/jplocher/Dropbox/KiCad/jBOM/examples/SPCoast-INVENTORY.csv -v
# All tests
PYTHONPATH=src python -m pytest tests/ -q --tb=short
python -m behave --format progress
```
