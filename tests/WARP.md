# Testing Guidelines

## Test Organization
- **Unit Tests:** Component parsing, matching logic, field handling
- **Functional Tests:** End-to-end CLI execution, file format validation
- **Test Data:** Use real inventory files from `/Users/jplocher/Dropbox/KiCad/jBOM-dev/`

## Test Structure
- 98 tests across 27 test classes
- 5 skipped tests (require optional dependencies)
- `tests/test_functional_base.py` - Shared utilities for functional tests

## Running Tests
```bash
# Full suite
python -m unittest test_jbom -v

# Specific test class
python -m unittest test_jbom.TestClassName -v

# Functional tests only
python -m unittest discover tests/ -v
```

## Test Requirements
- New component types require tests in `TestComponentTypeDetection`
- New matching logic needs corresponding test coverage
- Functional tests for CLI changes
- Mock external dependencies (files, networks)

## Coverage Areas
- **Parsing:** Resistor/capacitor/inductor value parsing
- **Matching:** Priority ranking, tolerance substitution
- **Output:** BOM generation, CSV formatting, custom fields
- **Error Handling:** Missing files, invalid data, no matches
