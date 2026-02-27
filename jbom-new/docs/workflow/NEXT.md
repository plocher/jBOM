# Phase 7 Cutover — Mechanical Tasks Handoff

## Purpose
This file is a step-by-step task list for a sub-agent executing the mechanical portions of the
Phase 7 legacy-to-new cutover. The full plan is at
`jbom-new/docs/workflow/planning/PHASE_7_PLAN.md`.

**You are executing the mechanical portions only.** Documentation authorship (README.md,
CHANGELOG.md, NEXT.md), legacy docs auditing, test failure remediation, and real-project
validation are reserved for a higher-capability agent to complete after your PR is reviewed.

## STOP Conditions — Read First
If any of the following occur, **stop immediately**, leave the branch as-is, push it, and open
the PR with `[BLOCKED]` in the title explaining exactly what happened:
- Any `pytest` or `behave` run has failures after a file-move step
- Any `jbom` command produces an error or unexpected output
- A `git mv` fails due to an unexpected conflict
- You are unsure how to resolve a situation — **do not guess**

## CRITICAL: Do Not Restore or Clean
Do **not** run `git restore`, `git clean`, or `git reset` at any point. The planning files
in this repo are intentionally untracked during development. Running `git clean` will
permanently destroy them.

## Working Directory
All shell commands use the **repo root** as `pwd`:
```
/Users/jplocher/Dropbox/KiCad/jBOM/
```
`jbom-new/` is a subdirectory of the repo root, not a separate repo.

## Co-author Line
Every commit message must end with:
```
Co-Authored-By: Oz <oz-agent@warp.dev>
```

---

## Step 0: Pre-flight Verification

Confirm the starting state before touching anything. Use `git status` only to read
— **do not use it to drive any cleanup commands**:

```bash
cd /Users/jplocher/Dropbox/KiCad/jBOM
git status
git branch                          # must be on main
PYTHONPATH=jbom-new/src python -m pytest jbom-new/tests/ -q --tb=short 2>&1 | tail -5
python -m behave --format progress jbom-new/features/ 2>&1 | tail -5
```

Both test runs must show 0 failures. If not, stop — do not proceed.
If `git status` shows untracked files, **ignore them** — do not clean them up.

---

## Step 1: Create GitHub Issue, Pre-Cutover Tag, and Feature Branch

### 1a. Create a GitHub issue for the cutover
```bash
gh issue create \
  --title "Phase 7: Legacy-to-new cutover (promote jbom-new to root, version 7.0.0)" \
  --body "Mechanical cutover tasks per jbom-new/docs/workflow/planning/PHASE_7_PLAN.md.

Archive legacy code, promote jbom-new/ to repo root, update pyproject.toml and CI for 7.0.0." \
  --label enhancement
```
Note the issue number printed (referred to as N below).

### 1b. Create the pre-cutover annotated tag on main
```bash
git tag -a v6.8.0-final-legacy -m "Last release with legacy jBOM implementation"
git push origin v6.8.0-final-legacy
```

### 1c. Create the feature branch
```bash
git checkout -b feature/issue-N-phase-7-cutover
```
(Replace N with the actual issue number from 1a.)

---

## Step 2: Archive Legacy Code

Move legacy code out of the way before promoting new code.

```bash
mkdir -p legacy/src
git mv src/jbom legacy/src/jbom

mkdir -p legacy
git mv tests legacy/tests
git mv features legacy/features
```

Commit:
```bash
git add -A
pre-commit run --files $(git diff --cached --name-only | tr '\n' ' ') 2>/dev/null; git add -A
git commit -m "refactor: archive legacy src, tests, and features to legacy/

Preserves legacy jBOM 6.8.0 implementation for reference during Phase 7 cutover.
Git history retains full change history; legacy/ provides direct file access.
Closes no issues — preparatory step for Phase 7.

Co-Authored-By: Oz <oz-agent@warp.dev>"
```

---

## Step 3: Promote jbom-new Source, Tests, and Features

```bash
git mv jbom-new/src/jbom src/jbom
git mv jbom-new/tests tests
git mv jbom-new/features features
```

### Checkpoint A — verify imports work before continuing
```bash
PYTHONPATH=src python -c "import jbom; print(jbom.__version__)"
```
Expected output: `5.0.0-alpha.1` (the jbom-new dev version — will be updated in Step 6).
If this fails with an ImportError, **stop** per the STOP Conditions above.

```bash
PYTHONPATH=src python -m pytest tests/ -q --tb=short 2>&1 | tail -10
```
All tests must pass. If not, stop.

Commit:
```bash
git add -A
pre-commit run --files $(git diff --cached --name-only | tr '\n' ' ') 2>/dev/null; git add -A
git commit -m "feat: promote jbom-new src, tests, and features to repo root

Moves the Phase 1-6 implementation from jbom-new/ to the standard repo layout:
- src/jbom/  (new implementation)
- tests/     (254 pytest tests)
- features/  (194 BDD scenarios)

Co-Authored-By: Oz <oz-agent@warp.dev>"
```

