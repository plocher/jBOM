# jBOM Functional Test Plan

## Overview
This document outlines functional tests needed to complement existing unit tests. 

**Status Update (2025-12-15):** Happy path functional tests have been implemented! The test suite now includes 130 total tests (109 unit + 21 functional) covering end-to-end CLI workflows. Remaining work focuses on error handling and edge cases.

## Current Test Coverage

### Existing Tests
- **test_jbom.py** (~2000 LOC, 100+ tests): Unit tests for parsing, matching, BOM generation, field systems, hierarchical schematics
- **test_position.py** (75 LOC, 3 tests): Basic POS field presets, units/origin, filters
- **test_cli.py** (86 LOC, 4 tests): Mock-based CLI tests for --jlc flag behavior
- **test_integration_projects.py** (72 LOC, 2 tests): Real project tests (requires INVENTORY env var)
- **test_inventory_numbers_real.py**: Real inventory file tests (requires INVENTORY env var)

### NEW: Functional Tests (Implemented)
- **test_functional_base.py** (136 LOC): Base class with CLI execution and CSV validation utilities
- **test_functional_bom.py** (201 LOC, 9 tests): BOM happy path end-to-end tests ✅
- **test_functional_pos.py** (284 LOC, 12 tests): POS happy path end-to-end tests ✅
- **Test fixtures**: Minimal project with schematic, PCB, and CSV inventory for isolated testing

### Coverage Status

**✅ Implemented (21 tests):**
- End-to-end CLI workflows (actual file I/O, no mocks)
- Output format validation (CSV structure, header correctness)
- Field preset combinations and custom field lists
- Console vs file output modes
- Coordinate precision and units

**⏳ Still TODO:**
- Error handling and user-facing error messages
- Edge cases (empty files, malformed inputs, missing files)
- Multiple inventory formats (CSV, XLSX, Numbers)
- Hierarchical schematic traversal with real files
- Performance tests with large projects
- Golden file regression tests

---

## Functional Test Categories

### 1. CLI End-to-End Tests

#### BOM Command - Happy Paths ✅ IMPLEMENTED (9 tests in `test_functional_bom.py`)
- ✅ **test_bom_default_fields**: Generate BOM with default (+standard) fields
  - Validates: Reference, Quantity, Description, Value, Footprint, Lcsc, Datasheet, Smd headers
  
- ✅ **test_bom_jlc_flag**: Generate BOM with --jlc flag
  - Validates: JLCPCB field preset (Reference, Quantity, Value, Package, Lcsc, Smd)
  
- ✅ **test_bom_custom_fields**: Generate BOM with custom fields
  - Input: -f "Reference,Value,Lcsc"
  - Validates: Only specified fields in output
  
- ✅ **test_bom_mixed_preset_and_custom**: Generate BOM with mixed preset + custom
  - Input: -f "+minimal,Footprint"
  - Validates: Minimal fields + Footprint field
  
- ✅ **test_bom_to_console**: Generate BOM to console
  - Input: -o console
  - Validates: Formatted table output (not CSV)
  
- ✅ **test_bom_to_stdout**: Generate BOM to stdout
  - Input: -o -
  - Validates: CSV to stdout (pipeline-friendly)
  
- ✅ **test_bom_verbose_mode**: Generate BOM with verbose mode
  - Input: -v
  - Validates: "Match Quality" and "Priority" columns present
  
- ✅ **test_bom_debug_mode**: Generate BOM with debug mode
  - Input: -d
  - Validates: Successful generation (Notes column if diagnostics present)
  
- ✅ **test_bom_smd_only**: Generate BOM with --smd-only filter
  - Validates: J1 (through-hole) excluded, SMD components included

#### BOM Command - Error Cases ⏳ TODO
- ⏳ **Test**: Missing inventory file
  - Input: -i nonexistent.csv
  - Expected: Clear error message, exit code 1
  
- ⏳ **Test**: Invalid inventory format
  - Input: -i textfile.txt
  - Expected: Error about unsupported format
  
- ⏳ **Test**: Missing project directory
  - Input: nonexistent_project/
  - Expected: Error about missing project
  
- ⏳ **Test**: Project with no schematic files
  - Input: Empty directory
  - Expected: Error "No .kicad_sch file found"
  
