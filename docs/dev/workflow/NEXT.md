# Current Development State

## Status: Post-Phase-7, v7.x active

Phase 7 cutover is complete. The codebase was promoted from `jbom-new/` to the repo root
in February 2026. The legacy implementation is archived in `legacy/` (retained for git
history; its source, tests, and features are superseded by the current implementation).

## Current version
See `src/jbom/__init__.py` for the active version string and `docs/CHANGELOG.md` for recent changes.

## Recently completed
- **#102** Query Intelligence Architecture — parametric search, Phase 4 heuristics
- **#117** Catalog-Driven Supplier Assignment — `NullSearchProvider`, `generic` supplier,
  `STALE_PART`/`BETTER_AVAILABLE` freshness checks, `jbom inventory --supplier`
- **#154** `jbom annotate` and `jbom audit --supplier` commands
- **#161** Non-code artifact cleanup — man pages, tutorials, legacy/poc removal

## What to work on next
See open GitHub issues for the current backlog:
```bash
gh issue list --state open
```

## Active omnibus coordination: #195
- Parent umbrella: `#195 meta(search): omnibus backlog for supplier parity, DRY refactor, and category expansion`
- Grouped execution slices:
  - `#199` Slice 1 — parity matrix + diagnostics baseline
  - `#200` Slice 2 — unified relevance contract + category weighting expansion
  - `#201` Slice 3 — shared normalization utilities + provider DRY pass
- Sequencing: `#199 -> #200 -> #201`
- Supervisor/delegate prompts and handoff contract are tracked in:
  - `docs/dev/workflow/WORK_LOG.md` (session entry 2026-03-17)
  - `https://github.com/plocher/jBOM/issues/195#issuecomment-4078650362`

## Development workflow
See `GIT_WORKFLOW.md` and `HUMAN_WORKFLOW.md` in this directory.
