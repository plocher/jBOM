# jBOM Functional Test Plan

## Overview
This document outlines functional tests needed to complement existing unit tests. Current test coverage includes 109 unit tests covering individual components, but lacks comprehensive end-to-end functional testing of CLI workflows, error handling, and edge cases.

## Current Test Coverage

### Existing Tests
- **test_jbom.py** (~2000 LOC, 100+ tests): Unit tests for parsing, matching, BOM generation, field systems, hierarchical schematics
- **test_position.py** (75 LOC, 3 tests): Basic POS field presets, units/origin, filters
- **test_cli.py** (86 LOC, 4 tests): Mock-based CLI tests for --jlc flag behavior
- **test_integration_projects.py** (72 LOC, 2 tests): Real project tests (requires INVENTORY env var)
- **test_inventory_numbers_real.py**: Real inventory file tests (requires INVENTORY env var)

### Coverage Gaps
Current tests are primarily **unit tests** with mocked dependencies. Missing:
- End-to-end CLI workflows (actual file I/O, no mocks)
- Error handling and user-facing error messages
- Edge cases (empty files, malformed inputs, missing files)
- Output format validation (CSV structure, header correctness)
- Field preset combinations and custom field lists
- Multiple inventory formats (CSV, XLSX, Numbers)
- Console vs file output modes
- Hierarchical schematic traversal with real files

---

## Functional Test Categories

### 1. CLI End-to-End Tests (`tests/test_functional_cli.py`)

#### BOM Command - Happy Paths
- **Test**: Generate BOM with default fields
  - Input: Simple project, CSV inventory
  - Expected: BOM file created with +standard fields
  
- **Test**: Generate BOM with --jlc flag
  - Input: Simple project, CSV inventory, --jlc
  - Expected: BOM with JLC fields (reference, quantity, value, package, lcsc, smd)
  
- **Test**: Generate BOM with custom fields
  - Input: -f "Reference,Value,LCSC,I:Tolerance"
  - Expected: Only specified fields in output
  
- **Test**: Generate BOM with mixed preset and custom
  - Input: -f "+minimal,I:Manufacturer,C:Tolerance"
  - Expected: minimal fields + custom fields
  
- **Test**: Generate BOM to console
  - Input: -o console
  - Expected: Formatted table to stdout, not CSV
  
- **Test**: Generate BOM to stdout
  - Input: -o -
  - Expected: CSV to stdout (pipeline-friendly)
  
- **Test**: Generate BOM with verbose mode
  - Input: -v
  - Expected: Match_Quality and Priority columns present
  
- **Test**: Generate BOM with debug mode
  - Input: -d
  - Expected: Notes column with matching diagnostics
  
- **Test**: Generate BOM with --smd-only
  - Input: Project with SMD and PTH components
  - Expected: Only SMD components in output

#### BOM Command - Error Cases
- **Test**: Missing inventory file
  - Input: -i nonexistent.csv
  - Expected: Clear error message, exit code 1
  
- **Test**: Invalid inventory format
  - Input: -i textfile.txt
  - Expected: Error about unsupported format
  
- **Test**: Missing project directory
  - Input: nonexistent_project/
  - Expected: Error about missing project
  
- **Test**: Project with no schematic files
  - Input: Empty directory
  - Expected: Error "No .kicad_sch file found"
  
- **Test**: Invalid field name
  - Input: -f "Reference,InvalidField"
  - Expected: Error listing valid fields
  
- **Test**: Invalid preset name
  - Input: -f "+invalid_preset"
  - Expected: Error listing valid presets (+standard, +jlc, +minimal, +all)
  
- **Test**: Malformed schematic file
  - Input: Invalid S-expression syntax
  - Expected: Parse error with file name
  
- **Test**: Missing required headers in inventory
  - Input: CSV without required columns
  - Expected: Error about missing headers

#### POS Command - Happy Paths
- **Test**: Generate POS with default fields
  - Input: board.kicad_pcb
  - Expected: POS file with +standard fields (includes smd)
  
