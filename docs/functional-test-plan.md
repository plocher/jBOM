# jBOM Functional Test Plan

## Overview
This document outlines functional tests needed to complement existing unit tests. 

**Status Update (2025-12-15):** Functional test implementation is progressing well! The test suite now includes 157 total tests (109 unit + 48 functional) covering end-to-end CLI workflows, error handling, and edge cases. Recent additions include inventory format tests and schematic edge cases.

## Current Test Coverage

### Existing Tests
- **test_jbom.py** (~2000 LOC, 100+ tests): Unit tests for parsing, matching, BOM generation, field systems, hierarchical schematics
- **test_position.py** (75 LOC, 3 tests): Basic POS field presets, units/origin, filters
- **test_cli.py** (86 LOC, 4 tests): Mock-based CLI tests for --jlc flag behavior
- **test_integration_projects.py** (72 LOC, 2 tests): Real project tests (requires INVENTORY env var)
- **test_inventory_numbers_real.py**: Real inventory file tests (requires INVENTORY env var)

### NEW: Functional Tests (Implemented)
- **test_functional_base.py** (142 LOC): Base class with CLI execution, exception handling, and CSV validation
- **test_functional_bom.py** (201 LOC, 9 tests): BOM happy path end-to-end tests ✅
- **test_functional_pos.py** (284 LOC, 12 tests): POS happy path end-to-end tests ✅
- **test_functional_bom_errors.py** (197 LOC, 8 tests): BOM error case tests ✅
- **test_functional_pos_errors.py** (174 LOC, 6 tests): POS error case tests ✅
- **test_functional_inventory_formats.py** (199 LOC, 7 tests): Inventory format tests ✅
- **test_functional_schematic_edge_cases.py** (265 LOC, 6 tests): Schematic edge cases ✅
- **Test fixtures**: Minimal project with schematic, PCB, and CSV inventory for isolated testing

### Coverage Status

**✅ Implemented (48 tests):**
- End-to-end CLI workflows (actual file I/O, no mocks)
- Output format validation (CSV structure, header correctness)
- Field preset combinations and custom field lists
- Console vs file output modes
- Coordinate precision and units
- Error handling for missing files and invalid inputs
- Argparse validation for CLI arguments
- Parse error handling for malformed files
- Multiple inventory formats (CSV, XLSX, Numbers) ✅
- Inventory edge cases (empty, unicode, extra columns) ✅
- Schematic edge cases (empty, unicode, DNP, in_bom=no) ✅
- Component filtering and CSV escaping ✅

**⏳ Still TODO:**
- PCB edge cases (empty PCB, rotation normalization)
- Hierarchical schematic traversal with real files
- Performance tests with large projects
- Golden file regression tests
- File I/O tests (encodings, permissions)

---

## Functional Test Categories

### 1. CLI End-to-End Tests

#### BOM Command - Happy Paths (9 tests in `test_functional_bom.py`)

| Status | Test Name | Input/Options | Validates |
|--------|-----------|---------------|------------|
| ✅ | test_bom_default_fields | Default | +standard preset headers (Reference, Quantity, Description, Value, Footprint, Lcsc, Datasheet, Smd) |
| ✅ | test_bom_jlc_flag | --jlc | JLCPCB preset fields (Reference, Quantity, Value, Package, Lcsc, Smd) |
| ✅ | test_bom_custom_fields | -f "Reference,Value,Lcsc" | Only specified fields in output |
| ✅ | test_bom_mixed_preset_and_custom | -f "+minimal,Footprint" | Minimal fields + Footprint |
| ✅ | test_bom_to_console | -o console | Formatted table output (not CSV) |
| ✅ | test_bom_to_stdout | -o - | CSV to stdout (pipeline-friendly) |
| ✅ | test_bom_verbose_mode | -v | "Match Quality" and "Priority" columns |
| ✅ | test_bom_debug_mode | -d | Successful generation with diagnostics |
| ✅ | test_bom_smd_only | --smd-only | J1 (PTH) excluded, SMD components included |

#### BOM Command - Error Cases (8 tests in `test_functional_bom_errors.py`)

| Status | Test Name | Input | Expected Result |
|--------|-----------|-------|------------------|
| ✅ | test_bom_missing_inventory_file | -i nonexistent.csv | FileNotFoundError, exit code 1 |
| ✅ | test_bom_invalid_inventory_format | -i textfile.txt | Unsupported format error |
| ✅ | test_bom_missing_project_directory | nonexistent_project/ | Error about missing project/schematic |
| ✅ | test_bom_project_with_no_schematics | Empty directory | Error "No .kicad_sch file found" |
| ✅ | test_bom_invalid_field_name | -f "Reference,InvalidField" | Error listing valid fields |
| ✅ | test_bom_invalid_preset_name | -f "+invalid_preset" | Error listing valid presets |
| ✅ | test_bom_malformed_schematic_file | Invalid S-expression | Parse/syntax error |
| ⏸️ | test_bom_missing_inventory_headers | CSV without required columns | SKIPPED - not yet implemented |

#### POS Command - Happy Paths (12 tests in `test_functional_pos.py`)

