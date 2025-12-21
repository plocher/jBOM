# Unit Tests for jBOM

This document provides an overview of the unit test suite for jBOM.

## Test Suite Overview

The test suite covers core functionality, edge cases, and integration scenarios. Tests are self-documenting; please refer to the docstrings in the test files for detailed behavior descriptions.

### Core Functionality
Tests in this category validate the fundamental logic of BOM generation:
- **Value Parsing**: Parsing and formatting of Resistor, Capacitor, and Inductor values (EIA formats, precision handling).
- **Component Classification**: Logic for detecting component types (RES, CAP, LED, etc.) from library IDs and footprints.
- **Inventory Matching**: Algorithms for matching schematic components to inventory items, including priority ranking and tolerance substitution.
- **BOM Generation**: Grouping, sorting, and CSV generation logic.

### Enhanced Features
Tests covering advanced capabilities:
- **Category-Specific Fields**: Dynamic field mapping based on component type.
- **Field System**: Case-insensitive handling, I:/C: prefix disambiguation, and preset expansion.
- **Debug Functionality**: Validation of debug diagnostics and alternative match reporting.
- **Hierarchical Schematics**: Detection and processing of multi-sheet designs.
- **SMD Filtering**: Filtering logic for Surface Mount Devices.

## Running the Tests

### Prerequisites
- Python 3.9+
- Dependencies: `sexpdata` (and others listed in `pyproject.toml`)

### Commands
Run all tests:
```bash
python -m unittest discover -s tests -v
```

Run a specific test module:
```bash
python -m unittest tests.test_jbom -v
```

Run multiple specific test classes:
```bash
python -m unittest test_kicad_bom_generator.TestFieldPrefixSystem test_kicad_bom_generator.TestCustomFieldOutput -v
```

### Running Individual Tests

Run a specific test method:
```bash
python -m unittest test_kicad_bom_generator.TestResistorParsing.test_parse_res_to_ohms -v
```

### Alternative: Using pytest (if available)

If you have pytest installed:
```bash
pytest test_kicad_bom_generator.py -v
```

Run specific test classes with pytest:
```bash
pytest test_kicad_bom_generator.py::TestCategorySpecificFields -v
```

## Test Coverage Areas

### Core BOM Generation (Tests 1-8)
- ✅ **Value Parsing**: Resistors, capacitors, inductors with EIA formatting
- ✅ **Component Matching**: Type detection, inventory matching, priority ranking
- ✅ **BOM Assembly**: Component grouping, sorting, CSV generation
- ✅ **Precision Handling**: 1% resistor detection and warnings
- ✅ **Output Formats**: Basic, verbose, and manufacturer columns

### Enhanced Features (Tests 9-14)
- ✅ **Category-Specific Fields**: Component-appropriate property extraction
- ✅ **Field Disambiguation**: I:/C: prefix system for inventory vs component fields
- ✅ **Custom Output**: User-specified field selection with `-f` option
- ✅ **Ambiguous Fields**: Automatic expansion into separate columns
- ✅ **Field Discovery**: Dynamic detection of available fields
- ✅ **Debug Functionality**: Comprehensive debug mode testing including:
  - Enhanced Notes column with detailed matching information
  - Alternative match display with IPN, scores, priorities, and part numbers
  - Debug mode enabled/disabled behavior validation
  - Method signature validation for 3-tuple return format
- ✅ **Hierarchical Schematic Support**: Complete testing of multi-sheet designs including:
  - Automatic hierarchical schematic detection
  - Sheet file reference parsing and validation
  - Intelligent file selection with hierarchical awareness
  - Autosave file handling with user warnings
  - Multi-file component aggregation and BOM generation
  - Error handling for missing sub-sheets
- ✅ **SMD Component Filtering**: Testing of Surface Mount Device filtering including:
  - SMD-only BOM generation with `--smd` flag
  - SMD/PTH component detection from inventory SMD field
  - Footprint-based SMD inference for ambiguous cases
  - Mixed inventory handling with both SMD and PTH components

## Test Data

Tests use temporary CSV files and mock components to avoid dependencies on external files. The test inventory includes:

- Standard resistor values (E6/E12/E24 series)
- Precision resistors (1% tolerance)
- Common capacitors and inductors
- Priority-ranked components for testing selection logic
- Fields that demonstrate inventory/component conflicts
- Multiple matching items for testing alternative match functionality
- Components with various tolerance and property configurations
- Mock hierarchical schematic structures with root and sub-sheet files
- Autosave file scenarios for testing warning and fallback behavior
- Missing sub-sheet scenarios for error handling validation

## Expected Test Results

All tests should pass with output similar to:
```
..............................................
----------------------------------------------------------------------
Ran 46 tests in 0.021s

OK
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `sexpdata` is installed: `pip install sexpdata`

2. **Missing Test Files**: Tests create temporary files automatically - no external test data required

3. **Path Issues**: Run tests from the project directory containing `kicad_bom_generator.py`

### Test Failures

If tests fail:

1. **Check Dependencies**: Verify `sexpdata` is installed and importable
2. **Check Python Version**: Tests require Python 3.9+
3. **Check File Permissions**: Tests create temporary files in `/tmp`
4. **Review Recent Changes**: Failed tests may indicate breaking changes to core functionality

### Testing Debug Functionality

To specifically test the debug functionality:
```bash
# Run all debug tests
python -m unittest test_kicad_bom_generator.TestDebugFunctionality -v

# Test specific debug feature
python -m unittest test_kicad_bom_generator.TestDebugFunctionality.test_debug_alternatives_displayed -v
```

The debug tests validate:
- **Debug information presence**: Notes column contains component analysis
- **Alternative matches**: Multiple options shown with IPN, scores, and part numbers
- **Method signatures**: 3-tuple returns from `find_matches()` with debug info
- **Mode switching**: Debug on/off behavior works correctly

### Testing Hierarchical Functionality

To specifically test the hierarchical schematic support:
```bash
# Run all hierarchical tests
python -m unittest test_kicad_bom_generator.TestHierarchicalSupport -v

# Test specific hierarchical features
python -m unittest test_kicad_bom_generator.TestHierarchicalSupport.test_is_hierarchical_schematic -v
python -m unittest test_kicad_bom_generator.TestHierarchicalSupport.test_find_best_schematic_autosave_warning -v
python -m unittest test_kicad_bom_generator.TestHierarchicalSupport.test_process_hierarchical_schematic -v
```

The hierarchical tests validate:
- **Detection algorithms**: Accurate identification of hierarchical vs simple schematics
- **File parsing**: Correct extraction of sheet file references from root schematics
- **Selection logic**: Intelligent preference for hierarchical roots and directory-matching files
- **Autosave handling**: Proper warnings when using autosave files with graceful fallback
- **Multi-file processing**: Correct aggregation of components from multiple sheet files
- **Error resilience**: Proper handling of missing sub-sheet files with informative warnings

### Debugging Individual Tests

To debug a specific test:
```bash
python -m unittest test_kicad_bom_generator.TestResistorParsing.test_parse_res_to_ohms -v
```

Add print statements to see intermediate values:
```python
def test_example(self):
    result = self.matcher._parse_res_to_ohms('10K0')
    print(f"Parsed result: {result}")  # Debug output
    self.assertEqual(result, 10000.0)
```

## Contributing

When adding new features to the BOM generator:

1. **Add corresponding tests** to validate the new functionality
2. **Update existing tests** if interfaces change
3. **Run the full test suite** to ensure no regressions
4. **Update this README** if new test classes or significant functionality is added

The test suite should maintain comprehensive coverage of both legacy and new features to ensure the tool remains reliable and backward-compatible.
