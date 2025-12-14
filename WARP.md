# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

jBOM is a sophisticated KiCad Bill of Materials (BOM) generator written in Python. It intelligently matches schematic components against an inventory file (CSV, Excel, or Apple Numbers) to produce fabrication-ready BOMs. The tool emphasizes supplier-neutral designs, up-to-date inventory matching, and flexible output customization.

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

### Test Suite (`test_jbom.py` - ~2200 lines, 46 tests)
Comprehensive unit tests organized into 14 test classes:
- Core parsing: resistors, capacitors, inductors, component type detection
- Matching algorithms: inventory matching, priority ranking, BOM generation
- Advanced features: hierarchical schematics, SMD filtering, debug functionality
- Output options: custom fields, field disambiguation, verbose output

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

- `README.md` - User-facing documentation with installation, usage examples, and troubleshooting (10.7 KB)
- `README.developer.md` - Technical documentation covering architecture, matching algorithms, field system, and extension points (16.3 KB)
- `README.tests.md` - Test suite documentation with test class descriptions and running instructions (11.3 KB)
- `WARP.md` - This file, guidance for WARP agents working in this repo

## Directory Structure

```
jBOM/
├── jbom.py                 # Main application (~2700 lines)
├── test_jbom.py           # Test suite (~2200 lines, 46 tests)
├── README.md              # User documentation
├── README.developer.md    # Developer/technical documentation
├── README.tests.md        # Test suite documentation
├── WARP.md               # This file
├── LICENSE               # License terms
└── .gitignore            # Git configuration
```

## Development Focus Areas

### Strengths
- Well-organized data flow with clear separation of concerns
- Comprehensive test coverage (46 tests across 14 test classes)
- Sophisticated matching logic handling real-world component variations
- Multiple inventory format support (CSV, Excel, Numbers)
- Extensive documentation across three specialized README files
- Clean dataclass-based architecture for Component, InventoryItem, BOMEntry

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