- ⏳ **Test**: Invalid field name
  - Input: -f "Reference,InvalidField"
  - Expected: Error listing valid fields
  
- ⏳ **Test**: Invalid preset name
  - Input: -f "+invalid_preset"
  - Expected: Error listing valid presets (+standard, +jlc, +minimal, +all)
  
- ⏳ **Test**: Malformed schematic file
  - Input: Invalid S-expression syntax
  - Expected: Parse error with file name
  
- ⏳ **Test**: Missing required headers in inventory
  - Input: CSV without required columns
  - Expected: Error about missing headers

#### POS Command - Happy Paths ✅ IMPLEMENTED (12 tests in `test_functional_pos.py`)
- ✅ **test_pos_default_fields**: Generate POS with default (+standard) fields
  - Validates: Reference, X, Y, Rotation, Side, Footprint, Smd headers
  
- ✅ **test_pos_jlc_flag**: Generate POS with --jlc flag
  - Validates: JLCPCB field order (Reference, Side, X, Y, Rotation, Package, Smd)
  
- ✅ **test_pos_custom_fields**: Generate POS with custom fields
  - Input: -f "Reference,X,Y,Smd"
  - Validates: Only specified fields in output
  
- ✅ **test_pos_units_mm**: Generate POS with millimeter units (default)
  - Validates: Coordinates in mm range (50-100mm)
  
- ✅ **test_pos_units_inch**: Generate POS in inches
  - Input: --units inch
  - Validates: Coordinates converted to inches (~2-4 inches)
  
- ✅ **test_pos_origin_board**: Generate POS with board origin (default)
  - Validates: Successful generation with board origin
  
- ✅ **test_pos_origin_aux**: Generate POS with aux origin
  - Input: --origin aux
  - Validates: Coordinates relative to aux axis
  
- ✅ **test_pos_layer_top**: Generate POS for TOP layer only
  - Input: --layer TOP
  - Validates: All components have Side=TOP
  
- ✅ **test_pos_layer_bottom**: Generate POS for BOTTOM layer only
  - Input: --layer BOTTOM
  - Validates: Only bottom-side components
  
- ✅ **test_pos_to_console**: Generate POS to console
  - Input: -o console
  - Validates: Formatted table output (not CSV)
  
- ✅ **test_pos_to_stdout**: Generate POS to stdout
  - Input: -o -
  - Validates: CSV to stdout (pipeline-friendly)
  
- ✅ **test_pos_coordinate_precision**: Verify coordinate precision
  - Validates: X/Y have ≤4 decimal places, Rotation has ≤1 decimal place

#### POS Command - Error Cases ⏳ TODO
- ⏳ **Test**: Missing PCB file
  - Input: nonexistent.kicad_pcb
  - Expected: Error about missing file
  
- ⏳ **Test**: Directory with no PCB
  - Input: Empty directory
  - Expected: Error "Could not find PCB file"
  
- ⏳ **Test**: Malformed PCB file
  - Input: Invalid S-expression
  - Expected: Parse error with filename
  
- ⏳ **Test**: Invalid units
  - Input: --units kilometers
  - Expected: argparse error with valid choices
  
- ⏳ **Test**: Invalid origin
  - Input: --origin center
  - Expected: argparse error
  
- ⏳ **Test**: Invalid layer
  - Input: --layer MIDDLE
  - Expected: argparse error
  
- ⏳ **Test**: Invalid loader
  - Input: --loader magic
  - Expected: argparse error

### 2. Output Format Validation

#### CSV Structure Tests ✅ COVERED BY HAPPY PATH TESTS
- ✅ **BOM CSV has correct headers**: Covered in test_bom_default_fields, test_bom_jlc_flag
  - Validates header row matches field list (Title Case)
  
- ✅ **BOM CSV has correct row count**: Covered in test_bom_smd_only
  - Validates component count after filtering
  
- ✅ **BOM CSV is valid CSV**: Covered in all BOM tests via assert_csv_valid()
  - Uses csv.reader to validate structure
  
- ✅ **POS CSV has correct headers**: Covered in test_pos_default_fields, test_pos_jlc_flag
  - Validates header row matches field list
  
