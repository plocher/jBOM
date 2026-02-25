# What to Do Next

## Current Task
**Task 1.3: Extract Package Matching Utilities** (Ready to start)

**Previous Tasks**:
- ✅ Doc Cleanup (Haiku agent, 13 commits)
- ✅ Task 1.1: Document Anti-Patterns (commit a4db0eb)
- ✅ Task 1.2: Value Parsing (commit aaf79ec, 76 tests passing)
- ✅ Task 1.2: Extract Value Parsing Utilities (value_parsing.py created)
- ✅ Task 1.2b: Unit Test Value Parsing (tests added)

## Current Branch
`feature/phase-1-extract-matcher`

## Context
Phase 1: Extract sophisticated matcher utilities.
Anti-patterns documented ✅ (see docs/architecture/anti-patterns.md).

Now extracting shared utilities before the main matcher service:
- ✅ Task 1.2: value_parsing (resistors, capacitors, inductors)
- ✅ Task 1.2b: unit tests for value_parsing
- Task 1.3: package_matching (footprint → package extraction)
- Task 1.4: component_classification (type detection)

## Files to Extract From
**Source**: `src/jbom/common/packages.py`
**Target**: `jbom-new/src/jbom/common/package_matching.py`

## What to Extract
Package parsing/extraction utilities:
- Constants: PackageType, SMD_PACKAGES (or equivalent)
- Functions for extracting package from footprint strings (e.g. "R_0603_1608Metric" → "0603")

## Success Criteria
- [ ] File: `jbom-new/src/jbom/common/package_matching.py` created
- [ ] All functions have type hints
- [ ] All public functions have docstrings (with examples)
- [ ] Functions are pure (no side effects, no I/O)
- [ ] File imports successfully from jbom-new

## Estimated Time
45 minutes

## Notes
Keep this a faithful port; avoid adding new package heuristics in Phase 1.
