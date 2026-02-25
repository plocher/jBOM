# Phase 1: Extract Sophisticated Matcher - Task Breakdown

## Overview
Extract old-jbom's proven matching algorithms and integrate into jbom-new's clean architecture.

Total Estimated Time: 2-4 weeks (with paired approach and learning)

---

## Task 1.1: Document Anti-Patterns ⏱️ 30 min
**Status**: ✅ Complete

**What You Do**:
1. Read through this task card
2. Tell agent: "Let's work on Task 1.1 - document anti-patterns from old-jbom"
3. Review the document agent creates
4. Ask questions or request changes
5. When satisfied, commit and update docs/workflow/NEXT.md

**What Agent Does**:
- Reads old-jbom code (inventory_matcher.py, bom.py)
- Creates `anti-patterns.md` with specific examples
- Shows WHY each pattern is bad
- Connects to jbom-new patterns that fix it

**Success Criteria**:
- [ ] File created: `docs/architecture/anti-patterns.md`
- [ ] Contains 3-5 concrete examples from old-jbom
- [ ] Each example has: code snippet, explanation, better alternative
- [ ] You understand the anti-patterns identified

**Output**: Documentation artifact

---

## Task 1.2: Extract Value Parsing Utilities ⏱️ 45-60 min
**Status**: ✅ Complete
**Depends on**: Task 1.1

**What You Do**:
1. Tell agent: "Let's work on Task 1.2 - extract value_parsing.py"
2. Watch as agent ports code
3. Check: Does it follow jbom-new patterns? Any unnecessary complexity?
4. Review: Type hints clear? Functions pure (no side effects)?
5. Commit when approved

**What Agent Does**:
- Copy `src/jbom/common/values.py` → `jbom-new/src/jbom/common/value_parsing.py`
- Add type hints throughout
- Add docstrings in jbom-new style
- Ensure functions are pure (no I/O, no globals)
- Make imports work in jbom-new context

**Success Criteria**:
- [ ] File: `jbom-new/src/jbom/common/value_parsing.py`
- [ ] Functions: parse_res_to_ohms, parse_cap_to_farad, parse_ind_to_henry, EIA converters
- [ ] All functions have type hints and docstrings
- [ ] File imports successfully: `from jbom.common.value_parsing import parse_res_to_ohms`

**Your Review Checklist**:
- [ ] No file I/O or globals introduced
- [ ] Type hints are accurate (not just `Any`)
- [ ] Docstrings explain what function does with examples
- [ ] No unnecessary "improvements" added

**Output**: Python module file

---

## Task 1.2b: Unit Test Value Parsing ⏱️ 30-45 min
**Status**: ✅ Complete
**Depends on**: Task 1.2

**What You Do**:
1. Tell agent: "Let's write tests for value_parsing.py"
2. Review test cases: Do they cover edge cases you care about?
3. Run tests: `cd jbom-new && pytest tests/unit/test_value_parsing.py -v`
4. If failures, work with agent to fix (might be bugs in ported code!)
5. Commit when tests pass

**What Agent Does**:
- Create `tests/unit/test_value_parsing.py`
- Test each function with typical and edge cases
- Examples: "10K" → 10000, "100nF" → 1e-7, "2M2" → 2200000
- Use pytest fixtures if helpful

**Success Criteria**:
- [ ] File: `tests/unit/test_value_parsing.py`
- [ ] Tests pass: `pytest tests/unit/test_value_parsing.py`
- [ ] Coverage ≥ 80% of value_parsing.py functions
- [ ] Edge cases tested (empty strings, malformed input, case variations)

**Your Review Checklist**:
- [ ] Tests are readable (you understand what they test)
- [ ] Test names describe what they validate
- [ ] No over-engineering (mocks, factories for simple parsing tests)

**Output**: Test file with passing tests

---

## Task 1.3: Extract Package Matching Utilities ⏱️ 45 min
**Status**: ✅ Complete (commit 7fab2d2)
**Depends on**: Task 1.2b

**What You Do**:
Same paired pattern as 1.2:
1. Tell agent the task
2. Review ported code for fidelity and simplicity
3. Check against anti-patterns doc
4. Commit when approved

**What Agent Does**:
- Port `src/jbom/common/packages.py` → `jbom-new/src/jbom/common/package_matching.py`
- Add type hints and docstrings
- Preserve PackageType constants and SMD_PACKAGES list

**Success Criteria**:
- [ ] File: `jbom-new/src/jbom/common/package_matching.py`
- [ ] Constants: PackageType, SMD_PACKAGES
- [ ] Functions for extracting package from footprint strings
- [ ] Imports work in jbom-new

**Output**: Python module file

---

## Task 1.3b: Unit Test Package Matching ⏱️ 30 min
**Status**: ✅ Complete (commit ceaf62a, 20 tests passing)
**Depends on**: Task 1.3

**What You Do**: Same review pattern

**What Agent Does**:
- Create `tests/unit/test_package_matching.py`
- Test package extraction: "R_0603_1608Metric" → "0603"
- Test various footprint formats