- ✅ **POS CSV coordinate precision**: Covered in test_pos_coordinate_precision
  - Verifies ≤4 decimal places for coordinates
  
- ✅ **POS CSV rotation precision**: Covered in test_pos_coordinate_precision
  - Verifies ≤1 decimal place for rotation
  
- ✅ **Console output is not CSV**: Covered in test_bom_to_console, test_pos_to_console
  - Verifies formatted table has visual separators
  
- ✅ **Stdout output is valid CSV**: Covered in test_bom_to_stdout, test_pos_to_stdout
  - Verifies -o - produces parseable CSV

#### Field System Tests ✅ COVERED BY HAPPY PATH TESTS
- ✅ **All preset fields exist in output**: Covered in test_bom_default_fields, test_bom_jlc_flag, test_pos_default_fields, test_pos_jlc_flag
  - Validates all preset fields are present
  
- ✅ **Custom fields appear in correct order**: Covered in test_bom_custom_fields, test_pos_custom_fields
  - Validates user-specified order is preserved
  
- **Test**: Inventory-prefixed fields (I:) work
  - I:Package pulls from inventory, not component
  
- **Test**: Component-prefixed fields (C:) work
  - C:Value pulls from component, not inventory
  
- **Test**: Field normalization works
  - "Reference", "REFERENCE", "reference" all work

### 3. Edge Cases and Boundary Conditions (`tests/test_functional_edge_cases.py`)

#### Schematic Edge Cases
- **Test**: Empty schematic (no components)
  - Expected: Empty BOM, no error
  
- **Test**: Hierarchical schematic (multi-sheet)
  - Expected: All sheets parsed, components aggregated
  
- **Test**: Hierarchical with missing sub-sheet
  - Expected: Warning about missing file, continue
  
- **Test**: Autosave file (_autosave-*.kicad_sch)
  - Expected: Warning but still process
  
- **Test**: Component with no value
  - Expected: Empty value field, no crash
  
- **Test**: Component with special characters in value
  - Expected: Proper CSV escaping (quotes, commas)
  
- **Test**: Component with unicode characters
  - Expected: UTF-8 encoding preserved

#### PCB Edge Cases
- **Test**: Empty PCB (no footprints)
  - Expected: Empty POS, no error
  
- **Test**: PCB with no aux origin set
  - Expected: --origin aux uses (0,0)
  
- **Test**: Footprint with no reference designator
  - Expected: Skip or handle gracefully
  
- **Test**: Footprint with rotation > 360 or < 0
  - Expected: Normalized to 0-360 range
  
- **Test**: Footprint with missing package token
  - Expected: Empty package field, no crash
  
- **Test**: Footprint with missing datasheet property
  - Expected: Empty datasheet field

#### Inventory Edge Cases
- **Test**: Empty inventory file
  - Expected: No matches, warning
  
- **Test**: Inventory with duplicate IPNs
  - Expected: Warning or error
  
- **Test**: Inventory with missing required columns
  - Expected: Clear error message
  
- **Test**: Inventory with extra/unknown columns
  - Expected: Ignored gracefully
  
- **Test**: XLSX inventory (requires openpyxl)
  - Expected: Works if installed, error otherwise
  
- **Test**: Numbers inventory (requires numbers-parser)
  - Expected: Works if installed, error otherwise
  
- **Test**: Inventory with unicode characters
  - Expected: UTF-8 handling

#### Matching Edge Cases
- **Test**: Component with no matches in inventory
  - Expected: Warning in output, empty LCSC
  
- **Test**: Component with multiple matches (ambiguous)
  - Expected: Best match selected, debug shows alternatives
  
- **Test**: Component with precision resistor value
  - Expected: Warning about precision matching
  
- **Test**: Resistor value parsing (K, M, R notation)
  - Expected: Correct normalization (1K = 1000 ohm)
  
- **Test**: Capacitor value parsing (pF, nF, uF)
  - Expected: Correct normalization
  
- **Test**: Inductor value parsing (uH, mH, H)
  - Expected: Correct normalization

### 4. File I/O Tests (`tests/test_functional_io.py`)

#### Input File Formats
- **Test**: Read CSV inventory with various encodings
  - UTF-8, UTF-8-BOM, Latin-1
  
