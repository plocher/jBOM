# ADR 0001: Fabricator-Aware Inventory Selection vs Matcher Responsibility
Date: 2026-02-25
Status: Accepted

## Context
In jbom-new, matching is being refactored into clean, testable domain services.

The desired end-to-end workflow is:
1. A large set of `InventoryItem` exists (possibly from multiple sources).
2. A fabricator-specific selection step prunes the inventory to items that are usable for that fabricator.
3. KiCad `Component`s are matched against the remaining items.

Some fabricators prefer a "native catalog" identifier (e.g., JLC's LCSC part number), but can fall back to non-catalog items when they can be cross-referenced using a manufacturer part number (e.g., MPN/MFGPN).

This implies a *multi-step policy*:
- Eligibility/pruning: keep items that have *either* a native catalog part number *or* a manufacturer part number.
- Preference/ranking: prefer items with native catalog IDs over items that only have manufacturer IDs.

We already have fabricator configuration with `part_number.priority_fields` (e.g., in `src/jbom/config/fabricators/*.fab.yaml`) that expresses which identifiers are preferred.

## Decision Drivers
- Preserve domain-centric boundaries (no CLI/I/O concerns in domain services).
- Port desired behavior, not legacy structure.
- Keep the matcher interface simple and testable.
- Support multi-step fabricator policies (eligibility + preference + fallback).
- Avoid duplicating fabricator selection logic across the codebase.

## Options

### Option A: Fabricator selection is a separate step (recommended separation)
Create/keep a distinct fabricator-aware service/function that:
- filters inventory to eligible items for a given fabricator
- optionally annotates items with selection metadata (e.g., which identifier field matched)
- optionally computes a preference tier to be used in ordering

The matcher stays fabricator-agnostic:
- input: `(component, eligible_inventory_items)`
- output: match results ordered by match score / priority

Pros:
- Cleanest separation of concerns.
- Matcher stays reusable across contexts (CLI, API, tests).
- Easier to unit test selection policy vs matching policy independently.

Cons:
- Requires an explicit orchestration step to ensure inventory is pre-filtered.
- Need a defined contract for how preference influences ordering (e.g., effective priority vs tiebreak).


### Option B: Add a fabricator parameter/policy to the matcher
Extend the matcher configuration (e.g., `MatchingOptions`) to include a fabricator policy derived from `FabricatorConfig.part_number.priority_fields`.

Matcher performs:
- fabricator eligibility pruning (and/or preference tiering)
- then matching

Pros:
- Single call does everything for the common CLI workflow.
- Harder to misuse (can’t forget the selection step).

Cons:
- Coupling: matcher now needs to understand fabricator concepts.
- More complex unit tests and public API.
- Risk of scope creep (matcher becomes an orchestration layer).


### Option C: Hybrid — external selection + matcher tie-break input
Selection remains external (Option A), but the matcher accepts a small, domain-friendly ordering hint (not a full fabricator object), e.g.:
- per-item `preference_tier` (catalog vs crossref)
- or a comparator/key function supplied at construction

Pros:
- Keeps fabricator logic out of matcher while still allowing consistent ordering.
- Small API surface.

Cons:
- Requires defining a stable, typed representation for ordering hints.

## Open Questions
- Where should the catalog-vs-crossref preference be applied?
  - Convert to `effective_priority` during selection?
  - Or add a tie-break layer in matcher ordering: `(priority asc, preference_tier asc, score desc)`?
- Should eligibility be "any of priority_fields" or a stricter rule per fabricator?
- Do we need to preserve legacy ordering exactly, or is adding a preference tier acceptable in Phase 1?

## Decision
**Chosen: Option A (Separate Selection Step)**

Fabricator-aware inventory selection will be a separate service/step from matching.

### Key Design Principles

#### Two Independent Priority Concepts (CRITICAL)
These are distinct concepts that must NOT be conflated:

1. **Item.priority (User's Stock Management)**
   - Purpose: User controls which IPN to consume first for inventory management
   - Example: Priority=1 for expensive reel (use first), Priority=2 for cheap basic part (use after)
   - Semantics: Lower number = use first
   - Set by: User in inventory file
   - Scope: Applies to ALL fabricators
   - Used in: Matcher sorting (secondary key)

2. **Fabricator Preference Tier (Catalog vs Crossref)**
   - Purpose: Fabricator prefers native catalog items over crossref items
   - Example: JLCPCB prefers LCSC catalog items, falls back to MPN crossref
   - Semantics: Tier 0=catalog (best), Tier 1=crossref, Tier 2=fallback
   - Set by: Fabricator config YAML (priority_fields order)
   - Scope: Fabricator-specific
   - Used in: Selection eligibility + matcher sorting (primary key)

**IMPORTANT**: Fabricator selection must NOT modify `item.priority` - that belongs to the user.
Instead, selection adds a separate `preference_tier` dimension.

### Implementation Design

#### Phase 1 (Task 1.5b-c): Matcher stays fabricator-agnostic
```python
class SophisticatedInventoryMatcher:
    def find_matches(
        component: Component,
        inventory: List[InventoryItem]  # Pre-selected by caller
    ) -> List[MatchResult]:
        # Sorts by: (item.priority, -score)
        # No fabricator concepts in matcher
```

Documentation note: "Caller responsible for fabricator-specific filtering.
For fabricator-aware ordering, use FabricatorInventorySelector (future)."

#### Phase 2 (Future): Add FabricatorInventorySelector service
```python
@dataclass
class EligibleInventoryItem:
    """Inventory item with fabricator selection metadata."""
    item: InventoryItem
    preference_tier: int  # 0=catalog, 1=crossref, 2=fallback
    matched_field: str    # Which priority_field matched ("LCSC", "MPN", etc.)

class FabricatorInventorySelector:
    """Selects eligible inventory for a fabricator."""

    def __init__(self, fabricator_config: FabricatorConfig):
        self._config = fabricator_config

    def select_eligible(
        self,
        inventory: List[InventoryItem]
    ) -> List[EligibleInventoryItem]:
        """Filter inventory and annotate with preference tier.

        Returns items that have at least one field from priority_fields.
        Annotates each with preference_tier based on which field matched.
        Does NOT modify item.priority (user's stock management).
        """
```

**Matcher update (Phase 2):**
```python
def find_matches(
    component: Component,
    eligible_inventory: List[EligibleInventoryItem]
) -> List[MatchResult]:
    # Sorts by: (preference_tier, item.priority, -score)
```

**Example ordering for JLCPCB:**
1. LCSC parts with Priority=1 (expensive stock, catalog)
2. LCSC parts with Priority=2 (cheap stock, catalog)
3. MPN-only parts with Priority=1 (expensive stock, crossref)
4. MPN-only parts with Priority=2 (cheap stock, crossref)

### Rationale

**Why Option A:**
- ✅ Clean separation of concerns (selection vs matching)
- ✅ Matcher stays reusable and testable
- ✅ Preserves both priority concepts independently
- ✅ Ports behavior without porting legacy coupling
- ✅ Selection service can be added in Phase 2 without breaking Phase 1

**Why not Option B:**
- ❌ Couples matcher to fabricator concepts
- ❌ Violates single responsibility
- ❌ Re-introduces anti-pattern we're removing from legacy

**Why not Option C:**
- ⚠️ Adds abstraction complexity (preference_tier hints)
- ⚠️ Option A with `EligibleInventoryItem` wrapper achieves same result more clearly

### Answers to Open Questions

**Q: Where should catalog-vs-crossref preference be applied?**
A: As separate `preference_tier` dimension during selection (primary sort key).
Does NOT modify user's `item.priority`.

**Q: Should eligibility be "any of priority_fields" or stricter?**
A: "Any of" (matches legacy behavior: item is eligible if ANY priority_field exists).

**Q: Do we need exact legacy ordering?**
A: No. Adding preference_tier as explicit dimension is better than legacy's
implicit coupling. Legacy hardcoded "generic" check is tech debt we're NOT porting.

## Consequences

### Positive
- Matcher service is simple, testable, and fabricator-agnostic
- Selection logic is isolated in dedicated service
- Both priority concepts remain independent and visible
- Phase 1 can complete without implementing full fabricator selection
- Clean foundation for Phase 2 enhancements

### Negative
- Requires orchestration layer to coordinate selection + matching
- Phase 1 matcher documentation must clearly state "caller handles fabricator filtering"
- Phase 2 work needed to add FabricatorInventorySelector

### Neutral
- Changes legacy API shape (separate calls vs single call with fabricator param)
- This is acceptable: we're porting behavior, not structure