**Success Criteria**:
- [ ] Tests pass
- [ ] Common footprints tested (0603, 0805, SOIC-8, QFN-32, etc.)

**Output**: Test file

---

## Task 1.4: Extract Component Classification ⏱️ 45 min
**Status**: ✅ Complete (pending commit)
**Depends on**: Task 1.3b

**What You Do**: Same paired pattern

**What Agent Does**:
- Port `src/jbom/processors/component_types.py` → `jbom-new/src/jbom/common/component_classification.py`
- Functions: get_component_type, get_category_fields
- ComponentType constants

**Success Criteria**:
- [ ] File: `jbom-new/src/jbom/common/component_classification.py`
- [ ] Functions work with jbom-new's Component type

**Output**: Python module file

---

## Task 1.4b: Unit Test Component Classification ⏱️ 30 min
**Status**: ✅ Complete (pending commit)
**Depends on**: Task 1.4

**What Agent Does**:
- Test classification: lib_id "Device:R" → "RES"
- Test various component types

**Output**: Test file

---

## Task 1.5: Design Matcher Service Interface ⏱️ 45-60 min
**Status**: ✅ Complete (commit 40b7106)
**Depends on**: Tasks 1.2-1.4 complete
**⚠️ CRITICAL CHECKPOINT**: Review interface carefully

**What You Do**:
1. Tell agent: "Let's design the matcher service interface following jbom-new patterns"
2. **Carefully review** the interface design:
   - Does it follow Constructor Configuration Pattern?
   - Is it a pure domain service (no CLI, no file I/O)?
   - Does it accept domain objects, not file paths?
   - Is the return type structured (not tuples)?
3. Discuss: This is where you prevent "grandiose monstrosity"
4. Iterate on interface until you're satisfied
5. Only approve when interface is simple and clean

**What Agent Does**:
- Create `services/sophisticated_inventory_matcher.py` with:
  - MatchingOptions dataclass
  - SophisticatedInventoryMatcher class skeleton
  - Method signatures with type hints
  - Docstrings explaining purpose
  - NO implementation yet (just interface)

**Success Criteria**:
- [ ] Clear constructor: `__init__(self, options: MatchingOptions)`
- [ ] Main method: `find_matches(self, component: Component, inventory: List[InventoryItem]) -> List[MatchResult]`
- [ ] MatchResult dataclass defined
- [ ] No file I/O in signatures
- [ ] No CLI concerns (print statements, etc.)
- [ ] Follows patterns in `docs/architecture/design-patterns.md`

**Your Review Checklist** (IMPORTANT):
- [ ] Interface is SIMPLE (not adding features beyond old-jbom)
- [ ] No "while we're at it" improvements
- [ ] Matches old-jbom capability, not more
- [ ] You can explain to someone what each method does

**Output**: Service skeleton (interface only)

---

## Task 1.5b: Implement Primary Filtering ⏱️ 60-90 min
**Status**: ✅ Complete (commits 3a63bad, 66bed7a)
**Depends on**: Task 1.5

**What You Do**:
1. Tell agent: "Implement primary filtering from old-jbom"
2. Watch for scope creep - just port the filter, don't "improve" it
3. Review: Does logic match old-jbom's `_passes_primary_filters`?
4. Commit when logic is faithful to original

**What Agent Does**:
- Implement filtering logic from old-jbom lines 186-235
- Type/category matching
- Package matching
- Value normalization
- Add unit tests for filtering

**Success Criteria**:
- [ ] Filtering logic ported accurately
- [ ] Tests demonstrate filtering behavior
- [ ] No "enhancements" added

**Output**: Partial implementation + tests

---

## Task 1.5c: Implement Scoring Algorithm ⏱️ 60-90 min
**Status**: 🔴 Not started
**Depends on**: Task 1.5b

**What You Do**: Same careful review

**What Agent Does**:
- Implement `_calculate_match_score` from old-jbom lines 121-173
- Score weights: 50 type, 40 value, 30 footprint
- Property matching bonus
- Priority ranking

**Success Criteria**:
- [ ] Scoring produces same results as old-jbom
- [ ] Tests validate scoring weights
- [ ] Priority ranking works correctly

**Output**: Complete matcher implementation

---

## Task 1.6: Integration Tests for Matcher ⏱️ 60 min
**Status**: 🔴 Not started
**Depends on**: Task 1.5c

**What You Do**:
1. Provide sample components and inventory from real project
2. Review test results against old-jbom behavior
3. Approve when matching behavior is equivalent

**What Agent Does**:
- Create `tests/integration/test_matcher_integration.py`
- Use real component data
- Compare results with old-jbom matcher

**Success Criteria**:
- [ ] Real components match correctly
- [ ] Results equivalent to old-jbom
- [ ] Integration tests pass

**Output**: Integration test file

---

## Checkpoint: Phase 1 Complete

When all tasks done:
- [ ] All files committed with semantic commit messages
- [ ] Update WORK_LOG.md with summary
- [ ] Update docs/workflow/NEXT.md to point to Phase 2
- [ ] Close GitHub Issue #48
- [ ] Create feature branch PR for review

**Estimated Total**: 10-15 paired sessions over 2-4 weeks
