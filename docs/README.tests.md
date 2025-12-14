# Unit Tests for jBOM

This document provides an overview of the unit test suite for jBOM and instructions for running the tests.

## Test Suite Overview

The test suite (`test_kicad_bom_generator.py`) contains **46 tests** organized into **13 test classes** that comprehensively validate both the core functionality and enhanced features including hierarchical schematic support, SMD filtering, advanced debug system, field disambiguation, and custom output options.

### Test Classes

#### Core Functionality Tests

1. **`TestResistorParsing`** - Tests resistor value parsing and EIA formatting
   - Parsing various formats: `330R`, `3R3`, `22K`, `2M2`, etc.
   - EIA formatting with precision control: `10K` vs `10K0`
   - Edge cases and invalid inputs

2. **`TestCapacitorParsing`** - Tests capacitor value parsing and formatting
   - Parsing formats: `100nF`, `1uF`, `220pF`, `1n0`, etc.
   - EIA-style formatting: `100nF`, `2u2F`, `4n7F`

3. **`TestInductorParsing`** - Tests inductor value parsing and formatting
   - Parsing formats: `10uH`, `2m2H`, `100nH`, etc.
   - EIA-style formatting: `10uH`, `2m2H`, `4u7H`

4. **`TestComponentTypeDetection`** - Tests component type detection logic
   - Detection from `lib_id`: `Device:R` → `RES`, `Device:C` → `CAP`
   - Detection from footprint patterns
   - Handling unknown component types

5. **`TestPrecisionResistorDetection`** - Tests precision resistor detection and warnings
   - Pattern detection for precision values: `10K0`, `47K5`, `2M7`
   - BOM generation warnings when 1% parts are implied but unavailable
   - Standard vs precision value handling

6. **`TestInventoryMatching`** - Tests inventory matching algorithms
   - Component to inventory matching by type, package, and value
   - Priority-based ranking (lower Priority numbers rank higher)
   - No-match scenarios

7. **`TestBOMGeneration`** - Tests BOM generation and CSV output
   - Component grouping by matching inventory items
   - Basic and verbose CSV output formats
   - Header validation and data integrity

8. **`TestBOMSorting`** - Tests BOM sorting by category and component numbering
   - Alphabetical category sorting: C, D, LED, R, U
   - Natural number sorting within categories: R1, R2, R10
   - Reference parsing and sort key generation

#### Enhanced Functionality Tests

9. **`TestCategorySpecificFields`** - Tests category-specific field mappings
   - `get_category_fields()` function validation
   - Value interpretation mapping: RES→Resistance, CAP→Capacitance
   - Category field constants validation

10. **`TestFieldPrefixSystem`** - Tests I:/C: prefix system for field disambiguation
    - Field discovery from inventory and component properties
    - Explicit field extraction with `I:` and `C:` prefixes
    - Ambiguous field handling and combined value return

11. **`TestDebugFunctionality`** - Tests debug mode and alternative match display
    - Debug information in Notes column
    - Alternative match formatting with IPN, scores, and part numbers
    - Debug mode enabled/disabled behavior
    - Method signature validation for 3-tuple returns

12. **`TestHierarchicalSupport`** - Tests hierarchical schematic functionality
    - Hierarchical schematic detection (`is_hierarchical_schematic()`)
    - Sheet file reference extraction (`extract_sheet_files()`)
    - Intelligent file selection (`find_best_schematic()`)
    - Autosave file handling with appropriate warnings
    - Multi-file processing (`process_hierarchical_schematic()`)
    - Missing sub-sheet handling and error recovery
    - Integration with simple (non-hierarchical) schematics

13. **`TestSMDFiltering`** - Tests SMD (Surface Mount Device) component filtering
    - SMD filtering enabled/disabled behavior
    - SMD component detection logic (`_is_smd_component()`)
    - Mixed SMD/PTH inventory handling
    - Footprint-based SMD inference for unclear SMD field values

14. **`TestCustomFieldOutput`** - Tests custom field selection in BOM output
    - Custom field CSV output with prefixed fields
    - Ambiguous field auto-expansion into separate columns
    - Field validation and error handling

## Running the Tests

### Prerequisites

- Python 3.9+
- Required dependencies: `sexpdata`

### Basic Test Execution

Run all tests:
```bash
python -m unittest test_kicad_bom_generator
```

Run with verbose output:
```bash
python -m unittest test_kicad_bom_generator -v
```

### Running Specific Test Classes

Run a specific test class:
```bash
python -m unittest test_kicad_bom_generator.TestResistorParsing -v
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