---

## Step 4: Promote jbom-new Docs

Move non-conflicting subdirectories from `jbom-new/docs/` into `docs/`:

```bash
git mv jbom-new/docs/architecture  docs/architecture
git mv jbom-new/docs/workflow      docs/workflow
git mv jbom-new/docs/guides        docs/guides
git mv jbom-new/docs/examples      docs/examples
git mv jbom-new/docs/tutorial      docs/tutorial
git mv jbom-new/docs/README.md     docs/README.md
```

`jbom-new/docs/design/` is empty — remove it:
```bash
rmdir jbom-new/docs/design 2>/dev/null || true
```

Move requirements:
```bash
mkdir -p docs
git mv jbom-new/requirements docs/requirements
```

Commit:
```bash
git add -A
pre-commit run --files $(git diff --cached --name-only | tr '\n' ' ') 2>/dev/null; git add -A
git commit -m "docs: promote jbom-new docs to repo root docs/

Moves architecture, workflow, guides, examples, tutorial, and requirements
from jbom-new/ to the repo root docs/ directory.
Legacy docs/ content (configuration guides, design notes, man pages) is
preserved in place for audit by a higher-capability agent.

Co-Authored-By: Oz <oz-agent@warp.dev>"
```

---

## Step 5: Clean Up jbom-new/

Remove the remaining jbom-new/ skeleton files — config is now in pyproject.toml,
and the changelogs/READMEs are superseded:

```bash
git rm jbom-new/behave.ini
git rm jbom-new/pytest.ini
git rm jbom-new/CHANGELOG.md
git rm jbom-new/README.md
git rm -f jbom-new/WARP-Context    2>/dev/null || true
git rm -f jbom-new/WARP-Issue.prompt 2>/dev/null || true
rm -rf jbom-new/scripts/__pycache__ 2>/dev/null || true
```

If `jbom-new/` is now empty, remove it:
```bash
rmdir jbom-new/docs 2>/dev/null || true
rmdir jbom-new/scripts 2>/dev/null || true
rmdir jbom-new 2>/dev/null || true
```

If `rmdir` fails because files remain, list what's left with `find jbom-new -type f` and
include that list in the PR description — **do not delete unknown files**.

Commit:
```bash
git add -A
pre-commit run --files $(git diff --cached --name-only | tr '\n' ' ') 2>/dev/null; git add -A
git commit -m "chore: remove jbom-new/ skeleton after promotion to root

All content has been moved to standard repo locations.
Dev artifacts (behave.ini, pytest.ini, CHANGELOG.md, README.md) removed;
config lives in pyproject.toml, changelogs in root CHANGELOG.md.

Co-Authored-By: Oz <oz-agent@warp.dev>"
```

---

## Step 6: Update pyproject.toml

Apply the following changes to `/Users/jplocher/Dropbox/KiCad/jBOM/pyproject.toml`:

**6a. Version and Python requirement**
- Change `version = "6.8.0"` → `version = "7.0.0"`
- Change `requires-python = ">=3.9"` → `requires-python = ">=3.10"`
- Remove `"Programming Language :: Python :: 3.9",` from classifiers

**6b. Package data — add missing yaml glob patterns**
Change the `[tool.setuptools.package-data]` section from:
```toml
jbom = [
    "config/*.yaml",
    "config/fabricators/*.yaml",
]
```
To:
```toml
jbom = [
    "config/*.yaml",
    "config/fabricators/*.yaml",
    "config/presets/*.yaml",
    "config/suppliers/*.yaml",
]
```

**6c. Semantic release version_variables**
Change:
```toml
version_variables = ["src/jbom/__version__.py:__version__"]
```
To:
```toml
version_variables = ["src/jbom/__init__.py:__version__"]
```

**6d. Pytest configuration**
Change the `[tool.pytest.ini_options]` section:
```toml
testpaths = [
    "tests",
]
pythonpath = ["src"]
```
(Remove the `jbom-new/` prefixed paths entirely.)

**6e. Behave configuration**
Change the `[tool.behave]` paths to:
```toml
paths = [
    "features",
]
```
(Remove the `jbom-new/` prefixed paths entirely.)

Commit:
```bash
git add pyproject.toml
pre-commit run --files pyproject.toml 2>/dev/null; git add pyproject.toml
git commit -m "feat: update pyproject.toml for 7.0.0 cutover

- Bump version to 7.0.0
- Require Python >=3.10 (union type syntax)
- Add config/presets and config/suppliers to package-data
- Update pytest testpaths and pythonpath to repo root layout
- Update behave paths to repo root layout
- Fix semantic_release version_variables to __init__.py

Co-Authored-By: Oz <oz-agent@warp.dev>"
```

---

## Step 7: Update Version File

Edit `src/jbom/__init__.py` — change the version line:
```python
__version__ = "7.0.0"
```
(The file currently has `"5.0.0-alpha.1"`.)

