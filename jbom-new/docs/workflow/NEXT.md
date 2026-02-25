# What to Do Next

## Current Task
**Task 1.5: Design Matcher Service Interface** (Ready to start)

**Previous Tasks**:
- ✅ Doc Cleanup (Haiku agent, 13 commits)
- ✅ Task 1.1: Document Anti-Patterns (commit a4db0eb)
- ✅ Task 1.2: Value Parsing (commit aaf79ec, 76 tests)
- ✅ Task 1.3: Package Matching (commit 7fab2d2)
- ✅ Task 1.3b: Package Matching Tests (commit ceaf62a, 20 tests)
- ✅ Task 1.4: Component Classification (pending commit)
- ✅ Task 1.4b: Component Classification Tests (pending commit)

## Current Branch
`feature/phase-1-extract-matcher`

## Context
Phase 1: Extract sophisticated matcher utilities.
Utilities extraction in progress:
- ✅ Task 1.2: value_parsing (complete)
- ✅ Task 1.3: package_matching (complete)
- ✅ Task 1.3b: package_matching tests (complete)
- ✅ Task 1.4: component_classification (complete)
- → Task 1.5: matcher service interface (current)

## Target
**File**: `src/jbom/services/sophisticated_inventory_matcher.py`

## What to Do
Design a clean service interface (no implementation yet):
- MatchingOptions dataclass
- SophisticatedInventoryMatcher class skeleton
- Method signatures + return dataclasses for results

## Success Criteria
- [ ] Clear constructor: `__init__(self, options: MatchingOptions)`
- [ ] Main method accepts domain objects (not file paths)
- [ ] Return type is structured (dataclass), not tuples/dicts
- [ ] No file I/O in the service interface

## Estimated Time
45-60 minutes

## Notes
This is a Phase 1 checkpoint: the interface will drive all later matcher ports. Keep it simple and faithful to legacy behavior (no new features).
