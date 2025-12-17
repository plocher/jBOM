# WARP.md

Project-wide guidance for AI agents working with jBOM.

## Project Overview
jBOM is a sophisticated KiCad Bill of Materials generator in Python. It matches schematic components against inventory files (CSV, Excel, Numbers) to produce fabrication-ready BOMs with supplier-neutral designs and flexible output customization.

## Core Standards

### Git & Versioning
- Always use conventional commits (`fix:`, `feat:`, `chore:`, etc.)
- Semantic versioning is automated - commit messages trigger version bumps
- Use `git mv`, `git rm`, `git add` for file operations
- Pre-commit hooks auto-fix issues - re-add modified files before committing

### Development Workflow
- Update README files when adding/changing functionality
- Use agent timeframes in estimates, not human ones
- Prefer concise prose and tables over long bulleted lists
- Run `python -m unittest test_jbom -v` for full test suite

### Shell & Environment Gotchas
**Testing:**
- Use `unittest`, NOT `pytest` - run with `python -m unittest discover -s tests`
- Test module paths: `tests.test_jbom`, not `test_jbom`

**Git Commits (zsh on macOS):**
- ALWAYS use single quotes for commit messages with special characters
- Example: `git commit -m 'feat!: breaking change'` (NOT double quotes)
- Exclamation marks (!) trigger zsh history expansion in double quotes
- Use `--no-verify` to bypass pre-commit hooks if needed

**Pre-commit Hooks:**
- Hooks may modify files - re-add them after running
- If hooks fail, check output and fix issues before retrying
- Common issues: flake8 line length, unused imports, tabs vs spaces

### Code Standards
- PEP 8 compliant with type hints throughout
- Extensive docstrings and inline comments
- Clear separation: parsing → matching → output phases
- Data validation at intake points

### Test Requirements
- Add tests for new component types in `TestComponentTypeDetection`
- Test new matching logic with corresponding test cases
- Functional tests in `tests/` directory for end-to-end validation
- 98 tests across 27 test classes - maintain coverage

## Test Data Locations
**Example inventory files:**
- `/Users/jplocher/Dropbox/KiCad/jBOM/examples/example-INVENTORY.{csv,xlsx,numbers}`

**Sample KiCad projects:**
- `/Users/jplocher/Dropbox/KiCad/projects/{AltmillSwitches,Core-wt32-eth0,LEDStripDriver}`

## Repository Structure
- `src/jbom/` - Main application code
- `tests/` - Functional and unit tests
- `docs/` - User and developer documentation
- `release-management/` - CI/CD and release configuration

## Architecture Summary
**Component Matching Pipeline:** parsing → filtering → ranking → scoring → output

**Key Data Classes:** `Generator`, `Component`, `InventoryItem`, `BOMEntry`

**Component Categories:** Resistors, Capacitors, Inductors, LEDs, ICs, Connectors, MCUs, Switches

**Features:** Check `docs/README.developer.md` for architecture details
