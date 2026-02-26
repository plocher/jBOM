# jBOM-new: Complete Roadmap
- [jBOM-new: Complete Roadmap](#jbom-new-complete-roadmap)
  - [Overview](#overview)
  - [Phase 2: Fabricator-Aware Inventory Selection (ADR 0001)](#phase-2-fabricator-aware-inventory-selection-adr-0001)
    - [Goal](#goal)
    - [Testing Strategy Note](#testing-strategy-note)
    - [Prerequisite: Fabricator Config Schema Refactoring (Issue #59)](#prerequisite-fabricator-config-schema-refactoring-issue-59)
    - [Tasks](#tasks)
      - [2.1: FabricatorInventorySelector Service](#21-fabricatorinventoryselector-service)
      - [2.2: Update Matcher to Accept EligibleInventoryItem](#22-update-matcher-to-accept-eligibleinventoryitem)
      - [2.3: Integration Tests with Real Fabricator Configs](#23-integration-tests-with-real-fabricator-configs)
    - [Deliverables](#deliverables)
  - [Phase 3: Wire Up to Existing jbom-new Services](#phase-3-wire-up-to-existing-jbom-new-services)
    - [Goal](#goal-1)
    - [Tasks](#tasks-1)
      - [3.1: Integrate with InventoryReader](#31-integrate-with-inventoryreader)
      - [3.2: Replace Simple Matcher in inventory\_matcher.py](#32-replace-simple-matcher-in-inventory_matcherpy)
      - [3.3: Update BOM Generator Workflow](#33-update-bom-generator-workflow)
      - [3.4: Integration Tests - End-to-End BOM Generation](#34-integration-tests---end-to-end-bom-generation)
    - [Deliverables](#deliverables-1)
  - [Phase 4: CLI Integration](#phase-4-cli-integration)
    - [Goal](#goal-2)
    - [Tasks](#tasks-2)
      - [4.1: Add --fabricator Flag to BOM Command](#41-add---fabricator-flag-to-bom-command)
      - [4.2: Match Diagnostics Command](#42-match-diagnostics-command)
      - [4.3: Inventory Validation Command](#43-inventory-validation-command)
    - [Deliverables](#deliverables-2)
  - [Phase 5: Advanced Property Matching](#phase-5-advanced-property-matching)
    - [Goal](#goal-3)
    - [Tasks](#tasks-3)
      - [5.1: LED-Specific Properties](#51-led-specific-properties)
      - [5.2: Oscillator-Specific Properties](#52-oscillator-specific-properties)
      - [5.3: IC-Specific Properties](#53-ic-specific-properties)
    - [Deliverables](#deliverables-3)
  - [Phase 6: Multi-Inventory Federation](#phase-6-multi-inventory-federation)
    - [Goal](#goal-4)
    - [Tasks](#tasks-4)
      - [6.1: InventoryRepository Implementation](#61-inventoryrepository-implementation)
      - [6.2: Source Tracking in Match Results](#62-source-tracking-in-match-results)
      - [6.3: Federated Inventory Tests](#63-federated-inventory-tests)
    - [Deliverables](#deliverables-4)
  - [Phase 7: Performance \& Scale](#phase-7-performance--scale)
    - [Goal](#goal-5)
    - [Tasks](#tasks-5)
      - [7.1: Benchmark Current Performance](#71-benchmark-current-performance)
      - [7.2: Optimize Primary Filtering](#72-optimize-primary-filtering)
      - [7.3: Parallel Matching](#73-parallel-matching)
    - [Deliverables](#deliverables-5)
  - [Phase 8: Production Readiness](#phase-8-production-readiness)
    - [Goal](#goal-6)
    - [Tasks](#tasks-6)
      - [8.1: Error Handling \& User Messages](#81-error-handling--user-messages)
      - [8.2: Logging \& Diagnostics](#82-logging--diagnostics)
      - [8.3: Migration Guide from Legacy jBOM](#83-migration-guide-from-legacy-jbom)
      - [8.4: User Documentation](#84-user-documentation)
    - [Deliverables](#deliverables-6)
  - [Phase 9: Deprecate Legacy jBOM](#phase-9-deprecate-legacy-jbom)
    - [Goal](#goal-7)
    - [Tasks](#tasks-7)
      - [9.1: Feature Parity Verification](#91-feature-parity-verification)
      - [9.2: Side-by-Side Comparison Tests](#92-side-by-side-comparison-tests)
      - [9.3: Deprecation Announcement](#93-deprecation-announcement)
      - [9.4: Archive Legacy Code](#94-archive-legacy-code)
    - [Deliverables](#deliverables-7)
  - [Estimated Total Effort](#estimated-total-effort)
  - [Priority Ranking](#priority-ranking)
  - [Success Criteria](#success-criteria)
  - [Notes](#notes)

**Status**: Phase 1 ✅ Complete | Phase 2 ✅ Complete | Phase 3 ⏳ Ready
**Date**: 2026-02-25
**Last Updated**: After PR #58 merge

## Overview
This is the master roadmap for completing jbom-new. Phase 1 delivered a sophisticated matching algorithm in clean architecture. Phases 2-9 add fabricator selection, integration, and production readiness.

**Progress:**
- ✅ **Phase 1 Complete**: Sophisticated matcher (PR #57, Issue #48, 122 tests passing)
- ✅ **Phase 2 Complete**: Fabricator selection (Issues #59, #60, 229 tests passing)
- ⏳ **Phase 3 Ready**: Service integration
- ⏳ **Phases 4-9**: Planned

## Phase 2: Fabricator-Aware Inventory Selection (ADR 0001)

**Status**: ✅ Complete
**Issues**: #59 (schema), #60 (consignment) - implemented
**Delivered**: FabricatorInventorySelector + tier_rules schema + matcher integration

### Goal
Implement the fabricator selection layer that works with the Phase 1 matcher.

### Testing Strategy Note
**Key Insight**: `generic` fabricator is the **explicit default**, not absence-of-fabricator.

CLI behavior:
```bash
jbom bom project.kicad_sch  # Implicitly: --fabricator generic
```

**Benefits for testing:**
1. **Reproducible default**: All tests have well-defined baseline behavior
2. **Isolation**: Feature tests assume generic default, override only when testing fabricator-specific logic
3. **Composition**: Features stack cleanly (matching → catalog preference → consignment → project filtering)
4. **No hardcoded assumptions**: "No fabricator specified" behavior is defined in `generic.fab.yaml`, not code

**BDD Test Pattern:**
```gherkin
# Base tests use implicit generic default
Scenario: Component matches inventory
  Given inventory with standard items
  When I generate a BOM  # Uses generic fabricator
  Then component matches by MPN

# Fabricator-specific tests override explicitly
Scenario: JLC prefers catalog over crossref
  Given fabricator "jlc"
  When I generate a BOM with fabricator "jlc"
  Then catalog item (tier 0) beats crossref (tier 1)
```

This makes `generic.fab.yaml` the **reference implementation** for all baseline testing.

### Prerequisite: Fabricator Config Schema Refactoring (Issue #59)
**Estimated**: 3-4 hours

**Problem**: Current `priority_fields` conflates field name synonyms with tier preferences.

**Solution**: Separate into two schema elements with three-level field design and policy-based tiering:
```yaml
# Before (implicit, conflated)
part_number:
  priority_fields: ["LCSC", "LCSC Part", "JLC", "MPN"]

# After (explicit, separated)
field_synonyms:
  fab_pn:  # Canonical name (internal)
    synonyms: ["LCSC", "LCSC Part", "LCSC Part #", "JLC"]
    display_name: "Fabricator Catalog Part Number"  # BOM output header
  supplier_pn:
    synonyms: ["DPN", "Distributor Part Number", "Mouser Part Number", "DigiKey Part Number"]
    display_name: "Supplier Part Number"
  mpn:
    synonyms: ["MPN", "MFGPN"]
    display_name: "MPN"

tier_rules:
  0:
    conditions:
      - field: "Consigned"
        operator: "truthy"
  1:
    conditions:
      - field: "Preferred"
        operator: "truthy"
      - field: "fab_pn"
        operator: "exists"
  2:
    conditions:
      - field: "fab_pn"
        operator: "exists"
  3:
    conditions:
      - field: "supplier_pn"
        operator: "exists"
  4:
    conditions:
      - field: "mpn"
        operator: "exists"
```

**Tasks**:
1. Update fabricator YAML schema
2. Migrate existing configs (jlc.fab.yaml, pcbway.fab.yaml, generic.fab.yaml, seeed.fab.yaml)
3. Update `FabricatorConfig` dataclass to parse new schema
4. Add tests for synonym resolution
5. Update documentation

**Benefits**:
- Eliminates semantic collision with `item.priority`
- Makes tier assignments explicit (not implicit by position)
- Enables reusable synonym mappings across all fields
- Cleaner foundation for Phase 2.1 implementation

### Tasks

#### 2.1: FabricatorInventorySelector Service
**Estimated**: 4-6 hours

Create `jbom/services/fabricator_inventory_selector.py`:
```python
@dataclass
class EligibleInventoryItem:
    """Inventory item with fabricator metadata."""
    item: InventoryItem
    preference_tier: int

class FabricatorInventorySelector:
    """Filters and annotates inventory for a fabricator."""

    def select_eligible(
        inventory: List[InventoryItem],
        fabricator_config: FabricatorConfig
    ) -> List[EligibleInventoryItem]:
        """Filter by affinity/project and assign tier via tier_rules."""
```

**Key Behaviors:**
- Normalize evolving inventory column names using `fabricator_config.field_synonyms`.
- Assign a preference tier by evaluating `fabricator_config.tier_rules` (policy-based, not positional list ordering).
- Output ordering is later applied as: `(preference_tier, item.priority, -score)`.

**Tests:**
- JLC config: Tier rules assign lower tiers to better identifiers/flags (consigned/preferred/catalog).
- Generic config: Default tier rules behave as configured.
- Multi-source inventory: Synonym normalization ensures evolving catalog column names resolve to canonical fields.

#### 2.2: Update Matcher to Accept EligibleInventoryItem
**Estimated**: 2-3 hours

Modify `SophisticatedInventoryMatcher`:
```python
def find_matches(
    component: Component,
    inventory: List[Union[InventoryItem, EligibleInventoryItem]]
) -> List[MatchResult]:
    # Sort by: (preference_tier, item.priority, -score)
```

**Backward compatible**: Accepts plain `InventoryItem` (tier=0 assumed)

**Tests:**
- Same priority, different tiers: tier 0 before tier 1
- Same tier, different priorities: priority 1 before priority 2
- Same tier + priority: higher score first

#### 2.3: Integration Tests with Real Fabricator Configs
**Estimated**: 2-3 hours

Test scenarios:
- JLC config with LCSC vs MPN items
- Generic config (no filtering)
- Multi-fabricator comparison (JLC vs PCBWay)

### Deliverables
- `fabricator_inventory_selector.py` with tests
- Updated matcher with 3-tier sorting
- Integration tests proving fabricator preference works
- Update ADR 0001 status to "Implemented"

---

## Phase 3: Wire Up to Existing jbom-new Services

### Goal
Replace POC-level matching with sophisticated matcher throughout jbom-new.

### Tasks

#### 3.1: Integrate with InventoryReader
**Estimated**: 2-3 hours

Current: `inventory_reader.py` loads CSV/XLSX/Numbers
Update: Returns `List[InventoryItem]` ready for selector/matcher

#### 3.2: Replace Simple Matcher in inventory_matcher.py
**Estimated**: 3-4 hours

Current: `inventory_matcher.py` has naive value-only matching
Update: Use `SophisticatedInventoryMatcher` + `FabricatorInventorySelector`

**Behavior change**: Matches improve dramatically (package, tolerance, scoring)

#### 3.3: Update BOM Generator Workflow
**Estimated**: 2-3 hours

Wire matcher into `bom_generator.py`:
1. Load components from schematic
2. Load inventory from file
3. Select eligible items (fabricator filter)
4. Match components to inventory
5. Generate BOM with matched data

#### 3.4: Integration Tests - End-to-End BOM Generation
**Estimated**: 3-4 hours

Real KiCad projects + SPCoast inventory:
- LEDStripDriver project → BOM with matched parts
- Core-wt32-eth0 project → BOM for JLC assembly
- Verify all components match or report orphans

### Deliverables
- Sophisticated matcher integrated throughout
- End-to-end BOM generation working
- Replacement for POC test_workflows.py

---

## Phase 4: CLI Integration

### Goal
Expose sophisticated matching via CLI commands.

### Tasks

#### 4.1: Add --fabricator Flag to BOM Command
**Estimated**: 2-3 hours

```bash
jbom bom project.kicad_sch --inventory parts.csv --fabricator jlc
jbom bom project.kicad_sch --inventory parts.csv --fabricator generic
```

Loads fabricator config, applies to selection/matching.

#### 4.2: Match Diagnostics Command
**Estimated**: 2-3 hours

```bash
jbom match component.kicad_sch --inventory parts.csv --debug
```

Shows match scoring breakdown for troubleshooting:
- Which items passed primary filters
- Score breakdown (type, value, package, properties)
- Priority + tier ordering

#### 4.3: Inventory Validation Command
**Estimated**: 2-3 hours

```bash
jbom validate-inventory parts.csv --fabricator jlc
```

Reports:
- Items eligible for fabricator
- Items missing required fields
- Orphaned components (in schematics but not inventory)

### Deliverables
- CLI commands working with sophisticated matcher
- Help text and examples
- User documentation

---

## Phase 5: Advanced Property Matching

### Goal
Port remaining property matching from legacy (LED, oscillator, etc.)

### Tasks

#### 5.1: LED-Specific Properties
**Estimated**: 2-3 hours

Add to matcher scoring:
- Wavelength matching (+10 points)
- Luminous intensity (mcd) (+10 points)
- Viewing angle (+10 points)

#### 5.2: Oscillator-Specific Properties
**Estimated**: 2-3 hours

Add to matcher scoring:
- Frequency matching (+15 points)
- Stability (ppm) (+10 points)
- Load capacitance (+5 points)

#### 5.3: IC-Specific Properties
**Estimated**: 3-4 hours

Add to matcher scoring:
- Family matching (ESP32, STM32, etc.) (+20 points)
- Pin count matching (+10 points)

### Deliverables
- Extended property matching for special component types
- Tests with real LED/oscillator/IC inventory items
- Documentation of scoring weights

---

## Phase 6: Multi-Inventory Federation

### Goal
Support multiple inventory sources with conflict resolution.

### Tasks

#### 6.1: InventoryRepository Implementation
**Estimated**: 4-6 hours

```python
class InventoryRepository:
    """Manages multiple inventory sources."""
    sources: List[InventorySource]

    def get_consolidated_items() -> List[InventoryItem]:
        """Merge sources with IPN conflict resolution."""
```

**IPN Conflict Resolution:**
- Same IPN from multiple sources = keep all, adjust priorities
- User-defined priority offsets per source

#### 6.2: Source Tracking in Match Results
**Estimated**: 2-3 hours

Add `source: str` to match results for traceability:
- "Which inventory file did this match come from?"
- Support for audit/compliance

#### 6.3: Federated Inventory Tests
**Estimated**: 3-4 hours

Test scenarios:
- Personal + company + JLCPCB inventories
- Same IPN with different priorities from different sources
- Conflicting data (prefer user's inventory over JLCPCB)

### Deliverables
- Multi-inventory support
- Conflict resolution logic
- Documentation of federation patterns

---

## Phase 7: Performance & Scale

### Goal
Ensure matcher performs well with large inventories.

### Tasks

#### 7.1: Benchmark Current Performance
**Estimated**: 2 hours

Measure with:
- 100 components × 1,000 inventory items
- 1,000 components × 10,000 inventory items

#### 7.2: Optimize Primary Filtering
**Estimated**: 3-4 hours

Potential optimizations:
- Index inventory by category (avoid scanning resistors for LED)
- Index by package (avoid scanning 0805 for 0603 components)
- Cache parsed values (don't re-parse "10k" every match)

#### 7.3: Parallel Matching
**Estimated**: 4-6 hours

Match components in parallel (independent operations):
- Use multiprocessing or asyncio
- Batch inventory loading

### Deliverables
- Performance benchmarks
- Optimizations for large inventories
- Documentation of performance characteristics

---

## Phase 8: Production Readiness

### Goal
Make jbom-new production-ready for real projects.

### Tasks

#### 8.1: Error Handling & User Messages
**Estimated**: 3-4 hours

Improve error messages:
- "No matches found for C12 (100nF, 0603) - check inventory or relax filters"
- "Ambiguous: R5 matched 3 items with score 120 - set priority to disambiguate"

#### 8.2: Logging & Diagnostics
**Estimated**: 2-3 hours

Add structured logging:
- Match statistics (candidates evaluated, passed filters, matched)
- Performance metrics (match time per component)

#### 8.3: Migration Guide from Legacy jBOM
**Estimated**: 4-6 hours

Document:
- Behavioral differences (if any)
- Inventory file format compatibility
- CLI command mapping (old → new)
- Migration checklist

#### 8.4: User Documentation
**Estimated**: 4-6 hours

Create:
- Getting started guide
- Inventory file format specification
- Fabricator configuration guide
- Troubleshooting matching issues

### Deliverables
- Production-quality error handling
- Comprehensive documentation
- Migration guide

---

## Phase 9: Deprecate Legacy jBOM

### Goal
Sunset the old jBOM codebase once jbom-new is feature-complete.

### Tasks

#### 9.1: Feature Parity Verification
**Estimated**: 6-8 hours

Compare legacy vs new:
- All legacy features working in new
- Test coverage equivalent or better
- Performance acceptable

#### 9.2: Side-by-Side Comparison Tests
**Estimated**: 4-6 hours

Run same projects through both:
- Compare BOM outputs
- Document any differences
- Verify improvements (better matches, clearer errors)

#### 9.3: Deprecation Announcement
**Estimated**: 2 hours

Communicate:
- Timeline for legacy sunset
- Migration support available
- New features in jbom-new

#### 9.4: Archive Legacy Code
**Estimated**: 2 hours

Move to `legacy/` directory:
- Preserve for reference
- Update README
- Remove from active development

### Deliverables
- Feature parity achieved
- Comparison report
- Legacy code archived
- jbom-new is production default

---

## Estimated Total Effort

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 2: Fabricator Selection | 3 | 8-12 hours |
| Phase 3: Service Integration | 4 | 10-14 hours |
| Phase 4: CLI Integration | 3 | 6-9 hours |
| Phase 5: Advanced Properties | 3 | 7-10 hours |
| Phase 6: Multi-Inventory | 3 | 9-13 hours |
| Phase 7: Performance | 3 | 9-14 hours |
| Phase 8: Production Ready | 4 | 13-19 hours |
| Phase 9: Deprecate Legacy | 4 | 14-18 hours |
| **TOTAL** | **27 tasks** | **76-109 hours** |

## Priority Ranking

**High Priority (Minimum Viable):**
1. Phase 2: Fabricator selection (ADR 0001 completion)
2. Phase 3: Service integration (wire up matcher)
3. Phase 4: CLI integration (user-facing functionality)

**Medium Priority (Production Ready):**
4. Phase 8: Production readiness (error handling, docs)
5. Phase 5: Advanced properties (better matching for special components)

**Low Priority (Nice to Have):**
6. Phase 6: Multi-inventory federation
7. Phase 7: Performance optimization
8. Phase 9: Legacy deprecation

## Success Criteria

**jbom-new is "complete" when:**
- ✅ Phase 1 complete (sophisticated matcher extracted)
- ✅ Phase 2 complete (fabricator selection working)
- ✅ Phase 3 complete (integrated with existing services)
- ✅ Phase 4 complete (CLI commands working)
- ✅ Phase 8 complete (production-ready with docs)
- ✅ Real projects generate correct BOMs for JLC/PCBWay/etc.
- ✅ Migration guide available for legacy users
- ✅ Test coverage ≥ 80%

## Notes

**Parallel Work Possible:**
- Phase 5 (advanced properties) can happen anytime after Phase 1
- Phase 6 (multi-inventory) independent of Phases 2-4
- Phase 7 (performance) can happen anytime

**Deferred to Future:**
- Machine learning for matching
- Fuzzy matching (typo tolerance)
- Automatic inventory updates from supplier APIs
- Web UI for match debugging

**Related Issues:**
- #48: Sophisticated matching (Phase 1 - DONE)
- #56: Fabricator field research (Phase 2 input)

---
**Last Updated**: 2026-02-25
**Status**: Phase 1 complete, Phase 2 ready to start
