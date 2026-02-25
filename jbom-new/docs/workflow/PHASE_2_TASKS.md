# Phase 2: Tactical Task Breakdown

**Status**: Ready to start
**Date**: 2026-02-25
**Context**: Phase 1 complete (PR #57), schema refactored (Issues #59, #60)

## Overview
Phase 2 implements fabricator-aware inventory selection as described in ADR 0001.
Work must proceed in dependency order: schema → selector → matcher integration.

## Prerequisites Completed
- ✅ Phase 1: Sophisticated matcher (PR #57, Issue #48)
- ✅ Design: Field synonyms + tier separation (Issue #59)
- ✅ Design: Consignment + project filtering (Issue #60)

## Task Sequence

### Task 2.0: Fabricator Config Schema Migration (Issue #59)
**Estimated**: 3-4 hours
**Prerequisite**: None (can start immediately)

Migrate existing fabricator configs to new schema with field_synonyms and explicit tiers.

**Files to modify:**
- `src/jbom/config/fabricators/generic.fab.yaml`
- `src/jbom/config/fabricators/jlc.fab.yaml`
- `src/jbom/config/fabricators/pcbway.fab.yaml`
- `src/jbom/config/fabricators/seeed.fab.yaml`

**New schema structure:**
```yaml
field_synonyms:
  fab_pn:
    synonyms: ["LCSC", "LCSC Part", "JLC Part"]
    display_name: "LCSC Part Number"
  mpn:
    synonyms: ["MPN", "MFGPN"]
    display_name: "MPN"

tier_rules:
  0:
    conditions:
      - field: "Consigned"
        operator: "exists"
  1:
    conditions:
      - field: "Preferred"
        operator: "exists"
      - field: "fab_pn"
        operator: "exists"
  2:
    conditions:
      - field: "fab_pn"
        operator: "exists"
  3:
    conditions:
      - field: "mpn"
        operator: "exists"
```

**Key change**: Tiers are based on inventory item properties (Consigned, Preferred), not which field name exists. After field synonym normalization, all LCSC variants → `fab_pn`.

**Action items:**
1. Update `generic.fab.yaml` first (simplest - single tier)
2. Update `jlc.fab.yaml` (catalog + crossref tiers)
3. Update `pcbway.fab.yaml` and `seeed.fab.yaml`
4. Verify YAML syntax with `python -c "import yaml; yaml.safe_load(open('jlc.fab.yaml'))"`

**Success criteria:**
- All 4 configs have new schema
- Old `part_number.priority_fields` removed
- YAML parses without errors

---

### Task 2.1: Update FabricatorConfig Dataclass
**Estimated**: 2-3 hours
**Prerequisite**: Task 2.0 (schema migration)

Update `FabricatorConfig` to parse new schema and provide accessor methods.

**Files to modify:**
- `src/jbom/config/fabricator_config.py` (or wherever `FabricatorConfig` is defined)

**Implementation:**
```python
@dataclass
class FieldSynonym:
    """Field synonym definition with display name."""
    synonyms: List[str]
    display_name: str

@dataclass
class TierCondition:
    """Condition for tier matching."""
    field: str
    operator: str  # "exists", "equals", "not_empty"
    value: Optional[str] = None

@dataclass
class TierRule:
    """Rule for assigning a tier."""
    conditions: List[TierCondition]

    def matches(self, item: InventoryItem) -> bool:
        """All conditions must be true (AND logic)."""
        for cond in self.conditions:
            field_value = item.raw_data.get(cond.field, "")

            if cond.operator == "exists":
                if not field_value:
                    return False
            elif cond.operator == "not_empty":
                if not field_value.strip():
                    return False
            elif cond.operator == "equals":
                if field_value != cond.value:
                    return False
        return True

@dataclass
class FabricatorConfig:
    # ... existing fields ...

    field_synonyms: Dict[str, FieldSynonym]  # canonical -> synonym config
    tier_rules: Dict[int, TierRule]          # tier number -> rule

    @staticmethod
    def from_yaml(yaml_dict: dict) -> 'FabricatorConfig':
        """Parse new schema from YAML."""
        # Parse field_synonyms
        field_synonyms = {}
        for canonical, config in yaml_dict.get('field_synonyms', {}).items():
            field_synonyms[canonical] = FieldSynonym(
                synonyms=config['synonyms'],
                display_name=config['display_name']
            )

        # Parse tier_rules
        tier_rules = {}
        for tier_num, rule_config in yaml_dict.get('tier_rules', {}).items():
            conditions = [
                TierCondition(
                    field=c['field'],
                    operator=c['operator'],
                    value=c.get('value')
                )
                for c in rule_config.get('conditions', [])
            ]
            tier_rules[int(tier_num)] = TierRule(conditions=conditions)

        return FabricatorConfig(
            field_synonyms=field_synonyms,
            tier_rules=tier_rules,
            # ... other fields ...
        )

    def resolve_field_synonym(self, field_name: str) -> Optional[str]:
        """Resolve field name variant to canonical name."""
        for canonical, config in self.field_synonyms.items():
            if field_name in config.synonyms:
                return canonical
        return None
```

**Tests to add:**
- `tests/unit/test_fabricator_config.py`:
  - Test YAML parsing with new schema
  - Test `resolve_field_synonym()` maps variants to canonical
  - Test tier lookup by canonical name
  - Test backward compatibility (old configs should fail gracefully with helpful error)

**Success criteria:**
- FabricatorConfig loads new YAML schema
- `resolve_field_synonym()` works for all synonyms
- All 4 configs load without errors
- Unit tests pass

---

### Task 2.2: Create FabricatorInventorySelector Service
**Estimated**: 4-6 hours
**Prerequisite**: Task 2.1 (FabricatorConfig updated)

Implement the four-stage selection filter as designed in Issue #60.

**Files to create:**
- `src/jbom/services/fabricator_inventory_selector.py`

**Implementation:**
```python
from dataclasses import dataclass
from typing import List, Optional
from jbom.common.types import InventoryItem
from jbom.config.fabricator_config import FabricatorConfig

@dataclass
class EligibleInventoryItem:
    """Inventory item with fabricator selection metadata."""
    item: InventoryItem
    preference_tier: int
    matched_canonical_field: str

class FabricatorInventorySelector:
    """Selects eligible inventory for a fabricator."""

    def __init__(self, fabricator_config: FabricatorConfig):
        self._config = fabricator_config

    def select_eligible(
        self,
        inventory: List[InventoryItem],
        project_name: Optional[str] = None
    ) -> List[EligibleInventoryItem]:
        """Four-stage filter: affinity → project → normalize → tier."""
        eligible = []

        for item in inventory:
            # Stage 1: Fabricator affinity filter
            if not self._passes_fabricator_filter(item):
                continue

            # Stage 2: Project restriction filter
            if not self._passes_project_filter(item, project_name):
                continue

            # Stage 3 & 4: Normalize fields and assign tier
            tier = self._assign_tier(item)
            if tier is None:
                continue  # No tier matched

            eligible.append(EligibleInventoryItem(
                item=item,
                preference_tier=tier,
                matched_canonical_field=""  # Not needed with tier_rules
            ))

        return eligible

    def _passes_fabricator_filter(self, item: InventoryItem) -> bool:
        """Keep if: item.fabricator == target OR item.fabricator == ''"""
        if not item.fabricator:
            return True  # Generic item, available to all
        return item.fabricator == self._config.id

    def _passes_project_filter(
        self,
        item: InventoryItem,
        project_name: Optional[str]
    ) -> bool:
        """Check project restriction (Issue #60)."""
        projects_field = item.raw_data.get('Projects', '').strip()

        if not projects_field:
            return True  # No restriction, available to all

        if not project_name:
            return False  # Item restricted but no project specified

        allowed = [p.strip() for p in projects_field.split(',')]
        return project_name in allowed

    def _assign_tier(
        self,
        item: InventoryItem
    ) -> Optional[int]:
        """Assign tier using fabricator's tier_rules."""
        # Check tiers in order (0, 1, 2, ...)
        for tier_num in sorted(self._config.tier_rules.keys()):
            rule = self._config.tier_rules[tier_num]

            # Empty conditions = match all (generic fab)
            if not rule.conditions:
                return tier_num

            # Check if item matches all conditions
            if rule.matches(item):
                return tier_num

        return None  # No tier matched
```

**Tests to add:**
- `tests/unit/test_fabricator_inventory_selector.py`:
  - Test fabricator affinity filter (keep generic + target, prune others)
  - Test project restriction filter (empty projects = available to all)
  - Test field normalization (synonyms → canonical)
  - Test tier assignment (Tier 0 before Tier 1)
  - Test consignment tier (Issue #60)

**Success criteria:**
- FabricatorInventorySelector passes all unit tests
- Four-stage filter works as designed
- Consignment support (Tier 0 for consigned items)

---

### Task 2.3: Integration Tests with Real Configs
**Estimated**: 2-3 hours
**Prerequisite**: Task 2.2 (selector implemented)

Test selector with real fabricator configs and SPCoast inventory.

**Files to create:**
- `tests/integration/test_fabricator_inventory_selection.py`

**Test scenarios:**
```python
def test_jlc_prefers_catalog_over_crossref():
    """JLC: LCSC catalog (Tier 0) beats MPN crossref (Tier 1)."""

def test_pcbway_prunes_jlc_items():
    """PCBWay: Items with fabricator=JLC are pruned."""

def test_consigned_beats_catalog():
    """Consigned items (Tier 0) beat catalog items (Tier 1)."""

def test_project_restriction():
    """Items restricted to CustomerA only match for CustomerA project."""

def test_generic_accepts_all():
    """Generic fabricator accepts all items (no filtering)."""
```

**Success criteria:**
- All integration tests pass with real configs
- SPCoast inventory loads and filters correctly

---

### Task 2.4: Update SophisticatedInventoryMatcher
**Estimated**: 2-3 hours
**Prerequisite**: Task 2.2 (selector implemented)

Extend matcher to accept `EligibleInventoryItem` and sort by preference_tier.

**Files to modify:**
- `src/jbom/services/sophisticated_inventory_matcher.py`

**Implementation changes:**
```python
def find_matches(
    self,
    component: Component,
    inventory: Union[List[InventoryItem], List[EligibleInventoryItem]]
) -> List[MatchResult]:
    """Match component to inventory. Accepts plain or eligible items."""

    # ... existing filtering logic ...

    # Sort results
    results.sort(key=lambda r: (
        self._get_preference_tier(r.item),  # New: tier first
        r.item.priority,                     # Existing: user priority second
        -r.score                             # Existing: match quality third
    ))

    return results

def _get_preference_tier(self, item: Union[InventoryItem, EligibleInventoryItem]) -> int:
    """Extract preference tier (0 if plain InventoryItem)."""
    if isinstance(item, EligibleInventoryItem):
        return item.preference_tier
    return 0  # Plain items treated as Tier 0
```

**Tests to update:**
- `tests/unit/test_sophisticated_inventory_matcher_scoring_and_ordering.py`:
  - Test ordering with preference tiers: `(tier, priority, -score)`
  - Test backward compatibility with plain InventoryItem list

**Success criteria:**
- Matcher accepts both plain and eligible items
- Sorting includes preference_tier as primary key
- Existing tests still pass

---

## Summary

**Total estimated effort**: 15-21 hours

**Dependency chain**:
```
Task 2.0 (Schema)
    ↓
Task 2.1 (Config dataclass)
    ↓
Task 2.2 (Selector service) → Task 2.4 (Matcher update)
    ↓
Task 2.3 (Integration tests)
```

**Completion criteria**:
- ✅ All 4 fabricator configs use new schema
- ✅ FabricatorInventorySelector implemented with 4-stage filter
- ✅ Consignment support (Tier 0)
- ✅ Project restriction support
- ✅ Matcher updated to sort by (tier, priority, -score)
- ✅ All unit and integration tests pass

**Next steps after Phase 2**:
- Phase 3: Wire selector into CLI commands
- Phase 4: End-to-end BOM generation tests
