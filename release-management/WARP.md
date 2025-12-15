# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

jBOM is a sophisticated KiCad Bill of Materials (BOM) generator written in Python. It intelligently matches schematic components against an inventory file (CSV, Excel, or Apple Numbers) to produce fabrication-ready BOMs. The tool emphasizes supplier-neutral designs, up-to-date inventory matching, and flexible output customization.

## Expectations
- if this is a git repository
   - use git mv, git rm and git add when renaming, moving, adding or removing files
   - use semantic versioning commits for each significant set of changes
- When adding or changing functionality, update the various README documentation files
- Use agent timeframes in estimates, not human ones
- When an example inventory file is needed to test the jBOM program, use these files
    - /Users/jplocher/Dropbox/KiCad/jBOM-dev/SPCoast-INVENTORY.numbers 
    - /Users/jplocher/Dropbox/KiCad/jBOM-dev/SPCoast-INVENTORY.xlsx 
    - /Users/jplocher/Dropbox/KiCad/jBOM-dev/SPCoast-INVENTORY.csv
- When a sample kicad project is needed, use one of
    - /Users/jplocher/Dropbox/KiCad/projects/AltmillSwitches 
    - /Users/jplocher/Dropbox/KiCad/projects/Core-wt32-eth0 
    - /Users/jplocher/Dropbox/KiCad/projects/LEDStripDriver 
- Concise prose and tables are preferred over long  bulleted lists

## Core Functionality

The application consists of two main files:

### Main Application (`jbom.py` - ~2700 lines)
The primary component matching engine supporting:
- **KiCad schematic parsing** via S-expression format (using `sexpdata`)
- **Hierarchical schematic support** for multi-sheet designs with intelligent root detection
- **Intelligent component matching** using category, package, and numeric value matching
- **Multiple inventory formats**: CSV, Excel (.xlsx/.xls), Apple Numbers (.numbers)
- **Advanced matching algorithms**:
  - Type-specific value parsing (resistors in ohms, capacitors in farads, inductors in henrys)
  - Tolerance-aware substitution (tighter tolerances can substitute for looser requirements)
  - Priority-based ranking (1=preferred, higher=less preferred)
  - EIA-style value formatting in output
- **Debug mode** with detailed matching information and alternative candidates
- **SMD filtering** capability for Surface Mount Device selection
- **Custom field system** with I:/C: prefix disambiguation for inventory vs component properties

### Test Suite (`test_jbom.py` - ~2200 lines, 98 tests)
Comprehensive unit tests organized into 27 test classes:
- **Core parsing**: Resistors, capacitors, inductors, component type detection
- **Matching algorithms**: Inventory matching, priority ranking, BOM generation, sorting
- **Field system**: Field normalization, case-insensitive handling, I:/C: prefix disambiguation
- **Advanced features**: Hierarchical schematics, SMD filtering, debug functionality, alternative matches
- **Output options**: Custom fields, field discovery, verbose output, multiple formats
- **Spreadsheet support**: CSV, Excel, and Numbers file handling

## Architecture Key Points

### Component Matching Pipeline
1. **Primary filtering** - Type, package, and value match (high confidence)
2. **Ranking & scoring** - Priority rank, then technical score from property matches
3. **Selection & alternatives** - Best match plus up to 2 alternatives for visibility
4. **Output formatting** - EIA-style values with warnings for precision mismatches

### Data Classes
- `Component` - Schematic component with ref, lib_id, value, footprint, properties
- `InventoryItem` - Inventory entry with IPN, category, value, package, attributes
- `BOMEntry` - Output BOM row with all required fields and optional debug info

### Key Features by Category
- **Resistors**: Precision detection (1% vs 5%), tolerance substitution
- **Capacitors**: Voltage-safety validation, type matching
- **Inductors**: Current/power rating matching
- **LEDs**: Brightness (mcd), wavelength, angle matching
- **ICs/Microcontrollers**: Family and voltage matching
- **Connectors**: Pin pitch matching

## Documentation

- `README.md` - User-facing overview with installation, quick start, and key concepts
- `docs/README.man1.md` - CLI reference with options, fields, examples, and troubleshooting
- `docs/README.man3.md` - Python library API reference for programmatic use
- `docs/README.man4.md` - KiCad Eeschema plugin setup and integration guide
- `docs/README.man5.md` - Inventory file format specification with field definitions
- `docs/README.developer.md` - Technical architecture, matching algorithms, field system, and extension points
- `docs/README.tests.md` - Test suite documentation with descriptions and running instructions
- `WARP.md` - This file, guidance for WARP agents working in this repo

## Directory Structure

```
jBOM/
├── jbom.py                    # Main application (~2700 lines)
├── test_jbom.py              # Test suite (~2200 lines, 98 tests, 27 classes)
├── README.md                 # User documentation with quick start
├── docs/
│   ├── README.man1.md        # CLI reference (man page style)
│   ├── README.man3.md        # Python library API (man page style)
│   ├── README.man4.md        # KiCad plugin setup (man page style)
│   ├── README.man5.md        # Inventory file format (man page style)
│   ├── README.developer.md   # Technical architecture and extension points
│   ├── README.tests.md       # Test suite documentation
│   ├── CHANGELOG.md          # Version history
│   └── CONTRIBUTING.md       # Contribution guidelines
├── release-management/
│   ├── WARP.md              # This file
│   ├── PRE_COMMIT_SETUP.md   # Pre-commit hook configuration
│   ├── PRE_COMMIT_QUICK_REFERENCE.md  # Pre-commit quick reference
│   ├── GITHUB_SECRETS_SETUP.md        # GitHub secrets configuration
│   └── SECURITY_INCIDENT_REPORT.md    # Security incident documentation
├── kicad_jbom_plugin.py     # KiCad Eeschema plugin wrapper
├── LICENSE                  # License terms
└── .gitignore               # Git configuration
```

