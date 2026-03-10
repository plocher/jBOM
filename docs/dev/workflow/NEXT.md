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

## Development workflow
See `GIT_WORKFLOW.md` and `HUMAN_WORKFLOW.md` in this directory.
