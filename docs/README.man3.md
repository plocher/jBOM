# jbom(3) — Python Library API

## NAME

jbom — Python library for KiCad bill of materials generation (planned for v8.x)

## SYNOPSIS

```python
# NOTE: A stable public Python API is planned for jBOM v8.x.
# In v7.x, the CLI is the stable interface. See jbom(1).
```

## DESCRIPTION

jBOM v7.x does not expose a stable public Python API. The primary interface is the CLI (`jbom bom`, `jbom pos`, etc.), which is stable and fully documented in [jbom(1)](README.man1.md).

A Python API is planned for v8.x to support:
- Programmatic BOM and placement file generation from Python scripts
- Integration with the KiCad Python scripting environment
- Back-annotation of schematics (`annotate` command, currently in `legacy/`)

For design inspiration, see `legacy/src/jbom/api.py` — the legacy API module that informed this plan.

For production use today, call the CLI from Python using `subprocess.run(["jbom", "bom", ...])`.

## DATA MODEL

The following types are defined in `src/jbom/common/types.py` and are expected to form the core of the planned v8.x API surface.

### Component

Represents a component from the KiCad schematic.

```python
@dataclass
class Component:
    reference: str               # e.g., "R1", "C2"
    lib_id: str                  # e.g., "Device:R"
    value: str                   # e.g., "10k", "100nF"
    footprint: str               # e.g., "Resistor_SMD:R_0603_1608Metric"
    uuid: str                    # KiCad UUID
    properties: Dict[str, str]   # Custom properties from schematic
    in_bom: bool                 # Whether to include in BOM
    exclude_from_sim: bool       # Exclude from simulation flag
    dnp: bool                    # Do Not Populate flag
```

### InventoryItem

Represents an entry from the inventory file.

```python
@dataclass
class InventoryItem:
    ipn: str                     # Internal part number
    keywords: str                # Search keywords
    category: str                # Component type (RES, CAP, LED, etc.)
    description: str             # Human-readable description
    smd: str                     # SMD indicator (SMD/PTH/TH)
    value: str                   # Component value
    type: str                    # Component type description
    tolerance: str               # Tolerance specification
    voltage: str                 # Voltage rating
    amperage: str                # Current rating
    wattage: str                 # Power rating
    lcsc: str                    # LCSC part number
    manufacturer: str            # Manufacturer name
    mfgpn: str                   # Manufacturer part number
    datasheet: str               # Datasheet URL
    package: str                 # Physical package (0603, SOT-23, etc.)
    distributor: str             # Distributor name
    distributor_part_number: str # Distributor SKU
    uuid: str                    # KiCad UUID for back-annotation
    fabricator: str              # Target fabricator (e.g. "jlc", "seeed")
    priority: int                # Selection priority (1=preferred, higher=less)
    source: str                  # Source tracking ("CSV", "JLC-Private", etc.)
    source_file: Optional[Path]  # Path to the file where this item was found
    raw_data: Dict[str, str]     # Original row data from inventory
```

### BOMEntry

Represents a bill of materials line item (aggregated by value+package).

```python
@dataclass
class BOMEntry:
    reference: str               # Component reference(s), e.g., "R1, R2"
    quantity: int                # Total quantity
    value: str                   # Component value
    footprint: str               # Package footprint
    lcsc: str                    # Matched LCSC part number
    manufacturer: str            # Matched manufacturer
    mfgpn: str                   # Matched manufacturer part number
    description: str             # Matched description
    datasheet: str               # Matched datasheet URL
    smd: str                     # SMD indicator (SMD/PTH)
    distributor: str             # Distributor name
    distributor_part_number: str # Distributor SKU
    match_quality: str           # Match quality indicator
    notes: str                   # Matching notes/diagnostics
    fabricator: str              # Fabricator ID
    fabricator_part_number: str  # Fabricator-specific part number
    priority: int                # Priority of selected part (verbose mode)
```

## PLANNED API (v8.x)

The following API is planned and subject to change. It is documented here to inform integrators and guide implementation.

### generate_bom()

```python
def generate_bom(
    input: Union[str, Path],
    inventory: Optional[Union[str, Path, List[Union[str, Path]]]] = None,
    output: Optional[Union[str, Path]] = None,
    fabricator: str = "generic",
    fields: Optional[List[str]] = None,
    verbose: bool = False,
) -> Dict[str, Any]
```

Returns a dict with `bom_entries` (list of `BOMEntry`), `component_count`, `unmatched_count`, `exit_code`.

### generate_pos()

```python
def generate_pos(
    input: Union[str, Path],
    output: Optional[Union[str, Path]] = None,
    fabricator: str = "generic",
    fields: Optional[List[str]] = None,
    smd_only: bool = False,
    layer: Optional[str] = None,
    origin: str = "board",
) -> Dict[str, Any]
```

Returns a dict with `entries` (list of placement rows), `component_count`.

### generate_inventory()

```python
def generate_inventory(
    input: Union[str, Path],
    output: Optional[Union[str, Path]] = None,
    existing_inventory: Optional[Union[str, Path]] = None,
    filter_matches: bool = False,
) -> Dict[str, Any]
```

Returns a dict with `inventory_items` (list of `InventoryItem`), `field_names`.

### search_parts()

```python
def search_parts(
    query: str,
    provider: str = "mouser",
    limit: int = 10,
    api_key: Optional[str] = None,
) -> List[SearchResult]
```

### back_annotate() (planned for v8.x)

```python
def back_annotate(
    project: Union[str, Path],
    inventory: Union[str, Path],
    dry_run: bool = False,
) -> Dict[str, Any]
```

The `annotate` command is currently available in `legacy/src/jbom/cli/commands/builtin/annotate.py` and is planned to be re-implemented as part of the v8.x public API.

## WORKAROUND FOR v7.x

Until the Python API is available, call the CLI from Python:

```python
import subprocess

result = subprocess.run(
    ["jbom", "bom", "MyProject/", "--inventory", "inventory.csv", "--jlc", "-o", "bom.csv"],
    check=True,
)
```

## FABRICATOR CONFIGURATION

The fabricator system is configurable via YAML files. See the Configuration section in [README.md](../README.md) for the full hierarchy and customization guide.

Built-in fabricators: `jlc`, `pcbway`, `seeed`, `generic`.

## SEE ALSO

- [**README.md**](../README.md) — Overview and quick start
- [**README.man1.md**](README.man1.md) — Command-line interface reference
- [**README.man4.md**](README.man4.md) — KiCad Eeschema plugin integration
- [**README.man5.md**](README.man5.md) — Inventory file format
- [**README.developer.md**](README.developer.md) — Architecture and internals
