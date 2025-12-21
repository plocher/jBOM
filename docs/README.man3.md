# jbom(3) — Python Library API

## NAME

jbom — Python library for KiCad bill of materials generation

## SYNOPSIS

```python
from jbom.api import generate_bom, generate_pos, back_annotate, search_parts, BOMOptions, POSOptions
from pathlib import Path
```

## DESCRIPTION

The jBOM library provides programmatic access to bill-of-materials generation, placement file generation, schematic back-annotation, and part searching.

## PUBLIC API

### Function: generate_bom()

**Signature**
```python
def generate_bom(
    input: Union[str, Path],
    inventory: Optional[Union[str, Path, List[Union[str, Path]]]] = None,
    output: Optional[Union[str, Path]] = None,
    options: Optional[BOMOptions] = None
) -> Dict[str, Any]
```

**Description**
: Generates a bill of materials for a KiCad project. Parses schematics, matches components against inventory, and returns structured data.

**Parameters**
: **input** — Path to project directory or .kicad_sch file
: **inventory** — Path(s) to inventory file(s) (.csv, .xlsx, .xls, .numbers)
: **output** — Output path (optional)
: **options** — BOMOptions instance or None

**Return value** (dict)
: **bom_entries** — List of BOMEntry objects
: **inventory_count** — Number of items in inventory
: **excluded_count** — Count of excluded components (e.g. non-SMD)
: **debug_diagnostics** — Diagnostic data list
: **components** — List of Component objects from schematics
: **available_fields** — Dict of {fieldname: description}

### Function: generate_pos()

**Signature**
```python
def generate_pos(
    input: Union[str, Path],
    output: Optional[Union[str, Path]] = None,
    options: Optional[POSOptions] = None
) -> Dict[str, Any]
```

**Description**
: Generates a component placement file (CPL/POS) for a KiCad project.

**Parameters**
: **input** — Path to project directory or .kicad_pcb file
: **output** — Output path (optional)
: **options** — POSOptions instance

**Return value** (dict)
: **board** — BoardModel object
: **entries** — List of PcbComponent objects
: **component_count** — Number of components found

### Function: back_annotate()

**Signature**
```python
def back_annotate(
    project: Union[str, Path],
    inventory: Union[str, Path],
    dry_run: bool = False
) -> Dict[str, Any]
```

**Description**
: Updates KiCad schematic files with data from an inventory file (Value, Footprint, LCSC, etc.) by matching UUIDs.

**Parameters**
: **project** — Path to project directory or .kicad_sch file
: **inventory** — Path to inventory file containing updates
: **dry_run** — If True, reports changes without writing to file

**Return value** (dict)
: **success** — Boolean success status
: **updated_count** — Number of components updated
: **updates** — List of update details
: **modified** — Boolean indicating if file was changed
: **error** — Error message string (if success=False)

**Example**
```python
from jbom.api import generate_bom, BOMOptions

# Generate BOM with JLC fabricator
opts = BOMOptions(verbose=True, fabricator='jlc')
result = generate_bom(input='MyProject/', inventory='inventory.xlsx', options=opts)

if result['bom_entries']:
    for entry in result['bom_entries']:
        print(f"{entry.reference}: {entry.value} -> {entry.lcsc}")
        print(f"  Fabricator: {entry.fabricator}, Part: {entry.fabricator_part_number}")
```

### Function: search_parts()

**Signature**
```python
def search_parts(
    query: str,
    provider: str = "mouser",
    limit: int = 10,
    api_key: Optional[str] = None,
    filter_parametric: bool = True
) -> List[SearchResult]
```

**Description**
: Search for parts from external distributors (e.g., Mouser).

**Parameters**
: **query** — Search query string (keyword, MPN, etc.)
: **provider** — Provider name (default: "mouser")
: **limit** — Maximum results to return
: **api_key** — Optional API key (overrides environment)
: **filter_parametric** — Enable smart parametric filtering

**Return value** (list)
: List of **SearchResult** objects

### Class: BOMOptions

**Signature**
```python
@dataclass
class BOMOptions:
    verbose: bool = False
    debug: bool = False
    smd_only: bool = False
    fields: Optional[List[str]] = None
    fabricator: Optional[str] = None
```

**Attributes**
: **verbose** — Include Match_Quality and Priority in output
: **debug** — Emit detailed matching diagnostics
: **smd_only** — Filter to surface-mount components only
: **fields** — List of output field names (None = use defaults)
: **fabricator** — Target fabricator ID (e.g. "jlc", "pcbway", "seeed", "generic") for part number lookup