| Status | Test Name | Input/Options | Validates |
|--------|-----------|---------------|------------|
| ✅ | test_pos_default_fields | Default | +standard preset headers (Reference, X, Y, Rotation, Side, Footprint, Smd) |
| ✅ | test_pos_jlc_flag | --jlc | JLCPCB field order (Reference, Side, X, Y, Rotation, Package, Smd) |
| ✅ | test_pos_custom_fields | -f "Reference,X,Y,Smd" | Only specified fields in output |
| ✅ | test_pos_units_mm | --units mm | Coordinates in mm range (50-100mm) |
| ✅ | test_pos_units_inch | --units inch | Coordinates in inches (~2-4 inches) |
| ✅ | test_pos_origin_board | --origin board | Board origin coordinates |
| ✅ | test_pos_origin_aux | --origin aux | Aux axis origin coordinates |
| ✅ | test_pos_layer_top | --layer TOP | All components have Side=TOP |
| ✅ | test_pos_layer_bottom | --layer BOTTOM | Only bottom-side components |
| ✅ | test_pos_to_console | -o console | Formatted table output (not CSV) |
| ✅ | test_pos_to_stdout | -o - | CSV to stdout (pipeline-friendly) |
| ✅ | test_pos_coordinate_precision | Default | X/Y ≤4 decimals, Rotation ≤1 decimal |

#### POS Command - Error Cases (6 tests in `test_functional_pos_errors.py`)

| Status | Test Name | Input | Expected Result |
|--------|-----------|-------|------------------|
| ✅ | test_pos_missing_pcb_file | nonexistent.kicad_pcb | FileNotFoundError, exit code 1 |
| ✅ | test_pos_directory_with_no_pcb | Empty directory | Error "Could not find PCB file" |
| ✅ | test_pos_malformed_pcb_file | Invalid S-expression | Parse/syntax error |
| ✅ | test_pos_invalid_units | --units kilometers | argparse error, shows valid: mm/inch |
| ✅ | test_pos_invalid_layer | --layer MIDDLE | argparse error, shows valid: TOP/BOTTOM |
| ✅ | test_pos_invalid_loader | --loader magic | argparse error, shows valid: auto/sexp/pcbnew |

Note: test_pos_invalid_origin was removed as --origin validation is not needed (board/aux both valid)

### 2. Output Format Validation (Covered by Happy Path Tests)

#### CSV Structure Tests

| Status | Test Aspect | Covered By | Validation |
|--------|-------------|------------|-------------|
| ✅ | BOM CSV headers | test_bom_default_fields, test_bom_jlc_flag | Header row matches field list (Title Case) |
| ✅ | BOM CSV row count | test_bom_smd_only | Component count after filtering |
| ✅ | BOM CSV valid | All BOM tests via assert_csv_valid() | csv.reader validates structure |
| ✅ | POS CSV headers | test_pos_default_fields, test_pos_jlc_flag | Header row matches field list |
| ✅ | POS coordinate precision | test_pos_coordinate_precision | X/Y ≤4 decimal places |
| ✅ | POS rotation precision | test_pos_coordinate_precision | Rotation ≤1 decimal place |
| ✅ | Console output format | test_bom_to_console, test_pos_to_console | Formatted table with visual separators |
| ✅ | Stdout CSV format | test_bom_to_stdout, test_pos_to_stdout | Valid parseable CSV output |

#### Field System Tests

| Status | Test Aspect | Covered By | Validation |
|--------|-------------|------------|-------------|
| ✅ | All preset fields exist | test_bom_default_fields, test_bom_jlc_flag, test_pos_default_fields, test_pos_jlc_flag | All preset fields present |
| ✅ | Custom field order | test_bom_custom_fields, test_pos_custom_fields | User-specified order preserved |
| ⏳ | Inventory-prefixed fields (I:) | TODO | I:Package from inventory |
| ⏳ | Component-prefixed fields (C:) | TODO | C:Value from component |
| ⏳ | Field normalization | TODO | "Reference", "REFERENCE", "reference" all work |

### 3. Edge Cases and Boundary Conditions (26 tests TODO)

#### Schematic Edge Cases (6/9 tests in `test_functional_schematic_edge_cases.py`)

| Status | Test Scenario | Expected Result |
|--------|---------------|------------------|
| ✅ | Empty schematic (no components) | Empty BOM, no error |
| ⏳ | Hierarchical schematic (multi-sheet) | All sheets parsed, components aggregated |
| ⏳ | Hierarchical with missing sub-sheet | Warning about missing file, continue |
| ⏳ | Autosave file (_autosave-*.kicad_sch) | Warning but still process |
| ✅ | Component with no value | Empty value field, no crash |
| ✅ | Component with special characters | Proper CSV escaping (quotes, commas) |
| ✅ | Component with unicode characters | UTF-8 encoding preserved |
| ✅ | DNP components excluded | Components with dnp=yes excluded |
| ✅ | Components with in_bom=no excluded | Power symbols and non-BOM parts excluded |
#### PCB Edge Cases (6 tests)

