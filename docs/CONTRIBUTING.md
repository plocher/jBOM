# Contributing to jBOM

Thank you for your interest in contributing to jBOM! This document provides guidelines and instructions for developers.

## Development Setup

### Prerequisites
- Python 3.9 or newer
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

The repository uses pre-commit hooks to prevent secrets, enforce code style, and catch common issues:

```bash
pre-commit install
```

For detailed information about pre-commit hooks, see [PRE_COMMIT_SETUP.md](../release-management/PRE_COMMIT_SETUP.md).

## Running Tests

Run the full test suite:
```bash
python -m pytest tests/ -v
# or using unittest:
python -m unittest tests.test_jbom -v
```

Run a specific test class:
```bash
python -m unittest tests.test_jbom.TestResistorParsing -v
```

Run a specific test method:
```bash
python -m unittest tests.test_jbom.TestResistorParsing.test_parse_res_to_ohms -v
```

All 98 tests should pass (with 3 skipped for optional dependencies):
```
Ran 98 tests in 0.037s
OK (skipped=3)
```

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
│   ├── __init__.py           # Package initialization
│   ├── __version__.py        # Version source of truth
│   ├── __main__.py           # CLI entry point
│   └── jbom.py              # Core module (~2700 lines)
├── tests/
│   ├── __init__.py
│   └── test_jbom.py         # Test suite (~2200 lines, 98 tests)
├── pyproject.toml           # Modern Python packaging config
├── setup.py                 # Legacy compatibility
├── README.md                # User documentation
├── CHANGELOG.md             # Version history
└── CONTRIBUTING.md          # This file
```

## Key Modules and Classes

### Core Data Classes
- `Component` - Schematic component (ref, lib_id, value, footprint, properties)
- `InventoryItem` - Inventory entry (ipn, category, value, package, attributes)
- `BOMEntry` - Output BOM row (reference, quantity, matched fields, notes)

### Main Classes
- `KiCadParser` - S-expression parsing for KiCad schematics
- `InventoryMatcher` - Component-to-inventory matching engine
- `BOMGenerator` - BOM generation and CSV output
- `GenerateOptions` - Options for BOM generation

### Key Functions
- `normalize_field_name()` - Convert field names to canonical snake_case
- `field_to_header()` - Convert field names to Title Case headers
- `generate_bom_api()` - Public API for programmatic use

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
python -m unittest tests.test_jbom -v
```

Ensure all tests pass before submitting.

### 4. Commit Your Changes
Write clear, descriptive commit messages:
```bash
git commit -m "Brief description of changes

More detailed explanation if needed:
- What was changed
- Why it was changed
- Any relevant context"
```

### 5. Push and Create Pull Request
```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Common Development Tasks

### Adding a New Component Type

1. Add type constant to `ComponentType` class
2. Update `_get_component_type()` method to detect the type
3. Add category-specific fields to `CATEGORY_FIELDS` dictionary
4. Implement matching logic in `_match_properties()`
5. Add tests to `TestComponentTypeDetection` and related test classes

### Extending Matching Algorithms

1. Modify `_match_properties()` for new scoring
2. Update `_parse_*()` methods for new value formats
3. Adjust tolerance substitution rules if needed
4. Add corresponding test cases

### Adding Spreadsheet Format Support

1. Add optional import with try/except
2. Create `_load_FORMAT_inventory()` method
3. Call `_process_inventory_data()` with normalized data
4. Add test cases for the new format

### Adding Output Fields

1. Extend `get_available_fields()`
2. Implement field extraction in `_get_field_value()`
3. Handle both inventory and component fields with I:/C: prefixes
4. Add tests for field discovery and output

## Testing Guidelines

### Test Organization
Tests are organized into 27 test classes covering:
- Core parsing (resistors, capacitors, inductors)
- Matching algorithms (inventory matching, scoring, sorting)
- Field system (normalization, disambiguation)
- Advanced features (hierarchical schematics, SMD filtering)
- Output formatting (CSV, custom fields)
- Spreadsheet support (CSV, Excel, Numbers)

### Writing New Tests

```python
class TestNewFeature(unittest.TestCase):
    """Test description"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary files if needed
        self.temp_inv = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        # ... initialize test data

    def tearDown(self):
        """Clean up after tests"""
        Path(self.temp_inv.name).unlink()

    def test_specific_behavior(self):
        """Test description - what should happen"""
        # Arrange: set up test data
        # Act: perform the action
        # Assert: verify the result
        self.assertEqual(actual, expected)
```

## Version Management

Version information is stored in a single location: `src/jbom/__version__.py`

When making a release:
1. Update version in `__version__.py`
2. Update `CHANGELOG.md` with changes
3. Commit with message: "Bump version to X.Y.Z"
4. Create git tag: `git tag -a vX.Y.Z -m "Description"`
5. Build and upload to PyPI (see packaging instructions below)

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
