# Phase 4: Inventory Schema + Enrichment Pipeline Fix

## Overview
Replace the ambiguous `Distributor + DPN` inventory model with explicit per-distributor columns (LCSC, Mouser, etc.), fix the enrichment pipeline, and clean up dead code.

**Design context**: See `docs/workflow/planning/PHASE_4_PLAN.md` for the design rationale.
**Prerequisites**: Phase 3 complete (PR #63)
**Branch pattern**: `feature/issue-N-brief-description` (create GitHub issue first)
**Test counts at start**: 231 pytest (8 skipped) + 192 BDD scenarios

## Key Design Decision
The inventory CSV changes from multi-row-per-IPN with `Distributor, DPN, DPNLink` to single-row-per-IPN with explicit `LCSC, Mouser` columns. Fabricator configs map directly to these columns via `field_synonyms`. No affinity filter, no conditional DPN logic, no row duplication.

## Task Dependency Graph
```
Task 4.1 (migrate inventory CSV)     — foundational, do first
    ↓
Task 4.2 (update fab configs)        — depends on new column names
Task 4.3 (fix InventoryReader)       — depends on new columns
    ↓
Task 4.4 (fix enrichment pipeline)   — depends on 4.2 + 4.3
Task 4.5 (simplify selector)         — depends on 4.1
    ↓
Task 4.6 (delete stale tests)        — independent, anytime
Task 4.7 (update test fixtures)      — after 4.1-4.5
Task 4.8 (retire old matcher)        — after 4.7
Task 4.9 (end-to-end validation)     — capstone
Task 4.10 (match diagnostics CLI)    — independent
```

---

## Task 4.1: Migrate Inventory CSV Schema

**Goal**: Replace `Distributor, DPN, DPNLink` columns with explicit `LCSC, Mouser` columns. One row per IPN.

**File**: `/Users/jplocher/Dropbox/KiCad/jBOM/examples/SPCoast-INVENTORY.csv`

**Current columns**: `IPN,Name,Keywords,Category,SMD,Value,Type,Description,Package,Form,Pins,Pitch,Tolerance,V,A,W,Angle,Wavelength,mcd,Frequency,Distributor,DPN,DPNLink,Priority,Status,Manufacturer,MPN,Symbol,Footprint,Datasheet`

**New columns**: `IPN,Name,Keywords,Category,SMD,Value,Type,Description,Package,Form,Pins,Pitch,Tolerance,V,A,W,Angle,Wavelength,mcd,Frequency,LCSC,Mouser,Priority,Status,Manufacturer,MPN,Symbol,Footprint,Datasheet`

**Migration rules**:
- Group rows by IPN
- For each IPN group, merge into a single row:
  - `Distributor=JLC, DPN=C25231` → `LCSC=C25231`
  - `Distributor=Mouser, DPN=303-xxx` → `Mouser=303-xxx`
  - `Distributor=SPCoast` → SPCoast DPN dropped (internal code, not useful in BOM)
  - Empty Distributor → both columns empty
- Priority: keep lowest (best) value from merged rows
- Component identity fields (Value, Package, MPN, Manufacturer, etc.): prefer non-empty values from any row

**Verification**: Row count should decrease (IPNs like SWI_EDG-104 that had 2 rows collapse to 1). All IPNs should still be present.

**Estimated effort**: 30-60 minutes (write a migration script or do manually)

---

## Task 4.2: Update Fabricator Configs

**Goal**: Remove DPN from `field_synonyms`, add explicit distributor column names.

**Files**: `src/jbom/config/fabricators/{jlc,pcbway,generic,seeed}.fab.yaml`

**JLC** (`jlc.fab.yaml`):
- `fab_pn` synonyms: keep ["LCSC", "LCSC Part", "LCSC Part #", "LCSC Part Number", "JLC", "JLC Part", "JLC Part #", "JLC PCB", "JLC PCB Part", "JLC PCB Part #", "JLC_PCB Part #"]
- `supplier_pn` synonyms: replace entire list with ["Mouser", "Mouser Part Number", "DigiKey", "DigiKey Part Number", "Arrow", "Farnell", "Newark", "Stock Code"]
- `mpn` synonyms: unchanged ["MPN", "MFGPN", "Manufacturer Part Number"]

**PCBWay** (`pcbway.fab.yaml`):
- Remove `fab_pn` section entirely (PCBWay has no catalog)
- `supplier_pn` synonyms: ["Mouser", "Mouser Part Number", "DigiKey", "DigiKey Part Number", "Arrow", "Farnell", "Newark", "Stock Code"]
- `mpn` synonyms: unchanged
- `bom_columns`: change `"Distributor Part Number": "fabricator_part_number"` → `"Manufacturer Part Number": "fabricator_part_number"`

**Generic** (`generic.fab.yaml`):
- `supplier_pn` synonyms: replace with ["LCSC", "LCSC Part #", "Mouser", "Mouser Part Number", "DigiKey", "DigiKey Part Number", "Arrow", "Farnell", "Newark", "Part Number", "P/N", "Stock Code"]
- Remove all DPN references

**Seeed** (`seeed.fab.yaml`):
- `supplier_pn` synonyms: remove DPN, add ["Mouser", "Mouser Part Number", "DigiKey", "DigiKey Part Number", "Arrow", "Farnell", "Newark", "Stock Code"]

**Verification**: `PYTHONPATH=src python -c "from jbom.config.fabricators import load_fabricator; [load_fabricator(f) for f in ['jlc','pcbway','generic','seeed')]"` — should load without errors.

**Estimated effort**: 30 minutes

---

## Task 4.3: Fix InventoryReader

**Goal**: Remove DPN hack, align column mappings with new CSV schema.

**File**: `src/jbom/services/inventory_reader.py`

**Changes** in `_process_inventory_data()` (line ~288-329):
1. Change `lcsc=self._get_first_value(row, ["LCSC", "LCSC Part", "LCSC Part #", "DPN"])` → `lcsc=self._get_first_value(row, ["LCSC", "LCSC Part", "LCSC Part #"])`
2. Remove or empty the `distributor_part_number` mapping (DPN column no longer exists)
3. The `distributor` mapping can stay but will be empty (column removed) — or remove it
4. Ensure `raw_data=row` still captures ALL columns including LCSC, Mouser, etc.

**Verification**:
```bash
PYTHONPATH=src python -c "
from jbom.services.inventory_reader import InventoryReader
from pathlib import Path
r = InventoryReader(Path('../../examples/SPCoast-INVENTORY.csv'))
items, fields = r.load()
for item in items[:3]:
    print(item.ipn, 'LCSC:', item.lcsc, 'raw LCSC:', item.raw_data.get('LCSC',''), 'raw Mouser:', item.raw_data.get('Mouser',''))
"
```

**Estimated effort**: 30 minutes

---

## Task 4.4: Fix Enrichment Pipeline

**Goal**: Resolve `fabricator_part_number` from matched item's `raw_data` via fabricator config, fix missing attributes.

**File**: `src/jbom/services/inventory_matcher.py`

**Changes to `enhance_bom_with_inventory()`**:
- Save the loaded `config` from `_filter_by_fabricator()` and pass it to `_enrich_entry()`
- Refactor `_filter_by_fabricator()` to return both eligible items AND the config

**Changes to `_enrich_entry()` — new signature**:
```python
def _enrich_entry(entry: BOMEntry, item: InventoryItem, config: Optional[FabricatorConfig] = None) -> BOMEntry:
```

**Enrichment logic**:
1. Resolve `fabricator_part_number`: use config's field_synonyms to walk `fab_pn` → `supplier_pn` → `mpn` on `item.raw_data`. First non-empty value wins.
   ```python
   def _resolve_fabricator_pn(item: InventoryItem, config: FabricatorConfig) -> str:
       normalized = {}  # build normalized raw_data using config.resolve_field_synonym()
       for canonical in ["fab_pn", "supplier_pn", "mpn"]:
           val = normalized.get(canonical, "")
           if val.strip():
               return val
       return item.mfgpn or ""  # final fallback
   ```
2. Fix `"lcsc_part"` → `"lcsc"` key name
3. Add `"package": item.package`
4. Add `"smd": item.smd`
5. Set `"fabricator_part_number"` from resolved value

**Verification**: Run JLC and PCBWay BOM for Core-wt32-eth0 — LCSC codes should appear for JLC, MPN for PCBWay.

**Estimated effort**: 1-2 hours

---

## Task 4.5: Simplify FabricatorInventorySelector

**Goal**: Remove the `_passes_fabricator_filter()` affinity check — no longer needed.

**File**: `src/jbom/services/fabricator_inventory_selector.py`

**Changes**:
- In `select_eligible()`, remove the `if not self._passes_fabricator_filter(item): continue` check
- Delete `_passes_fabricator_filter()` method
- `_passes_project_filter()`, `_normalized_raw_data()`, and `_assign_tier()` stay unchanged

**Rationale**: With single-row-per-IPN and no `Fabricator` column, the affinity filter always returns True (every item has `fabricator=""`). Removing it simplifies the code.

**Verification**: All existing tests pass. BOM output unchanged.

**Estimated effort**: 15 minutes

---

## Task 4.6: Delete Stale Skipped Test Files

**Goal**: Remove test files that reference non-existent modules.

**Files to delete**:
- `tests/integration/test_workflows.py` — references non-existent `jbom.workflows.bom_workflows`
- `tests/integration/test_schematic_reader_integration.py` — wrong import paths

**Verification**: 0 unconditional skips in pytest. BDD unchanged.

**Estimated effort**: 15 minutes

---

## Task 4.7: Update Test Fixtures

**Goal**: Align all test fixtures with new inventory CSV schema.

**Files to check/update**:
- `tests/services/matchers/test_inventory_matcher.py` — `_make_inventory_item()` helper needs `raw_data` with LCSC/Mouser columns instead of Distributor/DPN
- `tests/integration/test_service_composition.py` — similar fixture updates
- `tests/integration/test_target_inventory_contract.py` — uses real SPCoast-INVENTORY.csv (already migrated)
- BDD step definitions in `features/steps/` — check for Distributor/DPN references in fixtures

**New tests to add**:
- JLC enrichment resolves LCSC code as `fabricator_part_number`
- PCBWay enrichment resolves MPN as `fabricator_part_number`
- Same IPN row serves both JLC and PCBWay with different `fabricator_part_number` values
- Generic enrichment uses best available PN

**Estimated effort**: 1-2 hours

---

## Task 4.8: Retire ComponentInventoryMatcher

**Goal**: Delete old naive matcher after `inventory` CLI is migrated.

**Precondition**: `inventory.py` CLI no longer imports `ComponentInventoryMatcher`.

**Steps**:
1. Migrate `inventory` CLI to sophisticated pipeline (same as old Task 4.2)
2. `grep -r "ComponentInventoryMatcher" src/ tests/ features/` — should return nothing
3. Delete `src/jbom/services/component_inventory_matcher.py`
4. Run full test suite

**Estimated effort**: 1-2 hours (including inventory CLI migration)

---

## Task 4.9: End-to-End Validation with Real Projects

**Goal**: Verify pipeline produces correct output for real KiCad projects.

**Test projects** (read-only — no artifacts in project directories):
- `/Users/jplocher/Dropbox/KiCad/projects/Core-wt32-eth0/` — compare with `production/bom.csv`
- `/Users/jplocher/Dropbox/KiCad/projects/AltmillSwitchController/` — compare with `production/jlc-bom.csv`
- `/Users/jplocher/Dropbox/KiCad/projects/LEDStripDriver/`

**Validation**:
```bash
# JLC BOM — LCSC codes should appear in fabricator_part_number
PYTHONPATH=src python -m jbom bom Core-wt32-eth0 -o console --inventory SPCoast-INVENTORY.csv --fabricator jlc -v
# PCBWay BOM — MPN should appear, no LCSC codes
PYTHONPATH=src python -m jbom bom Core-wt32-eth0 -o console --inventory SPCoast-INVENTORY.csv --fabricator pcbway -v
# No-inventory BOM — compare base content with KiCad production/bom.csv
PYTHONPATH=src python -m jbom bom Core-wt32-eth0 -o console -v
```

**Success criteria**: LCSC codes match KiCad's `production/bom.csv` LCSC column. MPN visible for PCBWay. Known issues documented in GitHub issues.

**Estimated effort**: 1-2 hours

---

## Task 4.10: Match Diagnostics CLI

**Goal**: Expose matcher debug info via `--match-debug` flag on `bom` command.

**Independent of tasks 4.1-4.9** — can be done in parallel.

**Changes**:
1. Add `--match-debug` flag to `bom` CLI in `src/jbom/cli/bom.py`
2. Thread through `InventoryMatcher.enhance_bom_with_inventory(debug=True)`
3. Pass to `MatchingOptions(include_debug_info=True)`
4. Print scoring breakdown to stderr

**Output format** (stderr only):
```
[MATCH] R1,R2,R3 (10K 0603): → RES_10K_0603 (score=120, tier=0)
  Type: +50, Value: +40, Package: +30
[ORPHAN] U1 (ESP32-WROOM): no match found
```

**Estimated effort**: 1-2 hours

---

## Task 4S: Supplier Profiles (PARALLEL TRACK)

**Goal**: Introduce `*.supplier.yaml` profiles that capture supplier-specific knowledge — URL templates, PN validation, catalog search info. Replaces dropped `DPNLink` column with derived URLs.

**Independent of tasks 4.1-4.10** — no code dependencies. Can run in parallel.

**See plan**: `docs/workflow/planning/PHASE_4S_PLAN.md` for full design and implementation details.

**New files**:
- `src/jbom/config/suppliers.py` — loader module (mirrors `fabricators.py`)
- `src/jbom/config/suppliers/lcsc.supplier.yaml`
- `src/jbom/config/suppliers/mouser.supplier.yaml`
- `src/jbom/config/suppliers/digikey.supplier.yaml`
- `src/jbom/services/supplier_url_resolver.py` — URL generation from part numbers
- Unit tests for loader, URL resolver, PN validation

**Key design point**: Fabricator profiles and supplier profiles are orthogonal — they connect through shared inventory column names, not code coupling.

**Estimated effort**: 2-3 hours

---

## Summary

**Total estimated effort**: 8-13 hours (4.1-4.10: 6-10h + 4S: 2-3h)
**Execution**:
- Tasks 4.1-4.5: core schema/pipeline work (design session oversight recommended)
- Tasks 4.6-4.10: mechanical, sub-agent delegatable
- Task 4S: independent parallel track, sub-agent delegatable

**Design principles**:
- Tolerant synonym resolution — fab profiles ship with comprehensive defaults, missing columns resolve to empty
- Supplier profiles separate from fabricator profiles — orthogonal concerns

**After Phase 4**: The inventory model is clean, enrichment works per-fabricator, supplier URLs are derivable, and real projects validate the pipeline.
