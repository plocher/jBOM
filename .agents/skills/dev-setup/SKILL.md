---
name: dev-setup
description: Setting up a fresh jBOM development environment — clone, virtualenv, editable install, pre-commit hooks, running tests, common development tasks, and building distribution packages. Use when onboarding to jBOM development for the first time or when reinstalling a dev environment from scratch.
---

# dev-setup

Procedural how-to for getting a jBOM development environment working from
scratch. Covers installation, the test suite, common extension tasks, and
package distribution. For the git workflow (branching, committing, opening
PRs), see the [git-workflow skill](../git-workflow/SKILL.md). For the
conceptual design principles that govern contributions, see
[docs/design/contributing.md](../../../docs/design/contributing.md).

## Prerequisites

- Python 3.10 or newer
- Git

## Installation

Clone the repository:

```bash
git clone https://github.com/SPCoast/jBOM.git
cd jBOM
```

Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Install in editable mode with all optional dependencies:

```bash
pip install -e ".[dev,excel,numbers]"
```

This installs jBOM in editable mode plus:

- `dev` extras: build, twine, wheel (for packaging)
- `excel` extras: openpyxl (for Excel support)
- `numbers` extras: numbers-parser (for Apple Numbers support)

### Install Pre-Commit Hooks

```bash
pre-commit install
```

The repository uses pre-commit hooks to enforce code style and catch common
issues. For details on what the hooks do, see
[release-management/PRE_COMMIT_SETUP.md](../../../release-management/PRE_COMMIT_SETUP.md).

## Running Tests

Always set `PYTHONPATH` to point at `src/` when running pytest:

```bash
# Full unit test suite
PYTHONPATH=src python -m pytest tests/ -v

# BDD functional test suite (must pass before opening any PR)
python -m behave --format progress

# BDD scenarios by tag during development
python -m behave --tags @regression
```

Run the full BDD suite before committing or opening a PR — failing scenarios
mean a broken contract with a user. During development, running by tag is fine;
before merge, run the complete suite.

## Common Development Tasks

### Adding a New Component Type

1. Add the type constant to `ComponentType` in `src/jbom/common/constants.py`.
2. Extend `COMPONENT_TYPE_MAPPING` for new type aliases
   (e.g., `"XFMR": "XFMR"`).
3. Add category-specific scoring fields to `CATEGORY_FIELDS` in `constants.py`.
4. Add pytest tests covering the new type detection and matching, and BDD
   scenarios for any user-visible behavior.

### Extending Matching Algorithms

1. Modify `services/inventory_matcher.py` (category-driven matching) or
   `services/sophisticated_inventory_matcher.py` (value-parametric and
   tolerance-aware matching).
2. Update value parsing in `common/value_parsing.py` for new value formats.
3. Adjust tolerance substitution rules if needed.
4. Add corresponding pytest tests and BDD scenarios.

### Adding Spreadsheet Format Support

1. Add optional import with `try/except` in `services/inventory_reader.py`.
2. Add the file extension to the detection logic.
3. Implement a reader returning normalized row dicts.
4. Add pytest and BDD test coverage for the new format.

### Adding a New CLI Command

1. Create `src/jbom/cli/mycommand.py` with `register_command(subparsers)`
   and `handle_mycommand(args)`.
2. Import and register in `src/jbom/cli/main.py`.
3. Add BDD scenarios in `features/` describing expected behavior.

### Writing a New pytest Test

```python
import pytest
from jbom.common.value_parsing import parse_res_to_ohms


def test_specific_behavior():
    """Test description - what should happen"""
    # Arrange: set up test data
    # Act: perform the action
    result = parse_res_to_ohms("10K")
    # Assert: verify the result
    assert result == 10000.0
```

### Writing a New BDD Scenario

```gherkin
# features/myfeature/mycommand.feature
Feature: My new command

  Scenario: Basic usage
    Given a KiCad project at "examples/AltmillSwitches"
    When I run "jbom mycommand examples/AltmillSwitches"
    Then the exit code is 0
    And the output contains "success"
```

## Version Management

Versioning is fully automated via GitHub Actions and `python-semantic-release`.
**Do not manually bump version files.** When commits merge to `main`, the CI
pipeline analyzes conventional commit messages (`feat:`, `fix:`, `feat!:`,
etc.), determines the correct semantic version bump, updates
`src/jbom/__version__.py` and `pyproject.toml`, creates a git tag and GitHub
Release, and publishes to PyPI.

To trigger a release: use conventional commit messages (see the
[git-workflow skill](../git-workflow/SKILL.md)) and merge to `main`.

## Package Distribution

### Building Distribution Packages

```bash
pip install build
python -m build
```

This creates:

- `dist/jbom-<version>-py3-none-any.whl` (wheel)
- `dist/jbom-<version>.tar.gz` (source distribution)

### Testing on TestPyPI

```bash
pip install twine
python -m twine upload --repository testpypi dist/*
```

Then verify the installation:

```bash
pip install --index-url https://test.pypi.org/simple/ jbom
```

### Uploading to PyPI

```bash
python -m twine upload dist/*
```

Authentication uses `~/.pypirc` with API tokens. In CI, the `PYPI_API_TOKEN`
secret is used automatically.
