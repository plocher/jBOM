# What to Do Next

## Current Task
**Task 1.2: Extract Value Parsing Utilities** (Ready to start)

**Previous Tasks**:
- ✅ Doc Cleanup (Haiku agent, 13 commits)
- ✅ Task 1.1: Document Anti-Patterns (anti-patterns.md created)

## Current Branch
`feature/phase-1-extract-matcher`

## Context
Phase 1: Extract sophisticated matcher utilities.
Anti-patterns documented ✅ (see docs/architecture/anti-patterns.md).

Now extracting shared utilities before the main matcher service:
- Task 1.2: value_parsing (resistors, capacitors, inductors)
- Task 1.3: package_matching (footprint → package extraction)
- Task 1.4: component_classification (type detection)

## Files to Extract From
**Source**: `src/jbom/common/values.py`
**Target**: `jbom-new/src/jbom/common/value_parsing.py`

## What to Extract
Value parsing functions with EIA standard support:
- `parse_res_to_ohms()` - "10K", "2M2", "0R22" → ohms
- `parse_cap_to_farad()` - "100nF", "1u0", "220pF" → farads
- `parse_ind_to_henry()` - "10uH", "2m2" → henrys
- `ohms_to_eia()`, `farad_to_eia()`, `henry_to_eia()` - EIA converters
- Unit multiplier functions (cap_unit_multiplier, ind_unit_multiplier)

## Success Criteria
- [ ] File: `jbom-new/src/jbom/common/value_parsing.py` created
- [ ] All functions have type hints
- [ ] All functions have docstrings (with examples)
- [ ] Functions are pure (no side effects, no I/O)
- [ ] File imports successfully: `from jbom.common.value_parsing import parse_res_to_ohms`

## Anti-Pattern Reminders
From anti-patterns.md:
- ❌ AP-1: No file I/O in domain functions
- ❌ AP-2: No debug strings in domain logic
- ✅ AP-4: Pure functions in domain model layer

## Estimated Time
45-60 minutes (port + type hints + docstrings)

## Notes
Straightforward porting task. Functions already mostly pure.
Can delegate to Haiku if cost efficiency desired.
