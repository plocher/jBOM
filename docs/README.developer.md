# jBOM - Developer Documentation

This document provides detailed technical information about jBOM's internal workings, algorithms, and extension points.

## Architecture Overview

jBOM is a comprehensive fabrication tool that provides two main capabilities:

1. **BOM Generation**: Leverages schematic component fields and inventory spreadsheets to match components at BOM generation time. Using robust numeric matching for resistors, capacitors, and inductors, preference ranking for stocked/JLC parts, and flexible output options, this tool heuristically matches components found in the schematic to stock items in the inventory and produces a customizable BOM.csv file suitable for fabrication.

2. **Placement Generation**: Extracts component placement data from KiCad PCB files to generate CPL/POS files for pick-and-place assembly. Supports multiple loader methods (pcbnew API and S-expression parsing), flexible coordinate systems (board origin and aux origin), and output formats (KiCad-style and JLCPCB-compatible).

### Module Structure

jBOM follows a data-flow architecture (v3.0 refactoring, Dec 2024):

```
src/jbom/
├── api.py               # High-level API (generate_bom, BOMOptions)
│
├── cli/                 # Command-line interface
│   ├── main.py          # Argparse dispatcher with subcommands
│   ├── commands.py      # Base Command class with OutputMode
│   ├── bom_command.py   # BOM subcommand implementation
│   ├── pos_command.py   # POS subcommand implementation
│   ├── common.py        # Shared CLI utilities
│   └── formatting.py    # Console output formatting
│
├── common/              # Shared utilities and data types
│   ├── types.py         # Data classes: Component, InventoryItem, BOMEntry
│   ├── constants.py     # Enums: ComponentType, ScoreWeights, etc.
│   ├── fields.py        # Field name normalization and formatting
│   ├── fields_system.py # Field discovery and category-specific fields
│   ├── values.py        # Value parsing (resistors, capacitors, inductors)
│   ├── packages.py      # Package type detection from footprints
│   ├── sexp_parser.py   # S-expression parsing utilities
│   ├── utils.py         # File discovery and hierarchical schematics
│   ├── options.py       # BOMOptions dataclass
│   ├── output.py        # Output path resolution
│   └── generator.py     # Base generator utilities
│
├── loaders/             # Input file parsing
│   ├── schematic.py     # SchematicLoader: Parse .kicad_sch files
│   ├── pcb.py           # PCBLoader: Parse .kicad_pcb files
│   ├── pcb_model.py     # BoardModel and PcbComponent data structures
│   └── inventory.py     # InventoryLoader: CSV/Excel/Numbers
│
├── processors/          # Business logic
│   ├── component_types.py    # Component type detection and categorization
│   └── inventory_matcher.py  # InventoryMatcher: Match components to inventory
│
└── generators/          # Output file creation
    ├── bom.py           # BOMGenerator: Generate BOM CSV files
    └── pos.py           # POSGenerator: Generate placement CSV files
```

**Key Design Principles:**
- **Data-Flow Architecture**: Input (loaders) → Processing (processors) → Output (generators)
- **Separation by Function**: CLI, loaders, processors, generators are independent
- **Type Safety**: Extensive use of type hints and dataclasses throughout
- **Command Pattern**: CLI uses subcommands with shared base class
- **No Circular Dependencies**: Clean import hierarchy from common → loaders → processors → generators
- **Consistent Naming**: Loaders parse files, Processors transform data, Generators write output

## Key Features (Technical)

- **KiCad schematic parsing**
  - Uses robust S-expression parsing (sexpdata).
  - **Hierarchical schematic support**: Automatically detects and processes multi-sheet designs.
  - **Intelligent file selection**: Prefers hierarchical roots over sub-sheets, handles autosave files appropriately.
- **Primary filtering** is used to narrow down potential matches
  - Category: component must match inventory `Category` (e.g., RES, CAP, IND, LED, etc.).
  - Package: component `Footprint` must match inventory `Package` (e.g., 0603, 0805, SOT-23, SOIC, QFN) .
  - Value match by type:
    - RES: numeric compare `Value` in ohms (supports 330Ω, 330R, 3R3, 10k/10K0, 1M, etc.).
    - CAP: numeric compare `Value` in farads (supports 100n, 0.1u, 1u0, 220pF, etc.).
    - IND: numeric compare `Value` in henrys (supports 10uH, 2m2, 100nH, etc.).
