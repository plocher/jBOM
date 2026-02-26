# What to Do Next

## Status (as of 2026-02-26)
**Phase 1**: ✅ Complete (merged to main via PR #57)
**Phase 2**: ✅ Complete (merged to main via PR #61)
**Phase 3**: ✅ Complete (PR #63, Issue #62)

### Phase 1 Deliverables
- Sophisticated inventory matcher (Issue #48)
- 122 passing tests (112 unit + 10 integration)
- Extracted utility modules in `src/jbom/common/`
- ADR 0001 documenting fabricator-selection design

### Phase 2 Deliverables
- FabricatorInventorySelector service (4-stage filter)
- `field_synonyms` + `tier_rules` schema (Issues #59, #60)
- Matcher integration with `preference_tier` sorting
- 229 unit tests + 192 BDD scenarios passing

## Phase 3 Kickoff: Service Integration

**Goal**: Wire FabricatorInventorySelector into existing BOM generation workflow.

**Current state**: Phase 2 delivered the selector service, but it's not yet used by CLI commands or workflows.

**Next steps**: Integrate selector into:
1. InventoryReader workflow
2. BOM generation pipeline
3. CLI commands (`jbom bom`, `jbom inventory`)

See `docs/workflow/planning/JBOM_NEW_ROADMAP.md` Phase 3 for detailed tasks.

---

## Phase 2 Summary (for reference)
Phase 2 implemented fabricator-aware inventory selection with two independent priority concepts:
- `item.priority`: user's stock-management ordering (fabricator-agnostic)
- `preference_tier`: fabricator's catalog/crossref preference (fabricator-specific)

### Use Case: Generate BOM for Specific Fabricator
When generating a BOM for assembly, different fabricators have different supply chain constraints:

**Inventory items declare fabricator affinity** via `item.fabricator` field:
- `item.fabricator == "JLC"` → consigned/dedicated to JLCPCB
- `item.fabricator == "PCBWay"` → consigned/dedicated to PCBWay
- `item.fabricator == ""` → generic, available to any fabricator

**Fabricator configs declare identifier normalization + preference policy** (Issue #59 - schema refactoring):
- `field_synonyms`: Three-level field name design
  - **Canonical name**: Internal identifier used in code and tier definitions
  - **Synonyms**: Variant column names accepted from inventory CSVs
  - **Display name**: What appears in BOM output column headers
- `tier_rules`: Explicit, fabricator-defined tier assignment rules (policy-based)
  - Evaluated *after* field synonym normalization
  - Designed to remain stable even as catalog creators evolve column names

**Selection mechanics** (four-stage: affinity → normalize → tier → order):
1. **Fabricator affinity filter**:
   - Keep: `item.fabricator == target_fabricator` OR `item.fabricator == ""`
   - Prune: `item.fabricator == other_fabricator`

2. **Field synonym normalization**:
   - Resolve inventory column-name variants to canonical names using `field_synonyms`
   - Example: "LCSC Part #" → canonical `fab_pn`
   - Enables reusable synonym mappings across all fields (not just part numbers)

3. **Tier assignment** (policy-based):
   - Evaluate fabricator `tier_rules` in ascending tier order (0, 1, 2, ...)
   - Tier = first rule whose conditions all match
   - If no rule matches, the item is **not eligible** for that fabricator profile

4. **Final ordering**: `(preference_tier, item.priority, -score)`
   - Fabricator preference first
   - User stock management second
   - Match quality third

**Examples** (schema: `field_synonyms` + `tier_rules`):
- **JLCPCB**
  ```yaml
  field_synonyms:
    fab_pn:
      synonyms: ["LCSC", "LCSC Part", "LCSC Part #", "JLC", "JLC Part"]
      display_name: "LCSC Part Number"
    supplier_pn:
      synonyms: ["DPN", "Distributor Part Number", "Mouser Part Number", "DigiKey Part Number"]
      display_name: "Supplier Part Number"
    mpn:
      synonyms: ["MPN", "MFGPN", "Manufacturer Part Number"]
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

- **Generic**
  ```yaml
  field_synonyms:
    supplier_pn:
      synonyms: ["Part Number", "P/N", "Distributor Part Number", "DPN"]
      display_name: "Part Number"
    mpn:
      synonyms: ["MPN", "MFGPN"]
      display_name: "MPN"
  tier_rules:
    0:
      conditions:
        - field: "supplier_pn"
          operator: "exists"
    1:
      conditions:
        - field: "mpn"
          operator: "exists"
  ```

This design allows the same inventory to serve multiple fabricators with different:
- **Supply chain models** (catalog vs crossref vs self-source)
- **Consignment relationships** (fab-specific vs generic stock)
- **Part number schemas** (LCSC vs distributor catalogs vs manufacturer data)

## Phase 2 Completed Tasks
Completed on `feature/issue-59-fabricator-schema-migration`:
- ✅ Task 2.0: Schema migration (`field_synonyms` + `tier_rules`)
- ✅ Task 2.1: `FabricatorConfig` parsing + validation
- ✅ Task 2.2: `FabricatorInventorySelector` service (4-stage filter)
- ✅ Task 2.4: Matcher updated for `(preference_tier, item.priority, -score)` ordering
- ⏭ Task 2.3: Integration tests (deferred - covered by unit tests + BDD)

## Next Action: Start Phase 3

**Primary task**: Integrate `FabricatorInventorySelector` into BOM generation workflow.

**References**:
- `docs/workflow/planning/JBOM_NEW_ROADMAP.md` - Phase 3 tasks (service integration)
- `docs/workflow/PHASE_2_TASKS.md` - Phase 2 implementation details (reference)

## Phase 1 design note (keep)
Our tests and discussion clarified an important design nuance:
- The exact numeric scoring is not inherently valuable; it is a mechanism to achieve good ranking and to eliminate unsuitable matches.
- Longer term, we may want to evolve matching heuristics toward expressing intent more directly (e.g., "correct type/value/package always beats anything else", and priority is applied as a first-class ordering constraint), instead of relying on opaque point totals.
- If we do replace the scoring mechanism in the future, preserve the behavioral contracts: filtering correctness + ordering invariants.

## SEE ALSO
- `docs/architecture/adr/0001-fabricator-inventory-selection-vs-matcher.md`
- `docs/architecture/anti-patterns.md`
- `docs/workflow/planning/JBOM_NEW_ROADMAP.md` (complete roadmap)
- `docs/workflow/PHASE_2_TASKS.md` (Phase 2 tactical tasks)
