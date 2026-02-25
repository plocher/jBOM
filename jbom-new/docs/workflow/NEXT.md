# What to Do Next

## Current Task
**Task 1.5b: Implement Primary Filtering** (Ready to start)

**Previous Tasks**:
- ✅ Doc Cleanup (Haiku agent, 13 commits)
- ✅ Task 1.1: Document Anti-Patterns (commit a4db0eb)
- ✅ Task 1.2: Value Parsing (commit aaf79ec, 76 tests)
- ✅ Task 1.3: Package Matching (commit 7fab2d2)
- ✅ Task 1.3b: Package Matching Tests (commit ceaf62a, 20 tests)
- ✅ Task 1.4: Component Classification (pending commit)
- ✅ Task 1.4b: Component Classification Tests (pending commit)
- ✅ Task 1.5: Matcher Service Interface (commit 40b7106)

## Current Branch
`feature/phase-1-extract-matcher`

## Context
Phase 1: Extract sophisticated matcher utilities.
Utilities extraction in progress:
- ✅ Task 1.2: value_parsing (complete)
- ✅ Task 1.3: package_matching (complete)
- ✅ Task 1.3b: package_matching tests (complete)
- ✅ Task 1.4: component_classification (complete)
- ✅ Task 1.5: matcher service interface (complete)
- → Task 1.5b: primary filtering (current)

## Target
**File**: `src/jbom/services/sophisticated_inventory_matcher.py`

## What to Do
Implement primary filtering from legacy matcher `_passes_primary_filters`:
- Type/category matching
- Package matching
- Value normalization and numeric comparisons for RES/CAP/IND
- Add unit tests for filtering behavior

## Success Criteria
- [ ] Filtering logic ported accurately
- [ ] Tests demonstrate filtering behavior
- [ ] No "enhancements" added

## Estimated Time
60-90 minutes

## Notes
Keep scope tight: port behavior, not structure. No file I/O; accept domain objects.