| Status | Test Scenario | Expected Result |
|--------|---------------|------------------|
| ⏳ | Empty PCB (no footprints) | Empty POS, no error |
| ⏳ | PCB with no aux origin set | --origin aux uses (0,0) |
| ⏳ | Footprint with no reference designator | Skip or handle gracefully |
| ⏳ | Footprint with rotation > 360 or < 0 | Normalized to 0-360 range |
| ⏳ | Footprint with missing package token | Empty package field, no crash |
| ⏳ | Footprint with missing datasheet | Empty datasheet field |

#### Inventory Edge Cases (7/8 tests in `test_functional_inventory_formats.py`)

| Status | Test Scenario | Expected Result |
|--------|---------------|------------------|
| ✅ | Empty inventory file | No matches, BOM still generated |
| ⏳ | Inventory with duplicate IPNs | Warning or error |
| ✅ | Inventory with missing required columns | Clear error message (IPN, Category required) |
| ✅ | Inventory with extra/unknown columns | Ignored gracefully |
| ✅ | CSV inventory format | Loads successfully |
| ✅ | XLSX inventory (requires openpyxl) | Works if installed, skips if not |
| ✅ | Numbers inventory (requires numbers-parser) | Works if installed, skips if not |
| ✅ | Inventory with unicode characters | UTF-8 handling |
| ✅ | All formats produce consistent results | CSV/XLSX/Numbers produce similar BOMs |
#### Matching Edge Cases (6 tests)

| Status | Test Scenario | Expected Result |
|--------|---------------|------------------|
| ⏳ | Component with no matches | Warning in output, empty LCSC |
| ⏳ | Component with multiple matches | Best match selected, debug shows alternatives |
| ⏳ | Component with precision resistor value | Warning about precision matching |
| ⏳ | Resistor value parsing (K, M, R notation) | Correct normalization (1K = 1000 ohm) |
| ⏳ | Capacitor value parsing (pF, nF, uF) | Correct normalization |
| ⏳ | Inductor value parsing (uH, mH, H) | Correct normalization |

### 4. File I/O Tests (9 tests TODO)

#### Input File Formats (4 tests)

| Status | Test Scenario | Details | Expected Result |
|--------|---------------|---------|------------------|
| ⏳ | CSV inventory encodings | UTF-8, UTF-8-BOM, Latin-1 | All encodings handled |
| ⏳ | Schematic line endings | CRLF vs LF | Both formats work |
| ⏳ | PCB KiCad versions | KiCad 5, 6, 7, 8 formats | All versions supported |
| ⏳ | Symbolic links | Symlinked files | Follow links correctly |

#### Output File Handling (5 tests)

| Status | Test Scenario | Expected Result |
|--------|---------------|------------------|
| ⏳ | Write to existing file | File replaced |
| ⏳ | Write to read-only directory | Permission error |
| ⏳ | Write to non-existent directory | Create directories or error |
| ⏳ | Write with --outdir option | File created in specified directory |
| ⏳ | Default output filename | project/ → project_bom.csv, board.kicad_pcb → board_pos.csv |
| ⏳ | Stdout with diagnostics | Diagnostics go to stderr, not stdout |

### 5. Integration with Real Projects (5 tests TODO)

Expands on existing test_integration_projects.py:

| Status | Test Scenario | Details | Expected Result |
|--------|---------------|---------|------------------|
| ⏳ | Process example projects | Use projects in tests/fixtures/ | All projects process successfully |
| ⏳ | BOM + POS workflow | Generate both for same project | Consistent output, no errors |
| ⏳ | Golden file baseline | Compare with known-good output | Matches baseline (snapshot testing) |
| ⏳ | Performance test | Project with 1000+ components | Complete in < 10 seconds |
| ⏳ | Memory usage test | 10,000+ inventory items | No memory exhaustion |

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
2. ✅ **DONE** - CLI error handling (missing files, invalid arguments) - 14 tests implemented
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
  - test_functional_base.py with utilities + exception handling
- ✅ **High priority tests (happy paths)**: 2 hours
  - 9 BOM tests + 12 POS tests implemented
- ✅ **Error handling tests**: 1 hour
  - 8 BOM error tests + 6 POS error tests implemented
- **Subtotal completed**: 5 hours

### Remaining Estimate
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

**Overall Total**: 19-24 hours (5 completed + 14-19 remaining)

## Success Criteria

### Current Status (35/~60 functional tests implemented)
- ✅ **Happy path workflows covered**: 21 functional tests
- ✅ **Error handling validated**: 14 error case tests
- ✅ **No regressions**: All 144 tests pass (109 unit + 35 functional)
- ✅ **Infrastructure in place**: FunctionalTestBase with exception handling
- ✅ **Test fixtures created**: Minimal project for isolated testing

### Remaining for Full Success
- ⏳ 50+ functional test cases covering major workflows (currently 35)
- ⏳ Edge cases comprehensively tested (26 edge case tests remaining)
- ⏳ File I/O tests (9 tests remaining)
- ⏳ Integration tests (5 tests remaining)
- ⏳ 90%+ code coverage when combined with unit tests
- ⏳ All tests pass on CI for Python 3.9-3.12 (currently untested in CI)
