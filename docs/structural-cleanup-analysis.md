# Structural Cleanup Analysis

## Overview
Analysis of remaining structural issues and cleanup opportunities after the 2.0 refactoring.

---

## Issue 1: Unused Legacy Shims in sch/ Package

### Current State
The `src/jbom/sch/` package contains several "Phase P0" shim files that were meant to be temporary:

```
src/jbom/sch/api.py       - Shims GenerateOptions, generate_bom_api
src/jbom/sch/model.py      - Shims Component
src/jbom/sch/bom.py        - Shims BOMEntry, BOMGenerator
src/jbom/sch/parser.py     - Shims KiCadParser
```

All contain comments like:
```python
"""Phase P0 refactor: export the public API from jbom.jbom so callers can
import from jbom.sch.api without behavior change."""
```

### Analysis
**Actual usage check:**
- ✅ `src/jbom/cli/main.py` imports directly from `jbom.jbom` (NOT the shims)
- ✅ Tests import directly from `jbom` or `jbom.jbom` (NOT the shims)
- ❌ The shims are ONLY referenced in documentation examples
- ❌ No code actually uses these shim modules

### Recommendation: REMOVE SHIMS

**Rationale:**
1. They were marked as "Phase P0" temporary
2. No code depends on them
3. They add confusion (two ways to import the same thing)
4. They complicate the module structure

**Impact:** None - nothing uses them except docs

**Action:**
1. Remove the 4 shim files
2. Update documentation to show correct import paths
3. Update `src/jbom/sch/__init__.py` to not export shims

---

## Issue 2: BOM API in Wrong Location

### Current State
`generate_bom_api()` and related BOM code is in `src/jbom/jbom.py` (2700+ lines, monolithic file).

The BOM-specific code should logically be in `src/jbom/sch/` since it's schematic-related.

### Why It Matters
- `jbom.py` is a God Object (too many responsibilities)
- Violates the module structure established in refactoring
- `sch/` package is supposed to contain schematic-related code
- Makes the codebase harder to understand

### Current Structure
```
jbom.py (2700 lines):
  - Component class
  - InventoryMatcher class
  - BOMGenerator class
  - generate_bom_api() function
  - Field parsing logic
  - KiCadParser class
  - Inventory loading
  - Value parsers
  - ... everything
```

### Desired Structure
```
sch/
  api.py          - generate_bom_api() (actual implementation)
  bom.py          - BOMGenerator, BOMEntry (actual implementation)
  parser.py       - KiCadParser (actual implementation)
  model.py        - Component (actual implementation)

inventory/
  matcher.py      - InventoryMatcher (actual implementation)
  
common/
  values.py       - Value parsers (already extracted)
  fields.py       - Field utilities (already extracted)
  
jbom.py          - Re-exports for backward compatibility only
```

### Recommendation: EXTRACT CODE FROM jbom.py

This is the "finish the refactoring" work that was started but not completed.

**Estimated Effort:** 
- Extract to modules: 6-8 hours
- Update imports: 2-3 hours
- Test everything: 4-6 hours
- **Total: 12-17 hours (2-3 days)**

**Risk:** Medium - requires careful import management and testing

---

## Issue 3: Duplicate S-expression Parsing

### Current State
S-expression parsing using `sexpdata` library appears in two places:

1. **Schematic parsing** (`jbom.py` line 18)
   - `KiCadParser` class parses `.kicad_sch` files
   - Extracts components, properties, hierarchical sheets

2. **PCB parsing** (`pcb/board_loader.py` lines 107-123)
   - `BoardLoader._load_with_sexp()` parses `.kicad_pcb` files
   - Extracts footprints, positions, rotations

### Analysis: Can They Be Shared?

**Similarities:**
- Both use `sexpdata.loads()`
- Both use `Symbol` for S-expression node types
- Both use recursive walking patterns
- Both parse KiCad file formats

**Differences:**
- **Schematic**: Looks for `(symbol ...)` nodes, properties, sheets
- **PCB**: Looks for `(footprint ...)` nodes, position, layer
- **Different data models**: `Component` vs `PcbComponent`
- **Different extraction logic**: Schematic is more complex (hierarchical, properties)

### Recommendation: SHARED LOW-LEVEL, SPECIALIZED HIGH-LEVEL

Create a shared S-expression utility module:

```python
# src/jbom/common/sexp_parser.py

from sexpdata import loads, Symbol

def load_kicad_file(path: Path):
    """Load and parse a KiCad S-expression file."""
    text = path.read_text(encoding='utf-8')
    return loads(text)

def walk_nodes(sexp, node_type: str):
    """Generator that yields all nodes of a specific type.
    
    Example:
        for footprint_node in walk_nodes(sexp, 'footprint'):
            # process footprint
    """
    def walk(n):
        if isinstance(n, list) and n:
            if n[0] == Symbol(node_type):
                yield n
            else:
                for child in n:
                    yield from walk(child)
    yield from walk(sexp)

def find_child(node, child_type: str):
    """Find first child node of given type."""
    for child in node[1:]:
        if isinstance(child, list) and child and child[0] == Symbol(child_type):
            return child
    return None

def find_all_children(node, child_type: str):
    """Find all child nodes of given type."""
    results = []
    for child in node[1:]:
        if isinstance(child, list) and child and child[0] == Symbol(child_type):
            results.append(child)
    return results
```