## Development Focus Areas

### Strengths
- Well-organized data flow with clear separation of concerns
- Comprehensive test coverage (98 tests across 27 test classes)
- Sophisticated matching logic handling real-world component variations
- Multiple inventory format support (CSV, Excel, Numbers)
- Extensive documentation across four specialized README files plus man pages
- Clean dataclass-based architecture for Component, InventoryItem, BOMEntry
- Case-insensitive field name handling with normalization throughout

### Complexity Hotspots
- Component type detection logic with multiple pattern matching rules
- Tolerance substitution algorithm for resistors
- Field system with I:/C: prefix disambiguation
- Hierarchical schematic detection and multi-file processing
- SMD detection with footprint-based inference

## Common Development Tasks

### Adding New Component Types
1. Update `ComponentType` class with new type constant
2. Modify `_get_component_type()` to detect the new type
3. Add category-specific fields to `CATEGORY_FIELDS` dict
4. Add matching logic in component matching pipeline
5. Add tests to `TestComponentTypeDetection` and other relevant test classes

### Extending Matching Algorithms
- Modify `_match_properties()` for new property scoring
- Update `_parse_*()` methods for new value formats
- Adjust tolerance substitution rules in matching logic
- Add corresponding test cases for coverage

### Adding Inventory Features
- New spreadsheet formats: add optional import, update `_load_inventory()`, create `_load_FORMAT_inventory()`
- New field types: add to `CATEGORY_FIELDS`, update `get_available_fields()`, extend `_get_field_value()`
- New matching criteria: add to inventory Item, update filtering/scoring pipeline

## Testing Strategy

The test suite validates:
- **Parsing correctness**: Value parsing with various formats
- **Matching accuracy**: Priority ranking, property matching, alternative selection
- **Output formatting**: BOM generation, CSV output, custom fields
- **Feature completeness**: Hierarchical schematics, SMD filtering, debug mode
- **Error handling**: Missing files, incompatible formats, no matches

Run tests with: `python -m unittest test_jbom -v`

## Dependencies

**Required:**
- Python 3.9+
- `sexpdata` - KiCad S-expression parsing

**Optional:**
- `openpyxl` - Excel (.xlsx, .xls) support
- `numbers-parser` - Apple Numbers (.numbers) support

## Code Style Notes

- PEP 8 compliant with type hints throughout
- Extensive docstrings and inline comments
- Clear separation between parsing, matching, and output phases
- Data validation at intake points (e.g., inventory loading)
- Debug mode uses Notes column for detailed information

## Recent Development Activities

### Case-Insensitive Field Handling (Completed)
- Implemented `normalize_field_name()` function for canonical snake_case normalization
- Created `field_to_header()` for Title Case output formatting
- Updated all field processing to use normalized names internally
- Added 24 new unit tests for field normalization and disambiguation
- All field matching now handles variations: snake_case, Title Case, CamelCase, UPPERCASE, spaces, hyphens

### Tolerance Substitution Enhancement (Completed)
- Modified tolerance scoring to prefer exact matches over tighter tolerances
- Implemented next-tighter preference: when exact match unavailable, 5% is preferred over 1% for a 10% requirement
- Scoring penalty for over-specification: gap ≤ 1% gets full bonus, gap > 1% gets reduced bonus
- Updated documentation with concrete examples and scoring behavior explanation

### Documentation Updates (Completed)
- Created README.man5.md for inventory file format specification (213 lines)
- Created docs/README.man3.md for Python library API reference
- Created docs/README.man4.md for KiCad plugin integration guide
- Added docs/README.tests.md for test suite documentation
- Added SEE ALSO sections with markdown links to all READMEs for easy navigation
- Removed redundant Usage Documentation section from README.md
- Standardized naming to "jBOM" throughout all documentation

### Test Suite Growth
- Expanded from 46 tests to 98 tests (27 test classes)
- Added comprehensive field normalization tests
- Added spreadsheet format support tests
- Added tolerance substitution behavior tests
- All tests passing with 3 skipped (optional dependencies)

## GitHub Repository

Public repository: https://github.com/plocher/jBOM

Contribute at: https://github.com/plocher/jBOM/issues and https://github.com/plocher/jBOM/pulls

## Key Recent Changes

### Field System Enhancements
- Case-insensitive input: users can specify field names in any format
- Internal canonical representation using snake_case
- CSV output maintains human-readable Title Case headers
- I:/C: prefix system fully functional for field disambiguation

### Tolerance-Aware Matching
- Exact tolerance matches always preferred
- Tighter tolerances can substitute (with preference for next-tighter)
- No looser substitution (1% schematic cannot match 5% or 10% inventory)
- Scoring ensures sensible substitutions without over-specification

### Integration Options
- **KiCad plugin**: via `kicad_jbom_plugin.py` wrapper for Eeschema integration
- **Command-line**: via `jbom.py` with comprehensive options and presets
- **Python library**: programmatic use via `generate_bom_api()` function

## Extensions and Customization

### Adding New Features
- **New component types**: Add to `ComponentType` class, update `_get_component_type()`, add field mappings
- **New matching properties**: Modify `_match_properties()` scoring, update field systems
- **New spreadsheet formats**: Add optional import, implement `_load_FORMAT_inventory()` method
- **Custom output fields**: Extend `get_available_fields()` and `_get_field_value()`

### Testing New Features
- Run full suite: `python -m unittest test_jbom -v`
- Run specific class: `python -m unittest test_jbom.TestClassName -v`
- Run specific test: `python -m unittest test_jbom.TestClassName.test_method -v`
- Check test coverage areas in docs/README.tests.md