- **Test**: Read schematic with Windows line endings
  - CRLF vs LF
  
- **Test**: Read PCB with various KiCad versions
  - KiCad 5, 6, 7, 8 formats
  
- **Test**: Read from symbolic links
  - Expected: Follow links

#### Output File Handling
- **Test**: Write to existing file (overwrite)
  - Expected: File replaced
  
- **Test**: Write to read-only directory
  - Expected: Permission error
  
- **Test**: Write to non-existent directory
  - Expected: Create parent directories or error
  
- **Test**: Write with --outdir option
  - Expected: File created in specified directory
  
- **Test**: Default output filename generation
  - project/ → project_bom.csv
  - board.kicad_pcb → board_pos.csv
  
- **Test**: Write to stdout with other output
  - Ensure diagnostic messages go to stderr, not stdout

### 5. Integration with Real Projects (`tests/test_functional_integration.py`)

These expand on existing test_integration_projects.py:

- **Test**: Process all example projects
  - Use projects in tests/fixtures/ directory
  
- **Test**: BOM + POS workflow
  - Generate both for same project, verify consistency
  
- **Test**: Compare output with known-good baseline
  - Golden file testing (snapshot testing)
  
- **Test**: Performance with large projects
  - Project with 1000+ components
  - Should complete in reasonable time (< 10s)
  
- **Test**: Memory usage with large inventory
  - 10,000+ inventory items
  - Should not exhaust memory

---

## Implementation Strategy

### Test Fixtures Needed

#### Using Real Projects and Inventory
For realistic functional testing, use existing real-world resources:

**Inventory File:**
- `/Users/jplocher/Dropbox/KiCad/jBOM-dev/SPCoast-INVENTORY.numbers`
  - Full production inventory with comprehensive component data
  - Tests Numbers format support (requires numbers-parser)

**Sample KiCad Projects:**
- `/Users/jplocher/Dropbox/KiCad/projects/AltmillSwitches`
- `/Users/jplocher/Dropbox/KiCad/projects/Core-wt32-eth0`
- `/Users/jplocher/Dropbox/KiCad/projects/LEDStripDriver`

These provide:
- Real schematics and PCBs with actual component data
- Variety of component types and complexities
- Known-good baselines for validation

#### Additional Test Fixtures (create in `tests/fixtures/`)

1. **Minimal project** (for isolated testing)
   - Simple 1-sheet schematic with 5-10 components
   - Matching PCB with same components
   - Small CSV inventory with exact matches
   
2. **Error test fixtures** (for error path testing)
   - Malformed schematic (invalid S-expression)
   - Malformed PCB
   - Invalid inventory (wrong format, missing headers)
   - Empty files

3. **Inventory variants** (for format testing)
   - minimal.csv (CSV format)
   - inventory.xlsx (Excel, for optional test)
   - Use SPCoast-INVENTORY.numbers for Numbers format

### Test Infrastructure

```python
# tests/test_functional_base.py
class FunctionalTestBase(unittest.TestCase):
    """Base class for functional tests with common utilities."""
    
    @classmethod
    def setUpClass(cls):
        cls.fixtures = Path(__file__).parent / 'fixtures'
        
        # Real-world resources for integration testing
        cls.inventory_numbers = Path('/Users/jplocher/Dropbox/KiCad/jBOM-dev/SPCoast-INVENTORY.numbers')
        cls.real_projects = {
            'altmill': Path('/Users/jplocher/Dropbox/KiCad/projects/AltmillSwitches'),
            'core_wt32': Path('/Users/jplocher/Dropbox/KiCad/projects/Core-wt32-eth0'),
            'led_strip': Path('/Users/jplocher/Dropbox/KiCad/projects/LEDStripDriver'),
        }
        
        # Test fixtures for isolated/error testing
        cls.minimal_proj = cls.fixtures / 'minimal_project'
        cls.inventory_csv = cls.fixtures / 'inventory.csv'
    
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.tmp.name)
    
    def tearDown(self):
        self.tmp.cleanup()
    
    def run_jbom(self, args, expected_rc=0):
        """Run jBOM CLI and capture output."""
        from io import StringIO
        from jbom.cli.main import main
        
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        stdout = StringIO()
        stderr = StringIO()
        
        try:
            sys.stdout = stdout
            sys.stderr = stderr
            rc = main(args)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        
        if expected_rc is not None:
            self.assertEqual(rc, expected_rc, 
                f"Expected exit code {expected_rc}, got {rc}\nstderr: {stderr.getvalue()}")
        
        return rc, stdout.getvalue(), stderr.getvalue()
    
    def assert_csv_valid(self, csv_path):
        """Validate CSV file is well-formed."""
        import csv
        with open(csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        self.assertGreater(len(rows), 0, "CSV is empty")
        return rows
    
    def assert_csv_headers(self, csv_path, expected_headers):
        """Validate CSV has expected headers."""
        rows = self.assert_csv_valid(csv_path)
        self.assertEqual(rows[0], expected_headers)
```