- **Technical score**: `Value` + `Footprint` + field property matches (includes tolerance substitution)
- **Priority-based tie breaking** allows for primary and secondary inventory sources
  - Uses `Priority` column from inventory CSV (1=most desirable, higher=less desirable)
- **Tolerance-aware resistor display** and warnings
  - If schematic implies 1% (explicit trailing digit like 10K0, 47K5, 2M7, or Tolerance ≤ 1%), the BOM renders precision format.
  - If schematic implies 1% but no 1% inventory item exists, BOM Notes includes a warning with the best tolerance found.
- **Category-specific field system**
  - Automatic field discovery from inventory CSV and component properties
  - I:/C: prefix system for disambiguating inventory vs component fields
  - Custom field selection with `-f` option
- **Advanced debug functionality**
  - `-d/--debug` option provides detailed matching information in Notes column
  - Shows component analysis, filtering statistics, and alternative matches
  - Shows detailed component analysis and matching statistics
- **Organized BOM output**
  - Sorted by component category (C, D, LED, R, U, etc.) then by component number.
  - Natural number sorting: R1, R2, R3, R10.
  - Multi-component entries sorted by their lowest component number.
  - EIA-style value formatting
    - Resistors: 330R, 3R3, 10K, 10K0, 1M, 1M0
    - Capacitors: 100nF, 1uF, 220pF (always trailing F)
    - Inductors: 10uH, 2m2H, 100nH (always trailing H)
- **Flexible output columns**
  - Always includes: Reference, Quantity, Description, Value, Footprint, LCSC, Datasheet.
  - `-m/--manufacturer` adds Manufacturer and MFGPN columns.
  - `-v/--verbose` adds Match Quality (score) and debug columns.
  - `-f/--fields` allows custom field selection with I:/C: prefixes.
  - `--list-fields` shows all available fields.
  - Notes column describes BOM generation warnings or issues.

## Hierarchical Schematic Support

The BOM generator fully supports KiCad's hierarchical schematic designs:

### Automatic Detection
- **Hierarchical root detection**: Automatically identifies root schematics that reference sub-sheets
- **Multi-sheet processing**: Processes all referenced sub-sheets and combines components
- **Intelligent file selection**: Prefers hierarchical roots over individual sub-sheets when multiple files exist

### File Selection Logic
When processing a directory, the tool uses this priority order:
1. **Hierarchical roots matching directory name** (e.g., `Project/Project.kicad_sch` with sheet references)
2. **Any hierarchical root files** (files containing sheet references)
3. **Files matching directory name** (e.g., `Project/Project.kicad_sch`)
4. **Alphabetically first file**

### Example Hierarchical Processing with graceful handling of autosave files
```bash
# This project has a partially corrupted structure due to a KiCad crash:
Core-ESP32/
  ├── _autosave-Core-ESP32.kicad_sch  # Root with sheet references
  ├── IOConnections.kicad_sch         # Sub-sheet 1
  └── LevelShifters.kicad_sch         # Sub-sheet 2

# Results in:
% python3 jbom.py  Core-ESP32  -i SPCoast-INVENTORY.numbers
WARNING: Using autosave file _autosave-Core-ESP32.kicad_sch as it contains the hierarchical root (may be incomplete).
Hierarchical schematic set:
    0 Components      _autosave-Core-ESP32.kicad_sch (Warning: autosave file may be incomplete!)
   51 Components      LevelShifters.kicad_sch
   26 Components      IOConnections.kicad_sch
  ==============
   77 Components found in 3 schematic files

Inventory:
   96 Items       SPCoast-INVENTORY.numbers

BOM:
   21 Entries     Core-ESP32/Core-ESP32_bom.csv

```

## Data Flow & Functional Behavior

1) Input discovery
   - Project: the tool looks for a `.kicad_sch` file in the provided project directory.
   - Inventory: loads CSV/Excel/Numbers once; rows are normalized and cached.

2) Schematic parsing
   - S-expression parsing via `sexpdata` to extract symbols, Reference, Value, Footprint, Tolerance, W, etc.

3) Component grouping
   - Components are grouped by their best matching inventory item (IPN + footprint) to ensure equivalent components with alternate schematic values (e.g., 330R, 330Ω, 330 ohm) are properly grouped together.