**Then both parsers use it:**

```python
# sch/parser.py
from jbom.common.sexp_parser import load_kicad_file, walk_nodes

class KiCadParser:
    def parse(self):
        sexp = load_kicad_file(self.schematic_path)
        for symbol_node in walk_nodes(sexp, 'symbol'):
            component = self._parse_symbol(symbol_node)
            # ...

# pcb/board_loader.py
from jbom.common.sexp_parser import load_kicad_file, walk_nodes

class BoardLoader:
    def _load_with_sexp(self):
        sexp = load_kicad_file(self.board_path)
        for footprint_node in walk_nodes(sexp, 'footprint'):
            component = self._parse_footprint_node(footprint_node)
            # ...
```

**Benefits:**
- ✅ Eliminates duplicate `loads()` calls
- ✅ Shared walking logic
- ✅ Common utility functions
- ✅ Easier to test
- ✅ Single import point for sexpdata dependency

**Effort:** 
- Create shared module: 2 hours
- Refactor both parsers to use it: 3-4 hours
- Test: 2 hours
- **Total: 7-8 hours (1 day)**

**Risk:** Low - purely extracting common patterns

---

## Issue 4: inventory/ Package Structure

### Current State
```
inventory/
  __init__.py     - Re-exports from jbom.jbom
  matcher.py      - Shim that re-exports InventoryMatcher
```

Similar to `sch/`, this is just shims.

### Recommendation: SAME AS ISSUE 2

Move actual `InventoryMatcher` implementation to `inventory/matcher.py`, keep backward-compat re-export in `jbom.py`.

---

## Priority Ranking

### High Priority (Do Soon)
1. **Remove unused shims** (1-2 hours, zero risk)
   - Issue 1: Remove sch/ shims
   - Update docs to use correct imports

### Medium Priority (Next Sprint)
2. **Extract S-expression utilities** (1 day, low risk)
   - Issue 3: Create common/sexp_parser.py
   - Refactor both parsers to use it
   - Clear win with minimal risk

### Low Priority (Future Refactoring)
3. **Extract BOM code from jbom.py** (2-3 days, medium risk)
   - Issue 2: Move BOMGenerator, generate_bom_api to sch/
   - Issue 4: Move InventoryMatcher to inventory/
   - Requires careful testing
   - Part of "finish the modular refactoring"

---

## Detailed Action Plan

### Phase 1: Remove Dead Shims (Quick Win)

**Files to delete:**
```
src/jbom/sch/api.py
src/jbom/sch/model.py  
src/jbom/sch/bom.py
src/jbom/sch/parser.py
src/jbom/inventory/matcher.py
```

**Files to update:**
```
src/jbom/sch/__init__.py     - Remove shim exports
src/jbom/inventory/__init__.py - Remove shim exports
README.md                     - Update import examples
docs/README.arch.md          - Update import examples
docs/README.developer.md     - Update import examples
```

**Testing:**
- Run full test suite
- Verify imports still work from jbom.jbom
- Check that no code broke

**Commit message:**
```
refactor: Remove unused Phase P0 shim modules

These shims were temporary compatibility wrappers that are no longer
used by any code. They only appear in documentation examples.

- Remove sch/api.py, sch/model.py, sch/bom.py, sch/parser.py
- Remove inventory/matcher.py shim
- Update documentation to show correct import paths
- Simplify package structure

All code imports directly from jbom or jbom.jbom, not these shims.
```

### Phase 2: Extract S-expression Utilities

**Create:**
```
src/jbom/common/sexp_parser.py
```

**Update:**
```
src/jbom/jbom.py - Use shared utilities
src/jbom/pcb/board_loader.py - Use shared utilities  
src/jbom/common/__init__.py - Export new module
```

**Test:**
- Unit tests for utility functions
- Integration tests for both parsers
- Verify schematic and PCB loading unchanged

### Phase 3: Extract BOM Code (Future)

This is the big one - requires its own planning session.

**Scope:**
- Move ~1000 lines from jbom.py to sch/
- Move ~500 lines from jbom.py to inventory/
- Keep backward compat wrapper in jbom.py
- Update all imports
- Comprehensive testing

---

## Summary

### What We Found
1. ✅ **Unused shims** - Safe to remove immediately
2. ✅ **Duplicate S-expression code** - Easy to extract and share
3. ⚠️ **God Object (jbom.py)** - Needs gradual extraction
4. 📝 **Incomplete refactoring** - "Phase P0" never finished

### Quick Wins Available
- Remove shims: 1-2 hours
- Extract S-expression utils: 1 day

### Bigger Investment
- Finish extracting jbom.py: 2-3 days (future work)

### Your Observation Was Correct
The "Phase P0 refactor" mentioned in comments was indeed never completed. The shims were meant to be temporary but became permanent. They're now dead code that should be removed.
