# What to Do Next

## Status (as of 2026-02-25)
Phase 1 is complete and merged to `main` (PR #57; Issue #48 closed).

Phase 1 delivered the sophisticated inventory matcher extraction into jbom-new's clean architecture, including:
- 122 passing tests (112 unit + 10 integration)
- extracted utility modules in `src/jbom/common/`
- ADR 0001 documenting the Phase 2 fabricator-selection design

## Phase 2 Kickoff: Fabricator-aware inventory selection
Phase 2 implements the selection layer described in ADR 0001. Two independent priority concepts must be preserved:
- `item.priority`: user's stock-management ordering (Phase 1 behavior, fabricator-agnostic)
- `preference_tier`: fabricator's catalog/crossref preference (Phase 2 behavior, fabricator-specific)

### Use Case: Generate BOM for Specific Fabricator
When generating a BOM for assembly, different fabricators have different supply chain constraints:

**Inventory items declare fabricator affinity** via `item.fabricator` field:
- `item.fabricator == "JLC"` → consigned/dedicated to JLCPCB
- `item.fabricator == "PCBWay"` → consigned/dedicated to PCBWay
- `item.fabricator == ""` → generic, available to any fabricator

**Fabricator configs declare part number preferences** (Issue #59 - schema refactoring):
- `field_synonyms`: Map field name variants to canonical names (e.g., "LCSC", "LCSC Part", "JLC" → `lcsc`)
- `part_number_source_tiers`: Explicit tier definitions using canonical names
  - Tier 0: Native catalog (preferred)
  - Tier 1+: Crossref/fallback sources

**Selection mechanics** (three-stage: filter → normalize → tier):
1. **Fabricator affinity filter**:
   - Keep: `item.fabricator == target_fabricator` OR `item.fabricator == ""`
   - Prune: `item.fabricator == other_fabricator`
   - Example: Building for JLC → keep JLC-specific + generic, prune PCBWay-specific

2. **Field synonym normalization**:
   - Resolve field name variants to canonical names using `field_synonyms`
   - Example: item with "LCSC Part" field → normalized to `lcsc` canonical name
   - Enables reusable synonym mappings across all fields (not just part numbers)

3. **Preference tiering** (among normalized fields):
   - Look up canonical field names in `part_number_source_tiers`
   - Tier = explicit tier number for first matching canonical field
   - Example JLC: item with `lcsc` field → Tier 0, item with only `mpn` → Tier 1
   - No matching tier → item has no usable part number (warning)

3. **Final ordering**: `(preference_tier, item.priority, -score)`
   - Fabricator catalog preference first
   - User stock management second
   - Match quality third

**Examples** (using new schema from Issue #59):
- **JLCPCB**
  ```yaml
  field_synonyms:
    lcsc: ["LCSC", "LCSC Part", "JLC"]
    mpn: ["MPN", "MFGPN"]
  part_number_source_tiers:
    0: [lcsc]   # Catalog
    1: [mpn]    # Crossref
  ```
  - Items with `fabricator=="JLC"` + `lcsc` field → Tier 0 (consigned catalog - best)
  - Items with `fabricator==""` + `lcsc` field → Tier 0 (catalog available to JLC)
  - Items with `fabricator==""` + only `mpn` → Tier 1 (crossref via manufacturer)
  - Items with `fabricator=="PCBWay"` → pruned (competitor's consignment)

- **PCBWay**
  ```yaml
  field_synonyms:
    pcbway: ["PCBWay", "PCBWay Part"]
    mouser: ["Mouser", "Mouser Part Number"]
    mpn: ["MPN", "MFGPN"]
  part_number_source_tiers:
    0: [pcbway]        # Native catalog
    1: [mouser, digikey]  # Preferred distributors
    2: [mpn]           # Crossref
  ```
  - Items with `fabricator=="PCBWay"` + `pcbway` → Tier 0 (consigned catalog)
  - Items with `fabricator==""` + `mouser` → Tier 1 (distributor)
  - Items with `fabricator==""` + only `mpn` → Tier 2 (crossref/self-source)
  - Items with `fabricator=="JLC"` → pruned (competitor's warehouse)

- **Generic**
  ```yaml
  field_synonyms:
    mpn: ["MPN", "MFGPN", "Part Number", "P/N"]
  part_number_source_tiers:
    0: [mpn]  # All manufacturer data equal
  ```
  - All items with `fabricator==""` eligible (no fab-specific consignment)
  - Items with fab-specific values pruned (consigned elsewhere)
  - User controls all sourcing via `item.priority` (no fabricator preference)

This design allows the same inventory to serve multiple fabricators with different:
- **Supply chain models** (catalog vs crossref vs self-source)
- **Consignment relationships** (fab-specific vs generic stock)
- **Part number schemas** (LCSC vs distributor catalogs vs manufacturer data)

Primary reference for Phase 2 planning:
- `docs/workflow/planning/PHASE_2_REMAINING_WORK.md`

Expected Phase 2 ordering invariant:
- `(preference_tier, item.priority, -score)`

## Phase 1 design note (keep)
Our tests and discussion clarified an important design nuance:
- The exact numeric scoring is not inherently valuable; it is a mechanism to achieve good ranking and to eliminate unsuitable matches.
- Longer term, we may want to evolve matching heuristics toward expressing intent more directly (e.g., "correct type/value/package always beats anything else", and priority is applied as a first-class ordering constraint), instead of relying on opaque point totals.
- If we do replace the scoring mechanism in the future, preserve the behavioral contracts: filtering correctness + ordering invariants.

## SEE ALSO
- `docs/architecture/adr/0001-fabricator-inventory-selection-vs-matcher.md`
- `docs/architecture/anti-patterns.md`
- `docs/workflow/planning/PHASE_2_REMAINING_WORK.md`
