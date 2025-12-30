# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

# jBOM Project Guidance

jBOM is a sophisticated KiCad Bill of Materials generator in Python. It matches schematic components against inventory files (CSV, Excel, Numbers) to produce fabrication-ready BOMs with supplier-neutral designs and flexible output customization.

## Common Commands

### Development & Testing
- **Run all unit tests**: `make unit` or `python -m unittest discover -s tests -v`
- **Run full test suite (including integration)**: `make test`
- **Run a specific test module**: `python -m unittest tests.test_jbom -v`
- **Run a specific test class**: `python -m unittest tests.test_jbom.TestBOMGenerator -v`
- **Install for development**: `pip install -e .[dev,all]`
- **Clean artifacts**: `make clean`

### Version Control & Release
- **Commit Messages**: MUST follow **Conventional Commits** (`feat:`, `fix:`, `chore:`, `docs:`, etc.) to trigger automated semantic versioning.
  - Example: `git commit -m 'feat: add support for new inventory format'`
  - **Important**: Use **single quotes** for commit messages to avoid shell expansion issues (especially with `!`).
  - **Breaking Changes**: Use `feat!:` or include `BREAKING CHANGE:` in the footer.
- **Pre-commit Hooks**: This repo uses pre-commit hooks (flake8, etc.). If a hook modifies a file, you must `git add` the file again and retry the commit.
- **File Operations**: Use `git mv`, `git rm`, `git add` to track changes properly.

## Architecture Overview

jBOM follows a strict **Data-Flow Architecture**:
`Loaders (Input) → Processors (Logic) → Generators (Output)`

### Core Modules (`src/jbom/`)
1.  **`loaders/`**: Parses input files.
    -   `schematic.py`: Parses `.kicad_sch` using `sexpdata`. Handles hierarchical schematics.
    -   `pcb.py`: Parses `.kicad_pcb`. Dual-mode (pcbnew API or direct S-expression parsing).
    -   `inventory.py`: Loads CSV, Excel, or Numbers files. Normalizes data.
2.  **`processors/`**: Business logic.
    -   `inventory_matcher.py`: Core matching engine. Scores candidates based on value, footprint, and properties.
    -   `component_types.py`: Heuristics to classify components (RES, CAP, LED, etc.) from LibID/Footprint.
3.  **`generators/`**: Produces output.
    -   `bom.py`: Generates BOM CSVs. Handles grouping, sorting, and field formatting.
    -   `pos.py`: Generates Pick-and-Place files.
4.  **`cli/`**: Command-line interface.
    -   Uses `argparse` with a Command pattern (`commands.py`).

### Key Concepts
-   **Matching Logic**: Parsing → Filtering (Type/Value/Package) → Scoring → Ranking (Priority).
-   **Field System**:
    -   Internal: Normalized `snake_case`.
    -   Prefixes: `I:` for inventory fields, `C:` for component fields (e.g., `I:Voltage`).
-   **Hierarchical Schematics**: Automatically detects root sheets and processes sub-sheets.

## Expectations and Coding Standards

You are a detail oriented and organized collaborator who is helping me develop an open source utility application that will be used by electrical engineers as they create electronic projects using the KiCad electronic design CAD package.

jBOM is a github/pypi project that utilizes a PR-based feature branch methodology with semantic git commits.

The project favors a Behavioral- and test-driven development process (BDD with TDD).  You will find extensive gherkin tests in ./features/* as well as unit tests in ./tests/*

Agent notes can be found in WARP.md files in many folders.

-   **Code Style**: PEP 8 compliant with type hints throughout.
-   **Documentation**: Docstrings for all public methods. Inline comments for complex logic.
-   **Testing**:
    -   Regression and functional tests are exercised using `behave`
    -   Unit tests use `unittest` (NOT `pytest`).
    -   Maintain high unit test coverage, updating impacted unit tests when refactoring code changes implementation assumptions.
    -   Add gherkin feature tests (and steps) when adding new functionality.  Follow the BDD Axioms found in ./BDD_AXIOMS.md

## Test Data Locations
- **Example inventory files**: `/Users/jplocher/Dropbox/KiCad/jBOM/examples/example-INVENTORY.{csv,xlsx,numbers}`
- **Sample KiCad projects**: `/Users/jplocher/Dropbox/KiCad/projects/{AltmillSwitches,Core-wt32-eth0,LEDStripDriver}`

## Environment Gotchas

-   **Shell**: On macOS zsh, exclamation marks `!` in double quotes trigger history expansion. Always use single quotes for commit messages like `fix!: something`.
-   **Test Paths**: Use dot notation for tests (`tests.test_jbom`), not file paths.
-   **Auto-save Files**: The loader logic specifically handles (and usually ignores/warns about) KiCad autosave files.
