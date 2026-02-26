# Task 1.5: Matcher Service Interface Design

**Date**: 2026-02-25
**Status**: Design Review (Checkpoint)
**Goal**: Define clean interface for inventory matcher that ports behavior, not structure

## Key Behaviors to Port

From legacy analysis:
1. **Primary filtering** (fast path): type/category, package, exact value
2. **Scoring algorithm**: weighted match across multiple dimensions
3. **Priority handling**: inventory items have priorities (lower = better)
4. **Optional debug diagnostics**: structured information about match quality

## Anti-Pattern Avoidance

Per `anti-patterns.md`:
- **AP-1**: NO file I/O in constructors - accept `List[InventoryItem]`
- **AP-2**: NO debug strings in domain logic - return structured diagnostics
- **AP-3**: NO dict returns - use typed dataclasses
- **AP-4**: NO private method leakage - use pure functions from common/
- **AP-5**: NO monolithic scoring - decompose into testable sub-scorers

### Legacy Tech Debt NOT Being Ported

1. **Hardcoded fabricator ID checks** (config_fabricators.py:89):
   - Legacy: `if self.config.id == "generic": return True`
   - jbom-new: Generic behavior is fully declarative in `generic.fab.yaml` (no ID checks in code)

2. **File I/O in matcher constructor** (inventory_matcher.py:38-43):
   - Legacy: `__init__(inventory_path)` loads files
   - jbom-new: `__init__(inventory_items)` accepts data

3. **Debug string construction in domain logic** (inventory_matcher.py:73-109):
   - Legacy: Builds debug strings inline during matching
   - jbom-new: Return structured `MatchScore` with breakdown

## Proposed Interface

### Input Types
```python
@dataclass
class Component:
    """Schematic component (from KiCad)."""
    reference: str
    lib_id: str
    value: str
    footprint: str
    properties: Dict[str, str]  # Tolerance, Voltage, etc.

@dataclass
class InventoryItem:
    """Inventory line (from CSV/XLSX/Numbers)."""
    ipn: str
    category: str
    value: str
    package: str
    priority: int  # Lower = prefer
    # Plus optional: tolerance, voltage, wattage, manufacturer, etc.
```

### Output Types
```python
@dataclass
class MatchScore:
    """Breakdown of how a match scored."""
    total: int
    type_match: int      # 50 points
    value_match: int     # 40 points
    package_match: int   # 30 points
    property_score: int  # Varies (tolerance, voltage, etc.)

@dataclass
class ComponentMatch:
    """A single inventory item matched to a component."""
    inventory_item: InventoryItem
    score: MatchScore
    rank: int  # 1-based after sorting

@dataclass
class MatchResult:
    """Complete match result for one component."""
    component: Component
    matches: List[ComponentMatch]  # Sorted by priority, then score desc
    candidates_evaluated: int
    candidates_passed_filter: int
```

### Service Interface
```python
from jbom.common.config_fabricators import ConfigurableFabricator

class InventoryMatcherService:
    """Matches schematic components to inventory items using sophisticated scoring."""

    def __init__(self, inventory_items: List[InventoryItem]):
        """Initialize with inventory (no I/O).

        Args:
            inventory_items: Pre-loaded and merged inventory from all sources.
                            Caller is responsible for loading, merging, and setting priorities.
        """
        self._inventory = inventory_items

    def find_matches(
        self,
        component: Component,
        *,
            fabricator: Optional[ConfigurableFabricator] = None,
            min_score: int = 0,
    ) -> MatchResult:
        """Find matching inventory items for a component.

        Args:
            component: Component to match
            fabricator: Optional fabricator config (YAML-driven).
                       Fabricator-specific selection is based on `field_synonyms` + `tier_rules`.
                       (Phase 2 keeps that selection as a separate step from matching; see ADR 0001.)
            min_score: Minimum score threshold (default: return all candidates)

        Returns:
            MatchResult with matches sorted by (item.priority, -score)
        """
```

## Scoring Algorithm (Ported Behavior)

### Primary Filters (fast rejection)
1. **Type/Category**: If determined, must match
2. **Package**: If extracted, must match
3. **Value**: Exact numeric match for RES/CAP/IND

### Scoring Weights (from legacy)
- Type match: **50 points**
- Value match: **40 points**
- Package match: **30 points**
- Properties (varies):
  - Tolerance exact: **15 points**
  - Tolerance tighter: **10 points**
  - Voltage match: **10 points**
  - Power/Wattage match: **10 points**

### Sorting
1. Priority (ascending - lower is better)
2. Score (descending - higher is better)

## Implementation Strategy

### Phase 1 Scope (Simple)
- Single `InventoryMatcherService` class
- Uses pure functions from `common/`:
  - `component_classification.py` (Task 1.4)
  - `value_parsing.py` (Task 1.2)
  - `package_matching.py` (Task 1.3)
- Scoring logic decomposed into private helper methods
- Return structured `MatchResult` (not debug strings)

### Future Extensions (Out of Scope)
- Pluggable scoring strategies
- Multi-inventory federation
- Fuzzy matching
- Machine learning

## Dependencies

Already extracted (Tasks 1.2-1.4):
- `jbom.common.value_parsing`
- `jbom.common.package_matching`
- `jbom.common.component_classification`

## Key Design Questions

1. **Fabricator filtering**: Pass as lambda or declarative config?
   - **Decision**: Use declarative fabricator config (no lambdas) and keep selection separate from matching (ADR 0001).
   - Rationale: Catalog creators evolve their column names; `field_synonyms` normalizes that.
   - Fabricator preference is policy-based: `tier_rules` defines ordering/tie-breaks without hardcoding.
   - **Tech debt fix**: Avoid fabricator-ID special cases; generic behavior is defined in `generic.fab.yaml`.

2. **Multi-inventory handling**: Matcher or separate orchestration?
   - **Decision**: Caller merges inventories before passing to matcher
   - Rationale:
     - Phase 1 scope: port matching algorithm (not inventory federation)
     - Legacy `InventoryLoader` already handles multiple paths → single list
     - Priority management via inventory file (user controls: Priority=1 for expensive stock)
   - Future: Could add `InventoryRepository` as separate orchestration layer

3. **Debug diagnostics**: Include in every `MatchScore` or separate flag?
   - **Decision**: Always include score breakdown - cheap to compute

4. **Tolerance matching**: Port exact legacy logic or simplify?
   - **Decision**: Port exact logic (proven behavior)

5. **Should matcher validate inventory items**?
   - **Decision**: No - validation is loader responsibility (separation of concerns)

## Success Criteria

- ✅ No file I/O in domain service
- ✅ No debug strings in return values
- ✅ Pure functions for all normalization/classification
- ✅ Typed return values (no dicts)
- ✅ Testable with in-memory data
- ✅ Ports proven scoring behavior from legacy
- ✅ Single responsibility: matching (not loading, not formatting)

## Estimated Implementation

- Task 1.5b: Primary filtering logic (45-60 min)
- Task 1.5c: Scoring algorithm (60-90 min)
- Task 1.5d: Tests (60 min)

Total: ~3-4 hours agent work
