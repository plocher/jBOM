# Phase 7: Legacy-to-New Cutover Plan

## Goal
Replace legacy `src/jbom/` with jbom-new code so that `pip install jbom` and `jbom` CLI use the new implementation. After cutover, the `jbom-new/` subdirectory is eliminated — everything lives at the repo root.

## Current Layout
```
jBOM/
├── src/jbom/           ← legacy code (published to PyPI as jbom 6.8.0)
├── jbom-new/src/jbom/  ← new code (runs via PYTHONPATH during dev)
├── tests/              ← legacy unittest tests
├── jbom-new/tests/     ← new pytest tests (254 passing)
├── features/           ← legacy behave features
├── jbom-new/features/  ← new behave features (194 scenarios)
├── pyproject.toml      ← entry point: jbom = "jbom.cli.main:main"
│                         package-dir: src/
│                         version: 6.8.0
├── kicad_jbom_plugin.py ← thin wrapper, shells out to `jbom bom`
└── .github/workflows/  ← CI: test.yml (unittest), semantic-release.yml
```

## Target Layout
```
jBOM/
├── src/jbom/           ← new code (moved from jbom-new/src/jbom/)
├── tests/              ← new tests (moved from jbom-new/tests/)
├── features/           ← new features (moved from jbom-new/features/)
├── docs/               ← merged docs
├── pyproject.toml      ← updated entry point, deps, test config
│                         version: 7.0.0
├── kicad_jbom_plugin.py ← unchanged (still calls `jbom bom`)
├── legacy/             ← archived legacy src/ + tests/ + features/
└── .github/workflows/  ← updated CI: pytest + behave
```

## Pre-Cutover Checklist
* Confirm all jbom-new tests pass (254 pytest + 194 BDD) ✅
* Confirm PR #70 merged (Phase 6 search harvest) ✅
* Issues #68, #69 are non-blocking tech debt
* No open feature branches with uncommitted work

## Step 1: Archive Legacy Code
Move legacy code to `legacy/` for reference (git history preserves everything, but having it available during transition is helpful):
* `src/jbom/` → `legacy/src/jbom/`
* `tests/` → `legacy/tests/`
* `features/` → `legacy/features/`
* Keep `legacy/` as read-only reference; delete it in a follow-up once confident

## Step 2: Promote jbom-new to Root
Move new code to the standard locations:
* `jbom-new/src/jbom/` → `src/jbom/`
* `jbom-new/tests/` → `tests/`
* `jbom-new/features/` → `features/`
* `jbom-new/docs/` → merge into `docs/`
* Remove `jbom-new/` directory (behave.ini, pytest.ini, README.md, etc. get absorbed into root)

## Step 3: Update pyproject.toml
Key changes:
* `version`: bump to `7.0.0` (breaking: entirely new implementation)
* `[project.scripts]`: `jbom = "jbom.cli.main:main"` — same entry point, same module path (no change needed since package name is `jbom` in both)
* `requires-python`: update to `>=3.10` (jbom-new uses `X | Y` union types)
* `[tool.setuptools]`: `package-dir = {"" = "src"}` — unchanged
* `[tool.setuptools.package-data]`: ensure `config/*.yaml`, `config/fabricators/*.yaml`, `config/presets/*.yaml`, `config/suppliers/*.yaml` are included
* `[tool.pytest.ini_options]`: update `testpaths` to `["tests"]`, `pythonpath` to `["src"]`
* `[tool.behave]`: update `paths` to `["features"]`
* `[project.optional-dependencies]`: verify `search = ["requests>=2.28.0"]` stays

## Step 4: Update Version Files
* `src/jbom/__init__.py`: set `__version__ = "7.0.0"`
* Remove `src/jbom/__version__.py` if no longer imported (jbom-new uses `__init__.py` for version)
* Update `[tool.semantic_release]` version_variables to point to `src/jbom/__init__.py:__version__`

## Step 5: Update CI Workflows
### test.yml
* Replace `python -m unittest discover -s tests -v` with:
    * `PYTHONPATH=src python -m pytest tests/ -v`
    * `PYTHONPATH=src python -m behave --format progress features/`
* Add `pip install -e .[all]` (includes requests for search tests)
* Update Python matrix: drop 3.9, keep 3.10–3.12 (union type syntax requirement)

### semantic-release.yml
* Update `version_variables` path if changed
* No other changes needed (it reads `pyproject.toml`)

## Step 6: Update KiCad Plugin
The plugin calls `jbom bom` via subprocess — the CLI interface is the same, so **no changes needed**. Verify it still works after cutover.

## Step 7: Update Documentation
Documentation is the largest non-mechanical part of this cutover. The legacy docs have useful structural patterns and content that shouldn't be lost.

### 7a: Merge docs directories
* Move `jbom-new/docs/architecture/` → `docs/architecture/` (replace stale legacy architecture docs)
* Move `jbom-new/docs/workflow/` → `docs/workflow/`
* Move `jbom-new/requirements/` → `docs/requirements/` (if present)
* **Audit legacy `docs/`** before deleting — some content (API usage examples, configuration guides, design rationale) may still be relevant and should be preserved or adapted

### 7b: Root-level docs
* Update root `README.md` — new installation, CLI usage for all 6 commands, inventory format, fabricator profiles
* Update `CHANGELOG.md` with 7.0.0 release notes
* Update `NEXT.md` to reflect post-cutover status and future work

### 7c: Known documentation gaps (future work, not blockers)
* **KiCad plugin**: `kicad_jbom_plugin.py` works but is undocumented beyond its own docstring. Needs a user-facing setup guide.
* **Python API**: jbom-new has no public API surface beyond CLI. Legacy had `jbom.api` module. Documenting a programmatic API is future work.
* **Search command usage**: Examples, API key setup guide, rate limit guidance
* **Fabricator profile authoring**: How to create custom `.fab.yaml` profiles

## Step 8: Validation
* `pip install -e .[all]` from repo root
* `jbom --version` shows 7.0.0
* `jbom --help` shows all 6 commands (bom, pos, parts, inventory, search, inventory-search)
* `pytest tests/ -v` — all pass
* `python -m behave features/ --format progress` — all pass
* Run BOM validation against real projects (same 11 projects from Phase 5)
* `jbom bom -f reference,footprint,quantity,value -o - ~/Dropbox/KiCad/projects/Core-wt32-eth0/` produces correct output
* KiCad plugin still works

## Risk Mitigation
* **PyPI users**: 7.0.0 is a major version bump — `pip install jbom` will not auto-upgrade from 6.x
* **Rollback**: Legacy code preserved in `legacy/` and git history
* **Breaking changes**: Python 3.9 dropped (3.10+ required). CLI interface is backward-compatible for `bom`, `pos` commands. `search` and `inventory-search` are new.
* **annotate command**: Not ported. Users of legacy `jbom annotate` should stay on 6.x until Phase 8.

## Decisions
1. **legacy/ directory**: Delete after one release cycle. Create annotated git tags at milestones (e.g., `v6.8.0-final-legacy`, `v7.0.0`) to make it easy to find legacy code in history.
2. **annotate command**: No stub needed — it was never used in the wild.
3. **PyPI**: No concerns — package name is owned.

## Pre-Cutover Tag
Before starting, create an annotated tag on the current main:
```bash
git tag -a v6.8.0-final-legacy -m "Last release with legacy jBOM implementation"
git push origin v6.8.0-final-legacy
```
