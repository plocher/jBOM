# Contributing to jBOM

Thank you for your interest in contributing to jBOM! This document provides guidelines and instructions for developers.

## Development Setup

### Prerequisites
- Python 3.10 or newer
- Git

### Installation for Development

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

Install in development mode with all optional dependencies:
```bash
pip install -e ".[dev,excel,numbers]"
```

This installs jBOM in editable mode plus:
- `dev` extras: build, twine, wheel (for packaging)
- `excel` extras: openpyxl (for Excel support)
- `numbers` extras: numbers-parser (for Apple Numbers support)

### Install Pre-Commit Hooks

The repository uses pre-commit hooks to enforce code style and catch common issues (no secret scanner is used in this repo):

```bash
pre-commit install
```

For detailed information about pre-commit hooks, see [PRE_COMMIT_SETUP.md](../release-management/PRE_COMMIT_SETUP.md).

## Running Tests

Run the full unit test suite:
```bash
PYTHONPATH=src python -m pytest tests/ -v
```

Run the BDD functional test suite (must pass before opening any PR):
```bash
python -m behave --format progress
```

Run BDD scenarios by tag during development:
```bash
python -m behave --tags @regression
```

All unit tests and BDD scenarios must pass before committing or opening a PR.

## Code Style

jBOM follows PEP 8 with the following guidelines:

- **Type hints**: Required throughout the codebase
- **Docstrings**: Comprehensive docstrings for all classes and functions
- **Line length**: 100 characters maximum
- **Imports**: Standard library, then third-party, then local (organized with blank lines)
- **Comments**: Clear comments explaining complex logic

### Example Function
```python
def normalize_field_name(field: str) -> str:
    """
    Normalize field names to canonical snake_case format.

    Accepts any format: snake_case, Title Case, CamelCase, spaces, mixed formats.

    Args:
        field: The field name in any format

    Returns:
        The normalized snake_case field name, or empty string if input is empty

    Examples:
        >>> normalize_field_name('Match Quality')
        'match_quality'
        >>> normalize_field_name('I:Package')
        'i:package'
    """
```

## Project Structure

```
jBOM/
├── src/jbom/
│   ├── cli/              # CLI commands (thin wrappers over services)
│   ├── common/           # Shared domain types, utilities, constants
│   ├── config/           # Fabricator and supplier configuration
│   ├── services/         # Business logic (reader, matcher, generator)
│   └── workflows/        # Workflow registry (extension point)
├── tests/                # pytest unit tests
├── features/             # Behave BDD scenarios (Gherkin)
│   └── steps/            # Step definitions
├── docs/                 # User-facing documentation (man pages)
├── legacy/               # Archived v6 source (read-only reference)
├── pyproject.toml        # Python packaging config
├── kicad_jbom_plugin.py  # KiCad Eeschema integration wrapper
├── README.md             # Quick start
└── docs/CHANGELOG.md     # Version history
```

## Key Modules and Classes

### Core Data Classes (`common/types.py`)
- `Component` - Schematic component (ref, lib_id, value, footprint, properties)
- `InventoryItem` - Inventory entry (ipn, category, value, package, attributes)
- `BOMEntry` - Output BOM row (reference, quantity, matched fields, notes)

### Services (`services/`)
- `SchematicReader` - Parse .kicad_sch files (including hierarchical designs)
- `InventoryReader` - Load CSV/Excel/Numbers inventory files
- `InventoryMatcher` - Match schematic components to inventory items
- `BOMGenerator` - Generate BOM CSV output
- `POSGenerator` - Generate CPL/placement output
- `ProjectFileResolver` - Resolve input paths to project files

### Configuration (`config/`)
- `fabricators.py` - Fabricator column presets (jlc, pcbway, seeed, generic)
- `suppliers.py` - Supplier URL and part number configuration

### Common Utilities (`common/`)
- `get_component_type()` - Classify component from lib_id and footprint
- `normalize_field_name()` - Convert field names to canonical snake_case
- `field_to_header()` - Convert field names to Title Case headers
- `GeneratorOptions` - Options dataclass for generator services

## Making Changes

### 1. Create a Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes
- Implement your feature or fix
- Add tests for new functionality
- Update documentation as needed
- Follow the code style guidelines

### 3. Run Tests
```bash
PYTHONPATH=src python -m pytest tests/ -v
python -m behave --format progress
```

All unit tests and BDD scenarios must pass before submitting.

### 4. Commit Your Changes