4) Primary filtering per group (high certainty filtering)
   - Determine `comp_type` (RES/CAP/IND/LED/etc.) from the component's `Footprint` field.
   - Extract `comp_pkg` token from footprint (0603, 0805, SOT-23, SOIC, QFN, etc.).
   - Value comparison by type:
     - RES: parse to ohms (supports EIA and symbol forms) and compare numerically.
     - CAP: parse to farads and compare numerically.
     - IND: parse to henrys and compare numerically.
   - Candidates that fail type/package/value checks are excluded before any scoring.

5) Ranking and scoring
   - Priority rank (primary sort): Uses pre-computed Priority column from CSV (1=best, higher=worse).
   - Technical score (secondary sort): points for category match, value match, footprint match, and property matches (e.g., Tolerance, W).
   - Tolerance substitution: tighter tolerances (1%, 5%) can substitute for looser requirements (10%).
   - Sorting key: (priority, technical score).

6) Selection & alternatives
   - First candidate becomes the main BOM row.
   - Up to two alternative candidates are emitted as ALT rows (for visibility of near matches).

7) Warnings (resistors)
   - If the schematic implies 1% tolerance (trailing digit like 10K0, 47K5, 2M7, or Tolerance ≤ 1%) but none of the matched inventory parts are 1%, the Notes field includes a warning with the best tolerance found among candidates.

8) Value formatting for BOM
   - R: EIA-like (3R3, 330R, 10K, 10K0, 1M, 1M0), capital K and M. Trailing digit for precision is driven by schematic (trailing digit) or Tolerance ≤ 1%.
   - C: 1uF, 100nF, 220pF; unit appended.
   - L: 10uH, 2m2H, 100nH; unit appended.

9) CSV emission
   - Header built based on flags and whether any notes exist.
   - if  Manufacturer/MFGPN  information is required, use the `-m` option.
   - Additional processing notes are included with the `-v` option.

10) SMD Detection Logic: Robust component classification in _is_smd_component():
  1) Explicit SMD field values: Recognizes SMD, Y, YES, TRUE, 1 as SMD
  2) Explicit PTH field values: Recognizes PTH, THT, TH, THROUGH-HOLE, N, NO, FALSE, 0 as non-SMD
  3) Footprint-based inference: For unclear SMD field values, analyzes footprints:
    *  SMD indicators: 0402, 0603, 0805, 1206, 1210, sot-23, soic, tssop, qfn, dfn, bga
    *  Through-hole indicators: dip, through-hole, axial, radial
  4) Conservative default: Includes components when uncertain (better to include than exclude)

## BOMGenerator Class (`generators/bom.py`)

The `BOMGenerator` class is responsible for generating bill of materials from parsed components and inventory matches.

### Initialization

```python
from jbom.generators.bom import BOMGenerator
from jbom.processors.inventory_matcher import InventoryMatcher
from pathlib import Path

# Create BOM generator with components and matcher
components = [...] # from SchematicLoader
matcher = InventoryMatcher(Path('inventory.xlsx'))
generator = BOMGenerator(components, matcher)
```

### Core Methods

**`generate_bom(verbose, debug, smd_only)`**
- Main BOM generation method
- Returns: `(bom_entries, excluded_count, debug_diagnostics)`
- Groups components by matching inventory item
- Handles 1% resistor tolerance detection and warnings
- Filters for SMD-only if requested
- Sorts by category and component numbering

**`write_bom_csv(bom_entries, output_path, fields)`**
- Writes BOM to CSV file or stdout
- Handles field normalization and header generation
- Supports ambiguous field splitting (I:/C: prefixes)
- Special paths: "-", "console", "stdout" write to stdout

**`get_available_fields(components)`**
- Discovers all available fields from:
  - Standard BOM entry fields
  - Inventory CSV columns
  - Component properties from schematic
- Returns dict mapping normalized field names to descriptions
- Handles ambiguous fields (present in both inventory and components)

### Field Access Methods

**`_get_field_value(field, entry, component, inventory_item)`**
- Retrieves field value from appropriate source
- Handles standard BOM fields, inventory fields (i: prefix), component properties (c: prefix)
- Normalizes field names for case-insensitive matching
- Returns combined values for ambiguous fields

