# What to Do Next

## Status (as of 2026-02-25)
Phase 1 is complete and merged to `main` (PR #57; Issue #48 closed).

Phase 1 delivered the sophisticated inventory matcher extraction into jbom-new's clean architecture, including:
- 122 passing tests (112 unit + 10 integration)
- extracted utility modules in `src/jbom/common/`
- ADR 0001 documenting the Phase 2 fabricator-selection design

## Phase 2 Kickoff: Fabricator-aware inventory selection
Phase 2 begins with implementing the selection layer described in ADR 0001, without conflating the two priority concepts:
- `item.priority`: user stock-management ordering (Phase 1 behavior)
- `preference_tier`: fabricator preference ordering (Phase 2 behavior)

Primary reference for Phase 2 planning:
- `docs/workflow/planning/PHASE_2_REMAINING_WORK.md`

Expected Phase 2 ordering invariant:
- `(preference_tier, item.priority, -score)`

## Phase 1 design note (keep)
Our tests and discussion clarified an important design nuance:
- The exact numeric scoring is not inherently valuable; it is a mechanism to achieve good ranking and to eliminate unsuitable matches.
- Longer term, we may want to evolve matching heuristics toward expressing intent more directly (e.g., "correct type/value/package always beats anything else", and priority is applied as a first-class ordering constraint), instead of relying on opaque point totals.
- If we do replace the scoring mechanism in the future, preserve the behavioral contracts: filtering correctness + ordering invariants.

## SEE ALSO
- `docs/architecture/adr/0001-fabricator-inventory-selection-vs-matcher.md`
- `docs/architecture/anti-patterns.md`
- `docs/workflow/planning/PHASE_2_REMAINING_WORK.md`