Check if `src/jbom/__version__.py` exists. If it does, confirm it is **not** imported anywhere
in `src/jbom/` (grep to verify), then remove it:
```bash
grep -r "__version__" src/jbom/ --include="*.py" -l
```
If only `__init__.py` and `__version__.py` itself appear, delete it:
```bash
git rm src/jbom/__version__.py
```

Commit:
```bash
git add src/jbom/__init__.py
git rm src/jbom/__version__.py 2>/dev/null || true
git add -A
pre-commit run --files src/jbom/__init__.py 2>/dev/null; git add -A
git commit -m "feat: set version to 7.0.0, remove legacy __version__.py

New implementation uses __init__.py for version string.
Legacy __version__.py (which set 6.8.0) is no longer imported.

Co-Authored-By: Oz <oz-agent@warp.dev>"
```

---

## Step 8: Update CI — test.yml

Edit `/Users/jplocher/Dropbox/KiCad/jBOM/.github/workflows/test.yml`.

**8a. Python matrix** — remove `"3.9"`, keep `"3.10"`, `"3.11"`, `"3.12"`:
```yaml
        python-version: ["3.10", "3.11", "3.12"]
```

**8b. Install step** — change to install all extras:
```yaml
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e .[all]
        pip install behave
```

**8c. Run tests step** — replace unittest with pytest + behave:
```yaml
    - name: Run tests
      run: |
        PYTHONPATH=src python -m pytest tests/ -v
        PYTHONPATH=src python -m behave --format progress features/
```

**8d. Coverage step** — update to use 3.10 (3.9 is dropped) and pytest:
```yaml
    - name: Test coverage
      if: matrix.python-version == '3.10'
      run: |
        pip install coverage pytest-cov
        PYTHONPATH=src coverage run -m pytest tests/
        coverage report -m
```

Commit:
```bash
git add .github/workflows/test.yml
pre-commit run --files .github/workflows/test.yml 2>/dev/null; git add .github/workflows/test.yml
git commit -m "ci: update test.yml for pytest + behave, drop Python 3.9

- Replace unittest discover with pytest + behave
- Add pip install behave to install step
- Drop Python 3.9 from matrix (union type syntax requires 3.10+)
- Update coverage step to use pytest-cov on 3.10

Co-Authored-By: Oz <oz-agent@warp.dev>"
```

---

## Step 9: Final Local Validation

Run all verification commands from the repo root. Each must succeed before proceeding.

```bash
cd /Users/jplocher/Dropbox/KiCad/jBOM

# Install package in editable mode
pip install -e .[all]

# Version check
jbom --version
# Expected: 7.0.0

# Help — verify all 6 commands appear
jbom --help
# Expected: bom, pos, parts, inventory, search, inventory-search all listed

# Pytest
PYTHONPATH=src python -m pytest tests/ -v 2>&1 | tail -20
# Expected: all pass, 0 failures

# Behave
PYTHONPATH=src python -m behave features/ --format progress 2>&1 | tail -20
# Expected: all scenarios pass, 0 failing
```

If any step fails, **stop** per the STOP Conditions, push the branch as-is, and open the PR
with `[BLOCKED]` in the title including the exact failure output.

---

## Step 10: Push Branch and Open PR

```bash
git push -u origin feature/issue-N-phase-7-cutover
```

Open the PR:
```bash
gh pr create \
  --title "feat: Phase 7 cutover — promote jbom-new to root (v7.0.0)" \
  --body "## Summary
Mechanical cutover of jBOM from legacy jbom-new/ layout to standard repo root layout.
Sets version 7.0.0 and updates CI for pytest + behave.

## Changes
- Legacy code archived to legacy/ (git history preserved)
- New implementation promoted: src/jbom/, tests/, features/
- jbom-new/ docs promoted to docs/architecture, docs/workflow, etc.
- pyproject.toml updated: version 7.0.0, Python >=3.10, package-data, test paths
- src/jbom/__init__.py: __version__ = 7.0.0
- .github/workflows/test.yml: pytest + behave, Python 3.10-3.12
- jbom-new/ skeleton removed

## Validation
- jbom --version: 7.0.0
- pytest tests/: all pass
- behave features/: all scenarios pass

## Not included (reserved for higher-capability agent)
- README.md rewrite
- CHANGELOG.md 7.0.0 entry
- Legacy docs/ audit
- NEXT.md post-cutover update
- Real-project BOM validation

Closes #N" \
  --base main
```
(Replace N with the issue number from Step 1a.)

---

## Definition of Done

This handoff is complete when:
1. PR is open on GitHub targeting `main`
2. `jbom --version` outputs `7.0.0` locally
3. `pytest tests/ -v` passes with 0 failures
4. `python -m behave features/ --format progress` passes with 0 failing scenarios
5. All commits follow semantic commit format with co-author line
6. PR description lists what was and was not completed