**`_get_inventory_field_value(field, inventory_item)`**
- Extracts field from inventory item's raw data
- Handles field name normalization and whitespace cleanup

**`_has_inventory_field(field, inventory_item)`**
- Checks if field exists in inventory data
- Uses normalized field name matching

### Component Analysis Methods

**`_analyze_no_match_component(component)`**
- Diagnoses why a component has no inventory matches
- Returns structured diagnostic data with:
  - Component information (reference, lib_id, value, footprint)
  - Analysis results (type, package, normalized value)
  - Issue classification (type unknown, no type match, no value match, package mismatch)

**`_generate_diagnostic_message(diagnostic_data, format_type)`**
- Formats diagnostic data for different outputs:
  - "bom": Semicolon-separated format for CSV Notes column
  - "console": User-friendly multi-line format for warnings

**`_format_issue_message(issue, comp_type, format_type)`**
- Formats specific issue messages based on issue type
- Provides context-appropriate error descriptions

### Utility Methods

**`_group_components()`**
- Groups components by best matching inventory item (IPN + footprint)
- Ensures equivalent component notations are grouped together
- Fallback grouping by value + footprint for unmatched components

**`_format_display_value(component)`**
- Converts component values to EIA format for display
- Handles precision indicators (10K0 for 1% resistors)
- Type-specific formatting (R/C/L)

**`_analyze_matches(matches, best_item, verbose)`**
- Handles tied priority matches
- Returns notes and alternative items based on verbose flag
- Limits alternative entries to keep BOM manageable (max 2)

**`_is_smd_component(entry)`**
- Determines if component is surface mount
- Uses multi-level detection (explicit field → footprint inference → conservative default)

**`_bom_sort_key(entry)`**
- Generates sort key for BOM entry
- Returns: (category, min_component_number, full_reference)
- Handles multi-component entries (e.g., "R1, R2, R3")

**`_parse_reference(ref)`**
- Parses component reference into category and number
- Handles multi-letter prefixes (LED, IC, etc.)
- Returns: (category, number) for sorting

## Field System and Custom Columns

The BOM generator supports a sophisticated field system for customizing output columns with case-insensitive field name handling.

### Case-Insensitive Field Naming

All field names are normalized internally to canonical snake_case, allowing flexible user input:

**Normalization function** (`normalize_field_name()`):
- Converts Title Case → snake_case: `Match Quality` → `match_quality`
- Converts CamelCase → snake_case: `MatchQuality` → `match_quality`
- Converts UPPERCASE → lowercase: `MATCH_QUALITY` → `match_quality`
- Handles prefixes: `I:Package` → `i:package`, `C:Tolerance` → `c:tolerance`
- Normalizes whitespace: multiple spaces and hyphens → underscores
- Idempotent: normalizing twice yields same result

**Header generation** (`field_to_header()`):
- Converts snake_case → Title Case for CSV output: `match_quality` → `Match Quality`
- Preserves prefixes without spaces: `i:package` → `I:Package` (not `I: Package`)
- All user input normalized before lookup; output headers remain human-readable

### Field Discovery

Use `--list-fields` to see all available fields from your inventory and schematic:

```bash
python3 jbom.py AltmillSwitches -i SPCoast-INVENTORY.csv --list-fields
```

This shows:
- **Standard BOM fields**: Reference, Quantity, Value, LCSC, etc. (normalized snake_case internally)
- **Inventory fields**: All columns from your inventory CSV (normalized for matching)
- **Component fields**: Properties found in schematic components (normalized for matching)

All fields are displayed and can be used in any case format.

### Field Prefixes (I:/C: System)

When inventory and component properties have the same name, use prefixes:

- `I:fieldname` - Force use of inventory field
- `C:fieldname` - Force use of component property field
- `fieldname` - Ambiguous field (combines both sources)

### Custom Field Examples

```bash
# Basic custom fields
python3 jbom.py project -i SPCoast-INVENTORY.csv -f "Reference,Value,LCSC,Manufacturer"

# Using prefixes to disambiguate
python3 jbom.py project -i SPCoast-INVENTORY.csv -f "Reference,Value,I:Package,I:Category,C:Tolerance"

# Ambiguous fields auto-expand to separate columns
python3 jbom.py project -i SPCoast-INVENTORY.csv -f "Reference,Value,Tolerance"
# Creates: Reference, Value, I:Tolerance, C:Tolerance
```