### Class: POSOptions

**Signature**
```python
@dataclass
class POSOptions:
    units: str = "mm"
    origin: str = "board"
    smd_only: bool = True
    layer_filter: Optional[str] = None
    fields: Optional[List[str]] = None
    fabricator: Optional[str] = None
```

**Attributes**
: **units** — Coordinate units ("mm" or "inch")
: **origin** — Coordinate origin ("board" or "aux")
: **smd_only** — Filter to surface-mount components only
: **layer_filter** — Filter by side ("TOP" or "BOTTOM")
: **fields** — List of output field names
: **fabricator** — Target fabricator ID (e.g. "jlc") for default presets

### Class: SearchResult

Represents a part search result.

**Attributes**
```python
manufacturer: str            # Manufacturer name
mpn: str                    # Manufacturer part number
description: str            # Part description
price: Optional[float]      # Unit price
availability: str           # Availability string (e.g., "In Stock")
distributor_part_number: str # Distributor SKU
datasheet: Optional[str]    # Datasheet URL
attributes: Dict[str, str]  # Technical attributes (Value, Tolerance, etc.)
```

### Class: Component

Represents a component from the KiCad schematic.

**Attributes**
```python
reference: str              # e.g., "R1", "C2"
lib_id: str                # e.g., "Device:R"
value: str                 # e.g., "10k", "100nF"
footprint: str             # e.g., "Resistor_SMD:R_0603_1608Metric"
properties: Dict[str, str] # Custom properties from schematic
in_bom: bool              # Whether to include in BOM
dnp: bool                 # Do not populate flag
exclude_from_sim: bool    # Exclude from simulation flag
```

### Class: InventoryItem

Represents an entry from the inventory file.

**Attributes**
```python
ipn: str                    # Internal part number
keywords: str               # Search keywords
category: str               # Component type (RES, CAP, LED, etc.)
description: str            # Human-readable description
smd: str                    # SMD indicator (SMD/PTH/TH)
value: str                  # Component value
type: str                   # Component type description
tolerance: str              # Tolerance specification
voltage: str                # Voltage rating
amperage: str               # Current rating
wattage: str                # Power rating
lcsc: str                   # LCSC part number
manufacturer: str           # Manufacturer name
mfgpn: str                  # Manufacturer part number
datasheet: str              # Datasheet URL
package: str                # Physical package (0603, SOT-23, etc.)
priority: int               # Selection priority (1=preferred, higher=less)
raw_data: Dict[str, str]   # Original row data from inventory
```

### Class: BOMEntry

Represents a bill-of-materials line item.

**Attributes**
```python
reference: str             # Component reference(s) e.g., "R1, R2"
quantity: int              # Total quantity
value: str                 # Component value
footprint: str             # Package footprint
lcsc: str                  # Matched LCSC part number
manufacturer: str          # Matched manufacturer
mfgpn: str                 # Matched manufacturer part number
description: str           # Matched description
datasheet: str             # Matched datasheet URL
smd: str                   # SMD indicator (SMD/PTH)
match_quality: str         # Match quality indicator
notes: str                 # Matching notes/diagnostics
priority: int              # Priority of selected part
```

### Class: InventoryMatcher

Loads inventory and performs component matching.

**Constructor**
```python
matcher = InventoryMatcher(inventory_path: Path)
```

**Methods**
```python
find_matches(component: Component, debug: bool = False)
    -> List[Tuple[InventoryItem, int, Optional[str]]]
```
: Returns up to 3 matches: (inventory_item, score, debug_info_or_none)

### Class: BOMGenerator

Generates BOMs from components and inventory matcher.

**Constructor**
```python
gen = BOMGenerator(components: List[Component], matcher: InventoryMatcher)
```

**Methods**
```python
generate_bom(verbose: bool = False, debug: bool = False, smd_only: bool = False)
    -> Tuple[List[BOMEntry], int, List]
```
: Returns (bom_entries, smd_excluded_count, debug_diagnostics)

```python
write_bom_csv(entries: List[BOMEntry], output_path: Path, fields: List[str])
```
: Writes BOM to CSV file with specified columns.

```python
get_available_fields(components: List[Component]) -> Dict[str, str]
```
: Returns available output field names and descriptions.

