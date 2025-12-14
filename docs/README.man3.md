# jbom(3) — Python Library API

## NAME

jbom — Python library for KiCad bill of materials generation

## SYNOPSIS

```python
from jbom import generate_bom_api, GenerateOptions, BOMGenerator, InventoryMatcher
from pathlib import Path
```

## DESCRIPTION

The jBOM library provides programmatic access to bill-of-materials generation. Use it to embed BOM generation into other tools or custom workflows.

## PUBLIC API

### Function: generate_bom_api()

**Signature**
```python
def generate_bom_api(
    project_path: Union[str, Path],
    inventory_path: Union[str, Path],
    options: Optional[GenerateOptions] = None
) -> Dict[str, Any]
```

**Description**
: Generates a bill of materials for a KiCad project. Parses schematics, matches components against inventory, and returns structured data.

**Parameters**
: **project_path** — Path to project directory or .kicad_sch file
: **inventory_path** — Path to inventory file (.csv, .xlsx, .xls, .numbers)
: **options** — GenerateOptions instance (see below) or None for defaults

**Return value** (dict)
: **exit_code** — 0 (success), 2 (warning/unmatched), 1 (error)
: **error_message** — Error text if exit_code != 0
: **file_info** — List of (component_count, filepath, warning) tuples
: **inventory_count** — Number of items in inventory
: **bom_entries** — List of BOMEntry objects (see below)
: **smd_excluded_count** — Components excluded by SMD filter
: **debug_diagnostics** — Diagnostic data if options.debug=True
: **components** — List of Component objects from schematics
: **available_fields** — Dict of {fieldname: description}

**Example**
```python
from jbom import generate_bom_api, GenerateOptions

opts = GenerateOptions(verbose=True, debug=False)
result = generate_bom_api('MyProject/', 'inventory.xlsx', options=opts)

if result['exit_code'] == 0:
    for entry in result['bom_entries']:
        print(f"{entry.reference}: {entry.value} → {entry.lcsc}")
else:
    print(f"Error: {result['error_message']}")
```

### Class: GenerateOptions

**Signature**
```python
@dataclass
class GenerateOptions:
    verbose: bool = False
    debug: bool = False
    smd_only: bool = False
    fields: Optional[List[str]] = None
```

**Attributes**
: **verbose** — Include Match_Quality and Priority in output
: **debug** — Emit detailed matching diagnostics
: **smd_only** — Filter to surface-mount components only
: **fields** — List of output field names (None = use defaults)

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

## WORKFLOW EXAMPLE

```python
from jbom import (
    generate_bom_api, GenerateOptions, BOMGenerator,
    InventoryMatcher, Component, InventoryItem
)
from pathlib import Path

# Option 1: High-level API (recommended for most use cases)
opts = GenerateOptions(
    verbose=True,
    fields=['Reference', 'Quantity', 'Value', 'LCSC', 'Manufacturer']
)
result = generate_bom_api('MyProject/', 'inventory.xlsx', options=opts)

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