## Debug Functionality

The `-d/--debug` option provides comprehensive matching information:

### Debug Information Includes

1. **Component Analysis**:
   - Component reference and library ID
   - Detected component type (RES, CAP, IND, etc.)
   - Package extraction from footprint
   - Component value

2. **Issue Diagnosis**:
   - Specific reasons why components cannot be matched to inventory
   - Package mismatches with available alternatives
   - Missing component types or values in inventory
   - Component type detection issues

### Debug Output Example

**Console Warnings:**
```
Warnings:
============================================================
 1. Component C3 from Core-ESP32-eagle-import is a 10uF 0603 Capacitor
    Issue: Value '10uF' available in 1206 packages, but not 0603

 2. Component LED1 from Core-ESP32-eagle-import is a G 0603 LED
    Issue: No leds with value 'G' in inventory
```

**BOM File Debug Notes:**
```
No inventory match found Component: C3 (Core-ESP32-eagle-import:CAP0603) is a 10uF 0603 Capacitor; Issue: Value '10uF' available in 1206 packages, but not 0603
```

# Component Type Detection in jBOM

The script determines `comp_type` using the `_get_component_type()` method (lines 384-409). Here's how it works:

## Component Type Detection Logic

The method analyzes two key pieces of information from the KiCad component:

1. **`lib_id`** - The component's library identifier (e.g., \"Device:R\", \"SPCoast:resistor\")
2. **`footprint`** - The PCB footprint name (e.g., \"PCM_SPCoast:0603-RES\")

## Detection Rules

The method applies these rules in order:

### Resistors → `'RES'`
- Contains `'resistor'` in lib_id
- lib_id ends with `':r'` (e.g., \"Device:R\" → split(':') gives [\"Device\", \"R\"])
- Contains `'res'` in footprint

### Capacitors → `'CAP'`
- Contains `'capacitor'` in lib_id
- lib_id ends with `':c'`
- Contains `'cap'` in footprint

### Diodes → `'DIO'`
- Contains `'diode'` in lib_id
- lib_id ends with `':d'`
- Contains `'diode'` in footprint

### LEDs → `'LED'`
- Contains `'led'` in lib_id or footprint

### Inductors → `'IND'`
- Contains `'inductor'` in lib_id
- lib_id ends with `':l'`

### Connectors → `'CON'`
- Contains `'connector'` or `'conn'` in lib_id

### Switches → `'SWI'`
- Contains `'switch'` or `'sw'` in lib_id

### Transistors → `'Q'`
- Contains `'transistor'` in lib_id
- lib_id ends with something starting with `'q'`

### ICs/Microcontrollers → `'IC'`
- Contains `'ic'`, `'mcu'`, or `'microcontroller'` in lib_id
- lib_id ends with something starting with `'u'`
- lib_id ends with `':ic'`

## Examples

```python
# Real examples from KiCad schematics:
\"Device:R\"                    → 'RES'
\"Device:C\"                    → 'CAP'
\"Device:LED\"                  → 'LED'
\"Connector:Conn_01x02\"        → 'CON'
\"MCU:ESP32\"                   → 'IC'
\"SPCoast:resistor\"            → 'RES'

# With footprints:
footprint=\"PCM_SPCoast:0603-RES\"  → 'RES' (from 'res' in footprint)
footprint=\"Package_TO_SOT_SMD:SOT-23\"  → None (no clear indicator)
```

## Fallback Behavior

If none of the patterns match, the method returns None, which means:
•  The component type is unknown
•  Primary filtering will be less strict
•  Matching will rely more on other factors (value, footprint, keywords)

This approach allows the system to work with both standard KiCad libraries and custom library naming conventions, making it quite flexible for different PCB design workflows.

## PCB Module Architecture

The PCB module provides component placement extraction from KiCad PCB files for pick-and-place manufacturing.

### Board Loading

**Dual-mode loader** (`BoardLoader`):
- **pcbnew API mode**: Uses KiCad's native Python API when available (requires KiCad Python environment)
- **S-expression mode**: Built-in parser that works without KiCad installation
- **Auto mode**: Tries pcbnew first, falls back to S-expression automatically

**Features**:
- Extracts component positions (X, Y coordinates)
- Reads rotation angles (normalized 0-360°)
- Detects component layer (F.Cu/B.Cu → TOP/BOTTOM)
- Retrieves footprint information
- Supports KiCad 7 and 8 Reference property formats
- Recursive field discovery from footprint properties

### Position Generation

**PositionGenerator** class:
- Flexible field selection (presets and custom fields)
- Unit conversion (mm/inch)
- Origin selection (board origin or auxiliary axis)
- Layer filtering (TOP/BOTTOM)
- SMD-only filtering
- CSV output with customizable columns

**Field Presets**:
- `+kicad_pos`: Reference, X, Y, Rotation, Side, Footprint
- `+jlc`: Designator, Mid X, Mid Y, Layer, Rotation (JLCPCB format)
- `+minimal`: Reference, X, Y
- `+all`: All available fields

**Coordinate Systems**:
- Board origin: Lower-left corner (0,0)
- Aux origin: User-defined auxiliary axis (when set in PCB)
- Automatic fallback if aux origin not defined

### S-expression Parser

The S-expression parser handles `.kicad_pcb` files directly:
- Parses KiCad's nested S-expression format using `sexpdata`
- Handles both simple and complex property structures
- Supports multiple KiCad version formats
- Robust error handling for malformed files

### Integration with CLI

The `pos` subcommand integrates the PCB module:
```bash
jbom pos BOARD.kicad_pcb -o OUTPUT.csv [OPTIONS]
```

Options cascade through:
1. CLI argument parsing (`cli/main.py`)
2. BoardLoader instantiation with specified mode
3. PositionGenerator with field selection and filters
4. CSV output with proper formatting

## Spreadsheet Support Architecture

The tool supports multiple inventory file formats through a unified architecture:

### File Format Detection
- Automatic detection by file extension (.csv, .xlsx, .xls, .numbers)
- Graceful fallback with clear error messages for missing dependencies

### Excel Support (.xlsx, .xls)
- Uses `openpyxl` library for Excel file parsing
- Intelligent header detection: searches first 10 rows/columns for 'IPN' column
- Handles real-world spreadsheet layouts (data starting in arbitrary rows/columns)
- Processes only cells with actual data

### Numbers Support (.numbers)
- Uses `numbers-parser` library for Apple Numbers parsing
- Extracts data from first table in first sheet
- Uses proper cell access API: `table.cell(row, col)`
- Handles Numbers-specific table structure

### CSV Support (Legacy)
- Traditional comma-separated values using Python's csv module
- Maintains full backward compatibility

### Unified Processing
- All formats processed through `_process_inventory_data()` method
- Consistent field name cleaning and normalization
- Identical component matching logic regardless of input format

## Extension Points

### Adding New File Formats
1. Add optional import with try/except block
2. Add file extension to detection logic in `_load_inventory()`
3. Create new `_load_FORMAT_inventory()` method
4. Call `_process_inventory_data()` with normalized data

### Adding New Package Types
**Fully Automatic**: The footprint matching system now uses automatic dash removal, eliminating the need for manual mappings. The architecture is maximally simplified:

1. **`SMD_PACKAGES`**: Single authoritative list of SMD packages with consistent dash usage
2. **`PACKAGE_EXTRACTION_PATTERNS`**: Completely eliminated!
3. **`FOOTPRINT_PACKAGE_MAPPINGS`**: Completely eliminated!
4. **Automatic dash removal**: Handles inventory variations like 'sot23' vs 'sot-23' automatically

**To add a new package type:**
1. Add to `SMD_PACKAGES` (if SMD) or `THROUGH_HOLE_PACKAGES` (if PTH)
2. That's it! Both footprint extraction and matching work automatically

**Example**: Adding WLCSP support:
```python
SMD_PACKAGES = [..., 'wlcsp']
# Done! Works for both 'wlcsp' and 'wl-csp' inventory naming automatically
```

**Automatic Dash Handling**:
- Footprint: `sot-23` matches inventory: `sot23` ✓
- Footprint: `sod-123` matches inventory: `sod123` ✓
- Footprint: `sc-70` matches inventory: `sc70` ✓
- All 14+ packages with dashes work automatically
- No manual mapping tables to maintain

**Maximum Simplicity**:
- `SMD_PACKAGES`: Single source of truth - that's it!
- All footprint extraction and matching uses `SMD_PACKAGES` directly
- Longer patterns matched first to avoid conflicts (e.g., 'sot-23' before 'sot')
- Dash variants handled automatically in matching logic

### Customizing Component Matching
- Modify `_get_component_type()` for new component detection rules
- Extend `COMPONENT_TYPE_MAPPING` for new type aliases
- Add category-specific fields in `CATEGORY_FIELDS`
- Implement custom scoring in `_match_properties()`

### Output Customization
- Add new fields to `get_available_fields()`
- Extend `_get_field_value()` for custom field processing
- Modify `write_bom_csv()` for different output formats

## Project Structure

```
src/jbom/
  ├── api.py               # High-level API (generate_bom, BOMOptions)
  ├── __init__.py          # Public re-exports
  ├── cli/                 # CLI interface with Command pattern
  │   ├── main.py          # Argparse dispatcher
  │   ├── commands.py      # Base Command class
  │   ├── bom_command.py   # BOM subcommand
  │   ├── pos_command.py   # POS subcommand
  │   ├── common.py        # Shared CLI utilities
  │   └── formatting.py    # Console output
  ├── common/              # Shared utilities and data types
  │   ├── types.py         # Data classes (Component, InventoryItem, BOMEntry)
  │   ├── constants.py     # Enums (ComponentType, ScoreWeights)
  │   ├── fields.py        # Field normalization
  │   ├── fields_system.py # Field discovery
  │   ├── values.py        # Value parsing (R/C/L)
  │   ├── packages.py      # Package detection
  │   ├── utils.py         # File utilities
  │   └── ... (output.py, options.py, generator.py)
  ├── loaders/             # Input file parsing
  │   ├── schematic.py     # SchematicLoader (.kicad_sch)
  │   ├── pcb.py           # PCBLoader (.kicad_pcb)
  │   ├── pcb_model.py     # Board/component models
  │   └── inventory.py     # InventoryLoader (CSV/Excel/Numbers)
  ├── processors/          # Business logic
  │   ├── component_types.py    # Type detection
  │   └── inventory_matcher.py  # Component matching
  └── generators/          # Output file creation
      ├── bom.py           # BOMGenerator (CSV output)
      └── pos.py           # POSGenerator (placement files)
```

See [docs/README.arch.md](README.arch.md) for details.

### Import paths
- High-level API: `from jbom.api import generate_bom, BOMOptions`
- Loaders: `from jbom.loaders.schematic import SchematicLoader`
- Loaders: `from jbom.loaders.pcb import PCBLoader`
- Loaders: `from jbom.loaders.inventory import InventoryLoader`
- Processors: `from jbom.processors.inventory_matcher import InventoryMatcher`
- Generators: `from jbom.generators.bom import BOMGenerator`
- Generators: `from jbom.generators.pos import POSGenerator`
- Shared helpers: `from jbom.common.values import parse_res_to_ohms, farad_to_eia`

### Main Files

**jbom.py** (~2700 lines):
- KiCad S-expression parser (`KiCadParser`)
- Inventory loader supporting CSV, Excel, Numbers (`InventoryMatcher`)
- Component matching engine with intelligent scoring (`InventoryMatcher.find_matches`)
- BOM generation and output formatting (`BOMGenerator`)
- CLI entrypoint with argument parsing and output modes

**test_jbom.py** (~2200 lines, 74 tests):
- Unit tests across 14 test classes
- Coverage of parsing, matching, output formatting, and error handling
- Integration tests with real inventory files

**kicad_jbom_plugin.py** (~70 lines):
- KiCad Eeschema plugin wrapper
- Translates KiCad plugin interface to library API
- Handles file I/O and error reporting for plugin context

**Documentation**:
- [README.md](README.md): Entry point with installation and quick start
- [README.man1.md](README.man1.md): Complete CLI reference
- [README.man3.md](README.man3.md): Python library API reference
- [README.man4.md](README.man4.md): KiCad plugin setup and integration guide
- [README.man5.md](README.man5.md): Inventory file format
- [README.developer.md](README.developer.md): This file - technical deep dive and extension points

## Automated Releases with Semantic Versioning

jBOM uses GitHub Actions with python-semantic-release for automated version management and PyPI publishing.

### How It Works

The release process is triggered automatically by commits to the main branch:

1. **Conventional Commits**: Write commit messages following the Conventional Commits standard
2. **Automatic Analysis**: python-semantic-release analyzes commit messages
3. **Version Bump**: Determines MAJOR.MINOR.PATCH version change
4. **Update Files**: Updates `src/jbom/__version__.py` and `pyproject.toml`
5. **Create Tag**: Creates annotated git tag (e.g., v1.0.2)
6. **GitHub Release**: Generates release notes from commit messages
7. **PyPI Upload**: Builds and publishes to PyPI automatically
8. **Tests**: Full test suite runs before release

### Commit Message Format (Conventional Commits)

**Patch Release (1.0.1 → 1.0.2):**
```
fix: correct tolerance gap calculation in resistor matching

Fixes #42 - Tolerance gaps were not calculated correctly
when inventory had multiple candidates with different tolerances.
```

**Minor Release (1.0.1 → 1.1.0):**
```
feat: add support for custom validation functions

Users can now provide custom validation functions for
component matching via the new ValidatorFunc interface.
```

**Major Release (1.0.1 → 2.0.0):**
```
feat!: redesign component matching API

BREAKING CHANGE: The matching algorithm has been redesigned
for better performance. The old match_properties() method
is no longer available. Use new_match_scoring() instead.
```

### Git Tags

Tags are created automatically by the release process in the format `vX.Y.Z`:

```bash
# View all tags
git tag -l

# View a specific tag
git show v1.0.1

# Create manual tag (only if overriding automation)
git tag -a v1.0.2 -m "Release v1.0.2"
git push origin v1.0.2
```

### Commit Types

- **feat**: A new feature (results in a MINOR version bump)
- **fix**: A bug fix (results in a PATCH version bump)
- **feat!**: A breaking feature (results in a MAJOR version bump)
- **BREAKING CHANGE**: Indicates breaking changes (results in MAJOR bump)
- **docs**: Documentation only (no version bump)
- **style**: Code style changes (no version bump)
- **refactor**: Code refactoring (no version bump)
- **perf**: Performance improvements (no version bump)
- **test**: Test additions/changes (no version bump)
- **ci**: CI/CD changes (no version bump)
- **chore**: Maintenance tasks (no version bump)

### Workflows

Three GitHub Actions workflows automate the release process:

**test.yml**: Runs on every push and PR
- Tests on Python 3.9, 3.10, 3.11, 3.12
- Fails if any tests don't pass
- Prevents merging broken code

**semantic-release.yml**: Runs on pushes to main
- Analyzes conventional commits
- Determines version bump
- Updates version files
- Creates git tag
- Generates release notes
- Triggers publish workflow

**publish.yml**: Runs on release creation
- Runs full test suite
- Builds distribution packages
- Validates with twine
- Publishes to PyPI
- Creates GitHub Release page

### Manual Release Override

For edge cases, manually trigger a release:

```bash
# Create a release commit that skips CI
git commit --allow-empty -m "chore: release v1.1.0\n\n[skip ci]"
git push origin main
```

Or trigger manually in GitHub Actions UI:
- Go to Actions → Semantic Release → Run workflow

### Version Constraints

- Versions must follow semantic versioning: MAJOR.MINOR.PATCH
- Pre-release versions: 1.0.0-alpha.1, 1.0.0-beta.2
- Build metadata: 1.0.0+build.123 (not recommended for releases)

### Checking Latest Release

```bash
# Show latest git tag
git describe --tags --abbrev=0

# Show current version in code
grep "__version__" src/jbom/__version__.py

# Check PyPI for latest published version
python -m pip index versions jbom
```

### Development Before Release

During development, use work-in-progress commits:

```bash
# WIP commits don't trigger releases
git commit -m "wip: refactoring tolerance calculation"

# When ready, convert to proper commit
git commit --amend -m "feat: improve tolerance calculation algorithm"
```

## SEE ALSO

- [**README.md**](README.md) — Overview and quick start
- [**README.man1.md**](README.man1.md) — CLI reference
- [**README.man3.md**](README.man3.md) — Python library API
- [**README.man4.md**](README.man4.md) — KiCad plugin setup
- [**README.man5.md**](README.man5.md) — Inventory file format