## FABRICATOR CONFIGURATION

The fabricator system is fully configurable via YAML files. Available fabricators are loaded from the configuration hierarchy:

### Built-in Fabricators
- **jlc** — JLCPCB fabrication and assembly
- **pcbway** — PCBWay fabrication requirements
- **seeed** — Seeed Studio Fusion PCBA
- **generic** — Generic fabricator with dynamic manufacturer names

### Configuration Hierarchy
1. **Package defaults** — Built-in fabricator configurations
2. **System configs** — OS-specific system-wide settings
   - macOS: `/Library/Application Support/jbom/config.yaml`
   - Windows: `%PROGRAMDATA%\jbom\config.yaml`
   - Linux: `/etc/jbom/config.yaml`
3. **User configs** — Per-user customizations
   - macOS: `~/Library/Application Support/jbom/config.yaml`
   - Windows: `%APPDATA%\jbom\config.yaml`
   - Linux: `~/.config/jbom/config.yaml`
4. **Project configs** — Project-specific overrides
   - `.jbom/config.yaml` or `jbom.yaml` in project directory

### Custom Fabricators

Create custom fabricator configurations by copying and modifying existing ones:

```yaml
fabricators:
  - name: "My Custom Fab"
    id: "mycustom"
    based_on: "jlc"  # Inherit from JLC configuration
    description: "Custom fabricator based on JLC"
    part_number:
      header: "Custom Part Number"
      priority_fields:
        - "CUSTOM_PN"
        - "LCSC"
    bom_columns:
      "Reference": "reference"
      "Qty": "quantity"
      "Custom Part Number": "fabricator_part_number"
```

Then use in Python API:

```python
opts = BOMOptions(fabricator='mycustom')
result = generate_bom('MyProject/', options=opts)
```

## WORKFLOW EXAMPLE

```python
from jbom import (
    generate_bom_api, GenerateOptions, BOMGenerator,
    InventoryMatcher, Component, InventoryItem
)
from pathlib import Path

# Option 1: High-level API (recommended for most use cases)
opts = BOMOptions(
    verbose=True,
    fabricator='pcbway',  # Use PCBWay fabricator
    fields=['reference', 'quantity', 'value', 'lcsc', 'manufacturer']
)
result = generate_bom('MyProject/', 'inventory.xlsx', options=opts)

if result['exit_code'] == 0:
    # Process BOM entries
    for entry in result['bom_entries']:
        print(f"{entry.reference}: {entry.lcsc}")

    # Access diagnostics
    if result['debug_diagnostics']:
        for diagnostic in result['debug_diagnostics']:
            print(f"Note: {diagnostic}")

# Option 2: Low-level API (for custom workflows)
matcher = InventoryMatcher(Path('inventory.xlsx'))
gen = BOMGenerator([], matcher)  # components loaded separately

# Custom component processing
for component in custom_components:
    matches = matcher.find_matches(component, debug=True)
    if matches:
        best_match, score, debug_info = matches[0]
        print(f"{component.reference} → {best_match.ipn}")
```

## EXIT CODES

The library does not raise exceptions for normal validation errors. Instead, check the `exit_code` field in the result dict:

- **0** — Success, all components matched
- **1** — Error (file not found, unsupported format, etc.)
- **2** — Warning (one or more components unmatched, but BOM was generated)

## EXCEPTIONS

The library may raise:
- **FileNotFoundError** — Project or inventory file does not exist
- **ValueError** — Unsupported file format or invalid options
- **ImportError** — Optional packages (openpyxl, numbers-parser) not installed

## CONSTANTS

**ComponentType** — Component category constants (RES, CAP, IND, LED, DIO, IC, MCU, Q, CON, SWI, RLY, REG, OSC)

**DiagnosticIssue** — Diagnostic issue types (TYPE_UNKNOWN, NO_TYPE_MATCH, NO_VALUE_MATCH, PACKAGE_MISMATCH, NO_MATCH)

**CommonFields** — Common field name constants (VOLTAGE, AMPERAGE, WATTAGE, TOLERANCE, POWER, TEMPERATURE_COEFFICIENT)

## SEE ALSO

- [**README.md**](../README.md) — Overview and quick start
- [**README.man1.md**](README.man1.md) — Command-line interface reference
- [**README.man4.md**](README.man4.md) — KiCad Eeschema plugin integration
- [**README.developer.md**](README.developer.md) — Matching algorithms and internals
