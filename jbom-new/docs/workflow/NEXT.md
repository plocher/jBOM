# What to Do Next

## Current Task
**Task 1.5c: Implement Scoring Algorithm** (Ready to start)

**Previous Tasks**:
- ✅ Doc Cleanup (Haiku agent, 13 commits)
- ✅ Task 1.1: Document Anti-Patterns (commit a4db0eb)
- ✅ Task 1.2: Value Parsing (commit aaf79ec, 76 tests)
- ✅ Task 1.3: Package Matching (commit 7fab2d2)
- ✅ Task 1.3b: Package Matching Tests (commit ceaf62a, 20 tests)
- ✅ Task 1.4: Component Classification (pending commit)
- ✅ Task 1.4b: Component Classification Tests (pending commit)
- ✅ Task 1.5: Matcher Service Interface (commit 40b7106)
- ✅ Task 1.5b: Primary Filtering (commits 3a63bad, 66bed7a)

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
- ✅ Task 1.5b: primary filtering (complete)
- → Task 1.5c: scoring + ordering (current)

## Target
**File**: `src/jbom/services/sophisticated_inventory_matcher.py`

## What to Do
Implement scoring + ordering from legacy matcher `_calculate_match_score`:
- Type match weight (50)
- Value match weight (40)
- Footprint/package match weight (30)
- Property matching (tolerance/voltage/wattage)
- Final ordering: priority ascending, then score descending
- Add unit tests for scoring weights + ordering

## Success Criteria
- [ ] Scoring produces same outcomes as legacy matcher for representative cases
- [ ] Ordering matches legacy: (priority asc, score desc)
- [ ] Tests demonstrate scoring weights + ordering behavior
- [ ] No "enhancements" added

## Estimated Time
60-90 minutes

## Notes
Keep scope tight: port behavior, not structure. No file I/O; accept domain objects.