### Test Execution
- Add functional tests to `make test` target
- Create separate `make functional` target for slow tests
- Use pytest markers if switching from unittest:
  - `@pytest.mark.functional`
  - `@pytest.mark.slow`
  - `@pytest.mark.requires_kicad`

### Continuous Integration
Functional tests should run in CI with:
- Matrix testing: Python 3.9, 3.10, 3.11, 3.12
- OS matrix: Linux, macOS, Windows
- Optional dependencies: with/without openpyxl, numbers-parser

---

## Priority

### High Priority (Must Have)
1. ✅ **DONE** - CLI end-to-end happy paths (both BOM and POS) - 21 tests implemented
2. ⏳ **TODO** - CLI error handling (missing files, invalid arguments)
3. ✅ **DONE** - Output format validation (CSV structure, headers) - Covered by happy path tests
4. ✅ **DONE** - Field preset validation - Covered by happy path tests

### Medium Priority (Should Have)
5. ⏳ **TODO** - Edge cases (empty files, malformed inputs)
6. ⏳ **TODO** - Inventory format variations (CSV, XLSX, Numbers)
7. ✅ **DONE** - Console vs file output modes - test_bom_to_console, test_pos_to_console, etc.
8. ⏳ **TODO** - Hierarchical schematic handling

### Low Priority (Nice to Have)
9. ⏳ **TODO** - Performance tests
10. ⏳ **TODO** - Golden file regression tests
11. ⏳ **TODO** - Unicode and encoding edge cases
12. ⏳ **TODO** - Memory usage tests

---

## Effort Tracking

### Completed (2025-12-15)
- ✅ **Create test fixtures**: 1 hour
  - Created minimal_project with schematic, PCB, inventory
- ✅ **Test infrastructure setup**: 1 hour
  - test_functional_base.py with utilities
- ✅ **High priority tests (happy paths)**: 2 hours
  - 9 BOM tests + 12 POS tests implemented
- **Subtotal completed**: 4 hours

### Remaining Estimate
- **Error handling tests**: 4-6 hours
  - BOM error cases (8 tests)
  - POS error cases (7 tests)
- **Edge case tests**: 6-8 hours
  - Schematic edge cases (7 tests)
  - PCB edge cases (6 tests)
  - Inventory edge cases (7 tests)
  - Matching edge cases (6 tests)
- **File I/O tests**: 4-6 hours
  - Input formats (4 tests)
  - Output handling (5 tests)
- **Integration tests**: 3-4 hours
  - Real project workflows (5 tests)
- **Total remaining**: 17-24 hours

**Overall Total**: 21-28 hours (4 completed + 17-24 remaining)

## Success Criteria

### Current Status (21/~60 functional tests implemented)
- ✅ **Happy path workflows covered**: 21 functional tests implemented
- ✅ **No regressions**: All 130 tests pass (109 unit + 21 functional)
- ✅ **Infrastructure in place**: FunctionalTestBase with utilities
- ✅ **Test fixtures created**: Minimal project for isolated testing

### Remaining for Full Success
- ⏳ 50+ functional test cases covering major workflows (currently 21)
- ⏳ Clear, actionable error messages validated for all failure modes
- ⏳ Edge cases comprehensively tested
- ⏳ 90%+ code coverage when combined with unit tests
- ⏳ All tests pass on CI for Python 3.9-3.12 (currently untested in CI)
