# Phase 3: Service Integration - Task Breakdown

## Overview
Wire Phase 2 services (FabricatorInventorySelector + SophisticatedInventoryMatcher) into the actual BOM generation pipeline, replacing naive value-only matching with the sophisticated matching pipeline.

**Status**: ✅ Complete (PR #63, Issue #62)
**Date**: 2026-02-26
**Context**: Phase 2 complete (PR #61), services implemented but not wired into CLI

## Prerequisites Completed
- ✅ Phase 1: Sophisticated matcher (PR #57, Issue #48)
- ✅ Phase 2: FabricatorInventorySelector + tier-aware ordering (PR #61)
- ✅ Architecture: `docs/architecture/workflow-architecture.md` documenting correct pipeline

## Correct Pipeline (established in Phase 3 planning)
```
1. Extract.Components  →  Load components from KiCad schematic
2. Aggregate           →  Group components by electro-mechanical equivalence
3. Extract.Items       →  Load inventory from file(s)
4. Filter.Items        →  Filter/rank inventory by fabricator profile
5. Match.Components    →  Match each aggregated group to filtered inventory
6. Resolve.Conflicts   →  Handle orphans and ambiguous matches
7. Create.BOM          →  Format and output the BOM
```

Key insight: **aggregation is independent of inventory**. It groups components with identical electro-mechanical specs purely from schematic data. Matching operates on each aggregated group against the fabricator-filtered inventory.

## Task Sequence

### Task 3.1: Audit InventoryReader `raw_data` Population
**Status**: ✅ Complete (verification only, no code changes needed)

**Goal**: Verify all inventory loaders populate `InventoryItem.raw_data` with complete original row dicts, since `FabricatorInventorySelector._normalized_raw_data()` depends on it.

**What Happened**:
- Verified all 4 loaders pass complete row dicts:
  - CSV loader: `_process_inventory_data()` passes `raw_data=row` (line 327)
  - Excel loader: feeds into same `_process_inventory_data()`
  - Numbers loader: feeds into same `_process_inventory_data()`
  - JLC loader: `_process_rows()` passes `raw_data=row` (line 131)
- Unmapped columns (e.g., "Consigned", "Preferred", "LCSC Part #") survive into `raw_data`

**Success criteria**: ✅ All loaders confirmed

---

### Task 3.2: Replace Naive Matcher with Sophisticated Pipeline
**Status**: ✅ Complete

**Goal**: Refactor `InventoryMatcher.enhance_bom_with_inventory()` to use the Phase 2 services.

**Files modified**: `src/jbom/services/inventory_matcher.py`

**Implementation**:
- New method signature:
  ```python
  def enhance_bom_with_inventory(
      self, bom_data: BOMData, inventory_file: Path,
      fabricator_id: str = "generic", project_name: Optional[str] = None
  ) -> BOMData:
  ```
- Pipeline:
  1. Load inventory via `InventoryReader` (existing)
  2. Filter via `FabricatorInventorySelector(config).select_eligible(inventory, project_name)`
  3. For each BOMEntry, construct representative `Component` via `_bom_entry_to_component()`
  4. Match via `SophisticatedInventoryMatcher.find_matches(component, eligible_items)`
  5. Take best match and enrich entry attributes
  6. Track orphans (unmatched groups) in metadata
- Fallback: if fabricator config unavailable, uses unfiltered inventory (logged at debug level)
- Backward compatible: omitting fabricator defaults to `"generic"`

**Key design decision**: BOMEntry carries `lib_id`, `value`, `footprint`, and merged `attributes` from the representative component in its group. Since all components in an aggregated group have identical electro-mechanical specs by definition, any member is representative.

**Success criteria**: ✅ Pipeline wired, tests pass

---

### Task 3.3: Update CLI BOM Command Wiring
**Status**: ✅ Complete

**Goal**: Pass `fabricator_id` and `project_name` from CLI to the refactored matcher.

**Files modified**: `src/jbom/cli/bom.py` (line 247-253)

**Implementation**:
```python
matcher = InventoryMatcher()
bom_data = matcher.enhance_bom_with_inventory(
    bom_data,
    inventory_file,
    fabricator_id=fabricator,
    project_name=project_name,
)
```

Both `fabricator` and `project_name` were already resolved earlier in `handle_bom()`.

**Success criteria**: ✅ CLI passes parameters through

---

### Task 3.4: Update Tests for New Matcher Interface
**Status**: ✅ Complete

**Goal**: Update all tests for the new matcher interface and verify no regressions.

**Files modified/created**:
- `tests/services/matchers/test_inventory_matcher.py` (rewritten)
- `tests/integration/test_service_composition.py` (raw_data fix)

**What Changed**:
- Created `_make_inventory_item()` helper that auto-populates `raw_data` from kwargs — mirrors what `InventoryReader` produces from CSV rows
- Removed tests for deleted private methods (`_find_matching_inventory_item`, `_extract_package`)
- Added new tests:
  - `test_bom_entry_to_component` — verifies BOMEntry → Component conversion
  - `test_fabricator_filtering_fallback` — verifies graceful degradation with unknown fabricator
  - `test_metadata_includes_fabricator_info` — verifies new metadata fields
  - `test_fabricator_specific_matching` — verifies fabricator_id flows through
- Updated integration test `test_full_pipeline_three_services_composition` with realistic `raw_data` dicts

**Bug discovered and fixed**: `component_classification.py` had `"IC" in component_upper` which matched "GENERIC" (because "GENERIC" contains "IC"). Changed to exact match `component_upper == "IC"`. This was a pre-existing bug that only surfaced because the sophisticated matcher uses type classification where the naive matcher did not.

**Success criteria**: ✅ 231 pytest tests pass, 192 BDD scenarios pass

---

## Summary

**Total effort**: ~60 minutes (single session)

**Dependency chain**:
```
Task 3.1 (Audit raw_data) — independent, quick verification
    ↓
Task 3.2 (Refactor matcher) + Task 3.3 (CLI wiring) — core work
    ↓
Task 3.4 (Update tests) — verify and fix regressions
```

**Completion criteria**:
- ✅ `jbom bom --inventory X --fabricator Y` uses sophisticated matching pipeline
- ✅ All existing BDD scenarios pass (192/192)
- ✅ Generic fabricator default behavior unchanged
- ✅ New unit tests for pipeline components
- ✅ Orphan reporting in metadata
- ✅ Backward compatible (omitting fabricator defaults to "generic")

**Artifacts**:
- GitHub Issue: #62
- GitHub PR: #63
- Branch: `feature/issue-62-phase3-service-integration`
- Architecture doc: `docs/architecture/workflow-architecture.md`

**Bugs surfaced and fixed**:
- Component classification: `"IC" in "GENERIC"` false positive
- Test fixtures: mock `InventoryItem` objects need realistic `raw_data` for fabricator tier rules

**Next steps after Phase 3**:
- Phase 4: End-to-end BOM generation tests with real projects
- Phase 5+: Per roadmap (diagnostics, EIA formatting, multi-inventory, etc.)
