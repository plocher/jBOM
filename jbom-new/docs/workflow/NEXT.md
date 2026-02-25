# What to Do Next

## Current Task
**Task 1.4: Extract Component Classification** (Ready to start)

**Previous Tasks**:
- ✅ Doc Cleanup (Haiku agent, 13 commits)
- ✅ Task 1.1: Document Anti-Patterns (commit a4db0eb)
- ✅ Task 1.2: Value Parsing (commit aaf79ec, 76 tests)
- ✅ Task 1.3: Package Matching (commit 7fab2d2)
- ✅ Task 1.3b: Package Matching Tests (commit ceaf62a, 20 tests)

## Current Branch
`feature/phase-1-extract-matcher`

## Context
Phase 1: Extract sophisticated matcher utilities.
Utilities extraction in progress:
- ✅ Task 1.2: value_parsing (complete)
- ✅ Task 1.3: package_matching (complete)
- ✅ Task 1.3b: package_matching tests (complete)
- → Task 1.4: component_classification (current)

## Files to Extract
**Target**: `src/jbom/common/component_classification.py`
**Source**: `src/jbom/processors/component_types.py`

## What to Extract
Component classification functions:
- get_component_type(): Classify components based on lib_id (e.g., "Device:R" → "RES")
- get_category_fields(): Get relevant fields for component categories
- ComponentType constants: Standard component type identifiers

## Success Criteria
- [ ] File: `src/jbom/common/component_classification.py` created
- [ ] Functions: get_component_type(), get_category_fields()
- [ ] ComponentType constants ported
- [ ] Import works: `from jbom.common.component_classification import get_component_type`

## Estimated Time
45 minutes

## Notes
Port component classification utilities from legacy jbom to support sophisticated matcher extraction.
