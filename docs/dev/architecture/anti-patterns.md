# Legacy jBOM Anti-Patterns (Phase 1 Extraction Notes)

This document captures specific architectural anti-patterns found in the legacy ("old-jbom") codebase.

Goal: as we port the sophisticated inventory matcher into jbom-new, we want to preserve the proven behavior while *not* re-importing the legacy structure, coupling, and hidden side effects.

Each section is written in a lightweight ADR style.

## AP-1: Hidden file I/O and side effects during service construction

### Problem
Some domain services perform file I/O in `__init__`, creating hidden side effects and making the object hard to test.

**Example**: `src/jbom/processors/inventory_matcher.py:38-56`
```python
class InventoryMatcher:
    def __init__(self, inventory_path: Optional[Union[Path, List[Path]]] = None):
        self.inventory_path = inventory_path
        self.inventory: List[InventoryItem] = []
        self.inventory_fields: List[str] = []
        if self.inventory_path:
            self._load_inventory()

    def _load_inventory(self):
        loader = InventoryLoader(self.inventory_path)
        self.inventory, self.inventory_fields = loader.load()
```

### Constraints
- Phase 1 needs to faithfully port matching behavior.
- Inventory can come from multiple sources (CSV/XLSX/Numbers, project-derived inventory, federated inventory).
- Domain services should be deterministic and testable with in-memory data.

### Proposals
1. **Separate extraction from processing**: keep file reading in an inventory loader service/repository; pass `List[InventoryItem]` into the matcher.
2. Inject an `InventoryRepository` interface and let the matcher query it (more flexible, more abstraction).

### Decision
Use proposal (1) for Phase 1.

- In jbom-new, the matcher should accept inventory items (and possibly a configuration object) and not know about file formats.
- Inventory loading belongs in application orchestration or a dedicated "data extraction" service.

### Implications
- jbom-new will need a clear boundary between:
  - `InventoryReader` (file paths → domain objects)
  - `InventoryMatcher` (domain objects → match results)
- Tests become straightforward (construct inventory in the test, no temp files).

## AP-2: Debugging / presentation concerns leak into domain logic

### Problem
Legacy services mix business logic with debug-string creation and printing warnings. This couples algorithms to UX decisions and creates side effects that are hard to control in tests.

**Examples**:

1) Debug string assembly inside core matching loop: `src/jbom/processors/inventory_matcher.py:57-120`
```python
def find_matches(self, component: Component, debug: bool = False, ...) -> List[Tuple[...]]:
    debug_info = []
    if debug:
        debug_info.append(f"Component: {component.reference} ({component.lib_id})")
    ...
    result_debug = "; ".join(debug_info) if debug and debug_info else None
    return [(itm, sc, result_debug if i == 0 else item_debug) ...]
```

2) Printing warnings from generator logic: `src/jbom/generators/bom.py:537-546`
```python
print(
    f"Warning: Unexpected SMD field value '{smd_field}' ...",
    file=sys.stderr,
)
```

### Constraints
- We still want rich diagnostics during matching.
- The same matching service must be usable from CLI, KiCad plugin, tests, and potentially a GUI.

### Proposals
1. Return structured diagnostics (dataclasses) from domain services; format them in application/interface layers.
2. Add a logger dependency to domain services.

### Decision
Use proposal (1) as the default pattern in jbom-new.

- Domain services return rich *data*.
- Application layer decides whether to emit console output, add CSV "Notes" columns, etc.

### Implications
- Introduce (or reuse) a `MatchDiagnostics` / `DiagnosticEvent` value object (not strings).
- No `print()` in domain services.
- CLI becomes a consumer of diagnostics rather than the source of diagnostic formatting.

## AP-3: Unstructured "result dictionaries" and cross-layer data plumbing

### Problem
Some APIs return dictionaries containing heterogeneous objects, requiring callers to know internal keys and reach into internal implementation details.

**Example**: `src/jbom/cli/commands/builtin/bom.py:120-213` expects `generate_bom()` to return a dict with keys like `"generator"`, `"bom_entries"`, `"available_fields"`, etc.

It also calls a private method on the returned generator:

`src/jbom/cli/commands/builtin/bom.py:139-147`
```python
if "generator" in result and hasattr(result["generator"], "_generate_diagnostic_message"):
    msg = result["generator"]._generate_diagnostic_message(diag, "console")
```

### Constraints
- The CLI needs both:
  - domain results (BOM entries)
  - metadata (available fields, diagnostics)
- Phase 1 migration should minimize churn, but jbom-new should not repeat this coupling.

### Proposals
1. Replace dict returns with typed result objects (dataclasses) that explicitly define what the caller can use.
2. Keep dicts but centralize keys in constants and treat them as a stable contract.

### Decision
Use proposal (1) in jbom-new.

- A `GenerateBomResult` (or similar) dataclass becomes the contract.
- The CLI must not call private generator methods; formatting is an adapter responsibility.

### Implications
- Results become discoverable and type-checkable.
- Future refactors do not require "hunt all dict key users" changes.

## AP-4: Leaky encapsulation via private method calls across services

### Problem
Services frequently call each other’s private helpers, which means internal refactors become breaking changes.

**Example**: `src/jbom/generators/bom.py:548-555`
```python
comp_pkg = self.matcher._extract_package_from_footprint(component.footprint)
comp_val_norm = self.matcher._normalize_value(component.value) if component.value else ""
```

### Constraints
- We want to share normalization and classification logic.
- We do *not* want a monolithic "utils" module with unclear ownership.

### Proposals
1. Promote shared logic into domain-model-level pure functions (e.g., `value_parsing`, `package_matching`, `component_classification`).
2. Expose the helper methods as public APIs on the matcher class.

### Decision
Use proposal (1).

- Shared normalization/classification helpers belong in the domain model layer as pure functions.
- Domain services should keep private helpers private.

### Implications
- This aligns directly with Phase 1 Tasks 1.2–1.4 (extract these utilities first).
- The matcher’s public interface can stay small (e.g., `find_matches(...)`).

## AP-5: Monolithic conditional logic for property matching and scoring

### Problem
Large "do everything" methods implement many categories of rules with extensive branching and "stringly typed" field names.

**Example**: `src/jbom/processors/inventory_matcher.py:319-495` (`_match_properties`) handles tolerance/voltage/current/power plus multiple component-type-specific branches and generic matching.

This produces:
- high cognitive complexity
- unclear extension points
- weak contracts around which fields matter for which component types

### Constraints
- The legacy matching behavior is valuable and should be preserved.
- We want to keep Phase 1 scope small (avoid designing a full rule engine).

### Proposals
1. Break into small pure scoring functions per responsibility (tolerance, voltage, etc.) and per component type where needed.
2. Implement a pluggable strategy/rule engine.

### Decision
Use proposal (1) for Phase 1.

- Keep the algorithm, but decompose it into testable units.
- Return a structured `MatchScoreBreakdown` so callers can explain *why* a match scored as it did.

### Implications
- The ported matcher can maintain exact outputs while gaining clearer internal structure.
- Tests can lock in behavior per sub-score category.

## See also
- `design-patterns.md`
- `layer-responsibilities.md`
- `why-jbom-new.md`
