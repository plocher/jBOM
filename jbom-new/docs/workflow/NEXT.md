# What to Do Next

## Current Task
**Task 1.6: Integration Tests for Matcher** (Ready to start)

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
- ✅ Task 1.5c: Scoring + Ordering (commits ca5bb30, 099ead2)

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
- ✅ Task 1.5c: scoring + ordering (complete)
- → Task 1.6: integration tests (current)

## Target
**File**: `src/jbom/services/sophisticated_inventory_matcher.py`

## What to Do
Create integration tests validating the Phase 1 sophisticated matcher behavior:
- Use representative components + inventory items
- Confirm primary filtering + scoring results are equivalent to legacy for key cases
- Confirm ordering is exactly: (item.priority asc, score desc)

## Success Criteria
- [ ] Real components match correctly
- [ ] Results equivalent to old-jbom
- [ ] Integration tests pass

## Estimated Time
60-90 minutes

## Notes
This is the first end-to-end verification of the Phase 1 matcher port. Keep it focused on equivalence.