Write commit messages using the [Conventional Commits](https://www.conventionalcommits.org/) specification. The CI/CD pipeline parses these to automate version bumps and changelogs.

**Format:**
```
type(scope): subject

body (optional — what and why)

footer (optional — breaking changes, issue references)
```

**Common types:**

| Type | Description | Version bump |
|------|-------------|-------------|
| `feat` | New user-facing feature | minor |
| `fix` | Bug fix | patch |
| `docs` | Documentation only | none |
| `test` | Add or update tests | none |
| `refactor` | Code change with no feature/fix | none |
| `style` | Formatting, whitespace (no logic change) | none |
| `perf` | Performance improvement | patch |
| `chore` | Maintenance, dependency updates | none |
| `ci` | CI/CD pipeline changes | none |
| `build` | Build system changes | none |

**Scope** is optional and names the subsystem: `cli`, `bom`, `pos`, `inventory`, `search`, `matcher`, `docs`, etc.

**Breaking changes** — append `!` to the type or add a `BREAKING CHANGE:` footer (triggers a **major** version bump):
```bash
feat!: rename --inventory flag to --inventory-file
```
or
```bash
feat(cli): add --dry-run to bom command

BREAKING CHANGE: --output now defaults to stdout instead of a file
```

**Examples:**
```bash
git commit -m 'feat(cli): add inventory-search command'
git commit -m 'fix(matcher): handle empty package field gracefully'
git commit -m 'docs: update man1 with correct --inventory flag'
git commit -m 'test(bom): add BDD scenario for multi-source inventory'
git commit -m 'refactor(services): extract filter logic to component_filters.py'
```

Always include the co-author attribution line:
```bash
git commit -m 'feat: add foo

Co-Authored-By: Warp <agent@warp.dev>'
```

### 5. Push and Create Pull Request
```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Common Development Tasks

### Adding a New Component Type

1. Add the type constant to `ComponentType` in `src/jbom/common/constants.py`
2. Extend `COMPONENT_TYPE_MAPPING` for new type aliases (e.g., `"XFMR": "XFMR"`)
3. Add category-specific scoring fields to `CATEGORY_FIELDS` in `constants.py`
4. Add tests covering the new type detection and matching

### Extending Matching Algorithms

1. Modify `services/inventory_matcher.py` or `services/sophisticated_inventory_matcher.py`
2. Update value parsing in `common/value_parsing.py` for new value formats
3. Adjust tolerance substitution rules if needed
4. Add corresponding pytest tests and BDD scenarios

### Adding Spreadsheet Format Support

1. Add optional import with try/except in `services/inventory_reader.py`
2. Add file extension to the detection logic
3. Implement a reader returning normalized row dicts
4. Add pytest and BDD test coverage for the new format

### Adding a New CLI Command

1. Create `src/jbom/cli/mycommand.py` with `register_command(subparsers)` and `handle_mycommand(args)`
2. Import and register in `src/jbom/cli/main.py`
3. Add BDD scenarios in `features/` describing expected behavior
4. See `docs/README.developer.md` for a worked example

## Testing Guidelines

### Test Organization

**Unit tests** (`tests/`) cover key internal abstractions using pytest:
- Value parsing (resistors, capacitors, inductors)
- Inventory matching algorithms and scoring
- Field name normalization and disambiguation
- SMD detection, hierarchical schematics

**BDD scenarios** (`features/`) describe user-facing behavior using Gherkin:
- Each command (bom, inventory, pos, parts, search, inventory-search)
- Error handling and edge cases
- End-to-end workflow scenarios

Behave scenarios MUST pass before any PR is opened.

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

Versioning is fully automated via GitHub Actions and `python-semantic-release`. **Do not manually bump version files.**

When commits are merged to `main`, the CI pipeline:
1. Analyzes conventional commit messages (`feat:`, `fix:`, `feat!:`, etc.)
2. Determines the correct semantic version bump (MAJOR/MINOR/PATCH)
3. Updates `src/jbom/__version__.py` and `pyproject.toml`
4. Creates a git tag and GitHub Release
5. Publishes to PyPI

To trigger a release: use conventional commit messages and merge to `main`. The commit type drives the version bump:
- `fix:` → patch
- `feat:` → minor
- `feat!:` or `BREAKING CHANGE:` → major

## Package Distribution

### Building Distribution Packages

```bash
pip install build
python -m build
```

This creates:
- `dist/jbom-1.0.1-py3-none-any.whl` (wheel)
- `dist/jbom-1.0.1.tar.gz` (source distribution)

### Testing on TestPyPI

```bash
pip install twine
python -m twine upload --repository testpypi dist/*
```

Then test installation:
```bash
pip install --index-url https://test.pypi.org/simple/ jbom
```

### Uploading to PyPI

```bash
python -m twine upload dist/*
```

Authentication uses `~/.pypirc` with API tokens.

## Questions or Issues?

- Check existing issues and documentation
- Look at test cases for usage examples
- Review the README files for high-level context
- Check WARP.md for architectural guidance

## Code of Conduct

Be respectful and professional. We welcome contributors of all backgrounds and experience levels.

## License

By contributing to jBOM, you agree that your contributions will be licensed under the AGPLv3 license.