- **Test**: Generate POS with --jlc flag
  - Input: --jlc
  - Expected: JLC field order with smd field
  
- **Test**: Generate POS with custom fields
  - Input: -f "Reference,X,Y,SMD,Datasheet"
  - Expected: Only specified fields
  
- **Test**: Generate POS in inches
  - Input: --units inch
  - Expected: Coordinates in inches
  
- **Test**: Generate POS with aux origin
  - Input: --origin aux
  - Expected: Coordinates relative to aux axis
  
- **Test**: Generate POS for single layer
  - Input: --layer TOP
  - Expected: Only top-side components
  
- **Test**: Generate POS without SMD filter
  - Input: --smd-only=false (if supported) or modify PlacementOptions
  - Expected: All components (SMD + PTH)
  
- **Test**: Generate POS to console
  - Input: -o console
  - Expected: Formatted table output
  
- **Test**: Generate POS with both loaders
  - Input: --loader sexp vs --loader pcbnew
  - Expected: Same output (when KiCad available)

#### POS Command - Error Cases
- **Test**: Missing PCB file
  - Input: nonexistent.kicad_pcb
  - Expected: Error about missing file
  
- **Test**: Directory with no PCB
  - Input: Empty directory
  - Expected: Error "Could not find PCB file"
  
- **Test**: Malformed PCB file
  - Input: Invalid S-expression
  - Expected: Parse error with filename
  
- **Test**: Invalid units
  - Input: --units kilometers
  - Expected: argparse error with valid choices
  
- **Test**: Invalid origin
  - Input: --origin center
  - Expected: argparse error
  
- **Test**: Invalid layer
  - Input: --layer MIDDLE
  - Expected: argparse error
  
- **Test**: Invalid loader
  - Input: --loader magic
  - Expected: argparse error

### 2. Output Format Validation (`tests/test_functional_output.py`)

#### CSV Structure Tests
- **Test**: BOM CSV has correct headers
  - Validate header row matches field list
  
- **Test**: BOM CSV has correct row count
  - Match component count (after filtering)
  
- **Test**: BOM CSV is valid CSV (no malformed rows)
  - Use csv.reader to validate
  
- **Test**: POS CSV has correct headers
  - Validate header row matches field list
  
- **Test**: POS CSV coordinate precision
  - Verify 4 decimal places for coordinates
  
- **Test**: POS CSV rotation precision
  - Verify 1 decimal place for rotation
  
- **Test**: Console output is not CSV
  - Verify formatted table has visual separators
  
- **Test**: Stdout output is valid CSV
  - Verify -o - produces parseable CSV

#### Field System Tests
- **Test**: All preset fields exist in output
  - For each preset, verify all expected columns
  
- **Test**: Custom fields appear in correct order
  - User-specified order is preserved
  
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
1. CLI end-to-end happy paths (both BOM and POS)
2. CLI error handling (missing files, invalid arguments)
3. Output format validation (CSV structure, headers)
4. Field preset validation

### Medium Priority (Should Have)
5. Edge cases (empty files, malformed inputs)
6. Inventory format variations (CSV, XLSX, Numbers)
7. Console vs file output modes
8. Hierarchical schematic handling

### Low Priority (Nice to Have)
9. Performance tests
10. Golden file regression tests
11. Unicode and encoding edge cases
12. Memory usage tests

---

## Estimated Effort

- **Create test fixtures**: 2-4 hours
- **Test infrastructure setup**: 2-3 hours
- **High priority tests**: 8-12 hours
- **Medium priority tests**: 8-12 hours
- **Low priority tests**: 4-6 hours
- **Total**: 24-37 hours

## Success Criteria

- 50+ functional test cases covering major workflows
- No regressions when running full test suite
- Clear, actionable error messages for all failure modes
- 90%+ code coverage when combined with unit tests
- All tests pass on CI for Python 3.9-3.12
