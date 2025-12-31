# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

# jBOM Project Guidance

jBOM is a sophisticated KiCad Bill of Materials generator in Python. It matches schematic components against inventory files (CSV, Excel, Numbers) to produce fabrication-ready BOMs and CPLs with supplier-neutral designs and flexible output customization.

## Expectations for agents

### Feature based development & testing
- Utilize a plan + task list based workflow with explicit review and approval before embarking on any implementation work.
- When adding new features and capabilities to jBOM,
    - we use a Behavior-Driven Development pattern to gather and validate functional requirements, then
    - we use these requirements to create gherkin feature tests and associated step definitions that will be used for Test Driven Development.
    - Use the axioms found in ./BDD_AXIOMS.md for guidance.
- Functional tests are used to validate and verify that the project behaves according to its requirements.
    - Functional tests are only allowed to change when functional requirements change.
- Unit tests are used to validate and verify proper implementation behaviors.
    - Unit tests must be updated, deleted and created as necessary whenever refactoring or feature additions causes changes to the implementation code base.
- The repo's main branch is expected to be production quality at all times. To ensure all work begins on a solid foundation, run all tests on newly created branchs.
    - If any tests fail, some previous activity wasn't performed according to these rules, the code base is not in a deterministic state, and new work can not start. Report all failed tests and stop.
- The development of a new feature (or mofification of an existing one) is not complete until all  all functional and unit tests pass.

#### Adding new features
- Use Gherkin Behavior-Driven Development (BDD) framework to capture Feature requirements as a set of Scenarios using nouns and verbs from the project's functional vocabulary.
- Use Cucumber to create step definitions that support the Gherkin Scenarios
- Keep Gherkin Scenerios and Cucubmer step definitions high-level and focused on requirements
- Unit tests are the place where implementation details are tested.
- Present a review of, and obtain approval for any new features or changes to an existing feature.
- Once a Feature's Scenerios and Step Definitions have been reviewed and approved
    - Use them to create a suite of functional tests.
    - Proceeed with the plan's task list

#### Refactoring or Modifying an existing feature
- Review and understand all the requirements and behavior of the project before attempting to modify it.
- Existing requirements and functional tests may not be changed; unit tests impacted by implementation changes must be updated to match.
- **Run all unit tests when changes are made**: `make unit` or `python -m unittest discover -s tests -v`
      - Fix all issues detected: In general, presume the unit tests are correct
- **Run full test suite (including integration)**: `make test`
- **Run a specific test module**: `python -m unittest tests.test_jbom -v`
- **Run a specific test class**: `python -m unittest tests.test_jbom.TestBOMGenerator -v`
- **Install for development**: `pip install -e .[dev,all]`
- **Clean artifacts**: `make clean`

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

## Coding Standards
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
