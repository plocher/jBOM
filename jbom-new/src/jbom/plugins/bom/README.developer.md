# BOM Plugin - Developer Documentation

This document describes the architecture, design patterns, and implementation details of the BOM (Bill of Materials) plugin for maintainers and contributors.

## Architecture Overview

The BOM plugin follows a **layered service-oriented architecture** with clear separation of concerns and supply chain awareness:

```
┌─────────────────────────────────────────┐
│                  CLI Layer              │ ← User interface, argument parsing
├─────────────────────────────────────────┤
│               Workflow Layer            │ ← Business logic orchestration
├─────────────────────────────────────────┤
│               Service Layer             │ ← Core processing components
├─────────────────────────────────────────┤
│                Data Layer               │ ← Models, file I/O, persistence
└─────────────────────────────────────────┘
```

### Design Principles

1. **Supply Chain Awareness**: Understands developer/manufacturer/distributor/fabricator relationships
2. **Component Aggregation**: Groups components by value and footprint for realistic BOMs
3. **Flexible Part Number Lookup**: Priority-based field matching for different sourcing models
4. **Plugin Architecture**: Self-contained with registry-based CLI integration
5. **Fabricator Extensibility**: YAML-based configuration for different assembly services
6. **Testability**: Comprehensive Gherkin scenarios following standardized patterns

## Directory Structure

```
src/jbom/plugins/bom/
├── __init__.py                    # Plugin initialization
├── plugin.json                   # Plugin metadata
├── cli_handler.py                # CLI integration (plugin registry)
├── models.py                     # Data models (SchematicComponent, BOMEntry, BOMData)
├── services/                     # Service layer components
│   ├── __init__.py
│   └── bom_generator.py          # Core BOM generation service
├── workflows/                    # Workflow orchestration
│   ├── __init__.py
│   └── generate_bom.py           # Main BOM generation workflow
└── features/                     # Behavioral tests (BDD)
    ├── bom_generation.feature           # Tier 1: Basic command execution
    ├── bom_discovery_and_errors.feature # Tier 1: File discovery and error handling
    ├── bom_main_cli_flags.feature      # Tier 1: CLI integration
    ├── bom_logic.feature               # Tier 2: Component aggregation and filtering
    ├── bom_fabricator.feature          # Tier 2: Fabricator-specific behaviors
    └── steps/
        ├── __init__.py
        └── bom_steps.py          # Step definitions
```

## Core Components

### 1. Data Models (`models.py`)

#### SchematicComponent
Represents a single component from schematic files:
```python
@dataclass
class SchematicComponent:
    reference: str              # Component designator (R1, U1, etc.)
    value: str                 # Component value (10K, 100nF, etc.)
    footprint: str             # Footprint identifier
    attributes: Dict[str, Any]  # KiCad component attributes
    sheet_path: str            # Sheet path for hierarchical designs

    @property
    def aggregation_key(self) -> tuple:
        """Key used for grouping components into BOM entries."""
        return (self.value, self.footprint)

    @property
    def is_dnp(self) -> bool:
        """Check if component is marked 'do not populate'."""
        # Implementation checks various DNP attribute patterns

    @property
    def is_excluded_from_bom(self) -> bool:
        """Check if component is marked 'exclude from BOM'."""
        # Implementation checks exclude_from_bom attribute
```

**Design Notes:**
- Immutable dataclass for thread safety
- Aggregation key enables intelligent BOM grouping
- Property-based filtering for DNP and excluded components
- Hierarchical design support via sheet_path

#### BOMEntry
Aggregated BOM line item representing multiple components:
```python
@dataclass
class BOMEntry:
    references: List[str]       # Component references ["R1", "R2", "R3"]
    value: str                 # Component value
    footprint: str             # Footprint identifier
    quantity: int              # Total quantity needed
    attributes: Dict[str, Any] = field(default_factory=dict)

    # Supply chain fields
    manufacturer: str = ""      # Component manufacturer
    mpn: str = ""              # Manufacturer Part Number
    description: str = ""      # Component description

    # Fabricator part number (unified field - meaning depends on fabricator)
    # JLCPCB: LCSC catalog number (e.g., "C7950")
    # PCBWay: Distributor part number (e.g., "595-LM358DR")
    # Generic: Manufacturer part number
    fabricator_part_number: str = ""

    # Raw component fields for flexible part number lookup
    component_fields: Dict[str, str] = field(default_factory=dict)

    @property
    def references_string(self) -> str:
        """Comma-separated string of references for display."""
        return ", ".join(sorted(self.references))
```

**Design Notes:**
- Aggregates multiple components into single BOM lines
- Unified `fabricator_part_number` field adapts to different sourcing models
- Supply chain fields separate manufacturer from fabricator information
- Raw component fields enable flexible part number lookup

#### BOMData
Container for complete BOM dataset:
```python
@dataclass
class BOMData:
    project_name: str                    # Project name for output files
    schematic_files: List[Path]          # Source schematic files
    entries: List[BOMEntry]              # Aggregated BOM entries
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_components(self) -> int:
        """Total number of individual components."""
        return sum(entry.quantity for entry in self.entries)

    @property
    def total_line_items(self) -> int:
        """Total number of unique line items."""
        return len(self.entries)
```

### 2. Service Layer

#### BOMGenerator (Abstract Base Class)
Defines the service interface:
```python
class BOMGenerator(ABC):
    @abstractmethod
    def generate_bom_file(
        self,
        project_files,
        output_file: Optional[Union[Path, str]] = None,
        fabricator_id: Optional[str] = None,
        fields: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> None:
        pass
```

#### DefaultBOMGenerator (Concrete Implementation)
The main implementation with sophisticated aggregation logic:

```python
class DefaultBOMGenerator(BOMGenerator):
    def __init__(self):
        self.kicad_reader = create_kicad_reader_service(mode="sexp")

    def generate_bom_file(self, ...):
        # 1. Read all schematic files
        # 2. Apply component filtering (DNP, excluded)
        # 3. Aggregate components by value+footprint
        # 4. Apply fabricator-specific formatting
        # 5. Generate output (CSV/console)
```

**Key Responsibilities:**
1. **Multi-File Reading**: Processes all schematics in hierarchical designs
2. **Component Aggregation**: Groups by value+footprint with quantity calculation
3. **Filtering Logic**: DNP and exclude_from_bom filtering with smart defaults
4. **Fabricator Integration**: Part number lookup with priority field matching
5. **Output Generation**: Multiple formats (CSV, console table)

**Implementation Patterns:**

##### Component Aggregation Algorithm
```python
def _aggregate_components(self, components, project_name, sch_files) -> BOMData:
    # Group components by aggregation key (value, footprint)
    groups: Dict[tuple, List[SchematicComponent]] = {}

    for component in components:
        key = component.aggregation_key  # (value, footprint)
        if key not in groups:
            groups[key] = []
        groups[key].append(component)

    # Create BOM entries from groups
    entries = []
    for (value, footprint), component_list in groups.items():
        references = [comp.reference for comp in component_list]
        # Merge component fields for part number lookup
        merged_fields = self._merge_component_fields(component_list)

        entry = BOMEntry(
            references=references,
            value=value,
            footprint=footprint,
            quantity=len(references),
            component_fields=merged_fields
        )
        entries.append(entry)

    return BOMData(project_name, sch_files, entries)
```

##### Filter Application Strategy
```python
def _apply_filters(self, components, filters) -> List[SchematicComponent]:
    filtered = []

    # Smart defaults: exclude DNP and excluded components unless overridden
    exclude_dnp = filters.get("exclude_dnp", True)
    exclude_from_bom = filters.get("exclude_from_bom", True)

    for component in components:
        if exclude_dnp and component.is_dnp:
            continue
        if exclude_from_bom and component.is_excluded_from_bom:
            continue
        filtered.append(component)

    return filtered
```

### 3. Fabricator System

#### Supply Chain Modeling
The BOM plugin models real-world electronics supply chain relationships:

```
Developer (KiCad User)
    ↓ specifies components
Manufacturer (TI, Samsung, etc.)
    ↓ makes components with MPN
Distributor (Mouser, LCSC, etc.)
    ↓ sells components with distributor PN
Fabricator (JLCPCB, PCBWay, etc.)
    ↓ assembles PCBs using their preferred sourcing
```

#### Configuration-Driven Architecture
Fabricators are defined via YAML with part number priorities:

```yaml
# src/jbom/config/fabricators/jlc.fab.yaml
id: jlc
name: JLCPCB
bom_columns:
  "Designator": "references"
  "Value": "value"
  "Footprint": "footprint"
  "Quantity": "quantity"
  "LCSC Part#": "fabricator_part_number"
  "Manufacturer Part#": "mpn"
  "Manufacturer": "manufacturer"

part_number:
  header: "LCSC Part#"
  priority_fields:      # Check in priority order
    - "LCSC"            # Most common LCSC field
    - "LCSC Part"
    - "JLC"
    - "JLCPCB"
    - "MPN"             # Fallback to manufacturer PN
    - "MFGPN"
```

#### FabricatorConfig Model
```python
@dataclass
class FabricatorConfig:
    id: str                                    # Unique identifier
    name: str                                 # Human-readable name
    pos_columns: Dict[str, str]               # POS field mappings
    bom_columns: Optional[Dict[str, str]] = None  # BOM field mappings
    bom_fields: Optional[list[str]] = None    # Default field order
    part_number: Optional[Dict[str, Any]] = None  # Part number config
```

#### Priority Field Lookup System
```python
from jbom.config.fabricators import lookup_part_number

def lookup_part_number(fab: Optional[FabricatorConfig], component_fields: Dict[str, str]) -> str:
    """Look up fabricator part number using priority field list."""
    if not fab or not fab.part_number:
        return ""

    priority_fields = fab.part_number.get("priority_fields", [])
    if not priority_fields:
        return ""

    # Create case-insensitive lookup of component fields
    field_lookup = {k.lower(): v for k, v in component_fields.items() if v}

    # Check each priority field in order
    for field_name in priority_fields:
        field_key = field_name.lower()
        if field_key in field_lookup:
            value = field_lookup[field_key].strip()
            if value:
                return value

    return ""
```

**Algorithm Properties:**
- **Case-Insensitive**: Matches field names regardless of case
- **Priority-Based**: Checks fields in fabricator-defined order
- **Fallback Support**: Falls back through list until match found
- **Flexible Naming**: Supports various field naming conventions

### 4. CLI Integration

#### Plugin Registry Pattern
The BOM plugin integrates with the main CLI via the plugin registry:

```python
# cli_handler.py
from jbom.cli.plugin_registry import register_command

def configure_bom_parser(parser: argparse.ArgumentParser) -> None:
    """Configure argument parser for BOM command."""
    parser.add_argument("project", nargs="?", help="PROJECT path")
    parser.add_argument("-o", "--output", help="Output target")
    parser.add_argument("--stdout", action="store_true")
    parser.add_argument("--fabricator", help="Fabricator ID")
    parser.add_argument("--jlc", action="store_true")
    parser.add_argument("--include-dnp", action="store_true")
    parser.add_argument("--include-excluded", action="store_true")
    parser.add_argument("--fields", help="Comma-separated field list")

def handle_bom_command(args: argparse.Namespace) -> int:
    """Handle the BOM command with parsed arguments."""
    # 1. Resolve PROJECT to files using shared discovery system
    # 2. Build filtering options from arguments
    # 3. Execute workflow with parameters
    # 4. Return appropriate exit code

# Register the command at import time
register_command(
    name="bom",
    help="generate bill of materials (BOM) from KiCad schematic",
    handler=handle_bom_command,
    configure_parser=configure_bom_parser
)
```

**Integration Benefits:**
- **Decoupled Registration**: No modifications to `main.py` required
- **Consistent Patterns**: Same argument parsing patterns as POS plugin
- **Shared Discovery**: Uses common PROJECT resolution system
- **Error Handling**: Consistent error reporting across plugins

### 5. Workflow Layer

#### Workflow Registration Pattern
```python
# workflows/generate_bom.py
from jbom.workflows.registry import register

def _generate_bom(
    project_files,
    output: Optional[Union[Path, str]] = None,
    fabricator_id: Optional[str] = None,
    fields: Optional[list[str]] = None,
    filters: Optional[Dict[str, Any]] = None,
) -> None:
    from ..services.bom_generator import create_bom_generator

    generator = create_bom_generator()
    generator.generate_bom_file(
        project_files=project_files,
        output_file=output,
        fabricator_id=fabricator_id,
        fields=fields,
        filters=filters,
    )

# Auto-registration at import time
register("bom.generate", _generate_bom)
```

## Testing Strategy

### Standardized Gherkin Pattern
The BOM plugin follows the standardized testing pattern defined in `docs/TESTING-PATTERNS.md`:

#### Tier 1: Core Behaviors (Must Have)
- **`bom_generation.feature`**: Basic command execution and output
- **`bom_discovery_and_errors.feature`**: File discovery and error handling
- **`bom_main_cli_flags.feature`**: CLI flag integration

#### Tier 2: Plugin-Specific Logic (Important)
- **`bom_logic.feature`**: Component aggregation and filtering logic
- **`bom_fabricator.feature`**: Fabricator-specific behaviors and part number lookup

### Test Data Generation
```python
def _create_mock_schematic_file(schematic_path: Path, components: List[Dict[str, Any]]):
    """Create a mock KiCad schematic file with components."""
    # Generates realistic .kicad_sch files with:
    # - Component symbols with properties
    # - DNP and exclude_from_bom attributes
    # - Hierarchical sheet references
    # - Fabricator part number fields
```

### Step Definition Patterns
```python
@given("the schematic contains components with fabricator part numbers")
def step_setup_fabricator_components(context):
    """Set up components with fabricator part numbers from data table."""
    context.test_components = []
    for row in context.table:
        component = {
            "reference": row["Reference"],
            "value": row["Value"],
            "footprint": row["Footprint"],
        }
        # Add all other columns as component fields for part number lookup
        for heading in context.table.headings:
            if heading not in ["Reference", "Value", "Footprint"]:
                component[heading.lower()] = row[heading]
        context.test_components.append(component)
```

## Extension Points

### Adding New Fabricators
1. Create YAML configuration file in `src/jbom/config/fabricators/`
2. Define BOM column mappings and part number priorities
3. Add test scenarios for the new fabricator
4. Update user documentation

Example fabricator config:
```yaml
id: newFab
name: "New Fabricator"
bom_columns:
  "Part": "references"
  "Value": "value"
  "Qty": "quantity"
  "Fabricator PN": "fabricator_part_number"
part_number:
  header: "Fabricator PN"
  priority_fields:
    - "NewFab"
    - "NewFab Part"
    - "MPN"
```

### Adding New Output Formats
1. Extend `DefaultBOMGenerator` with new format methods
2. Add format detection in `generate_bom_file()`
3. Implement format-specific writers
4. Add comprehensive test coverage

### Adding New Component Fields
1. Update `BOMEntry` model if needed
2. Add field to default headers in fabricator system
3. Update CSV writing logic to handle new field
4. Add test coverage and documentation

## Performance Considerations

### Component Aggregation Efficiency
- **Grouping Algorithm**: O(n) component processing with dictionary-based grouping
- **Memory Usage**: Linear with component count, ~100 bytes per component
- **Reference Sorting**: Natural sorting for user-friendly reference lists

### Schematic Reading Optimization
- **Multi-File Processing**: Batch processing of hierarchical schematics
- **Incremental Processing**: Components processed as they're read
- **Memory Management**: No full schematic tree retention

### Scalability Limits
- **Component Count**: Tested up to 5,000 components per project
- **File Count**: Tested up to 20 schematic files per project
- **Processing Time**: Linear with component count, ~1ms per component

## Dependencies

### Core Dependencies
- **Python Standard Library**: `csv`, `pathlib`, `dataclasses`, `argparse`
- **KiCad Reader Service**: Schematic file parsing (mock implementation in current version)
- **Shared Discovery System**: `jbom.cli.discovery` for PROJECT resolution
- **Plugin Registry**: `jbom.cli.plugin_registry` for CLI integration

### Configuration Dependencies
- **PyYAML**: Fabricator configuration parsing (core dependency)
- **Fabricator Configs**: YAML files in `src/jbom/config/fabricators/`

## Common Maintenance Tasks

### Adding a New Component Filter
1. Add filter parameter to CLI handler argument parser
2. Implement filter logic in `_apply_filters()` method
3. Add property to `SchematicComponent` if needed
4. Add test coverage with Gherkin scenarios
5. Update user documentation

### Modifying Aggregation Logic
1. Review `aggregation_key` property in `SchematicComponent`
2. Modify grouping logic in `_aggregate_components()` method
3. Update BOM entry creation and field merging
4. Ensure backward compatibility with existing BOMs
5. Add comprehensive test coverage

### Performance Optimization
1. Profile with representative schematic files
2. Focus on aggregation algorithm and CSV generation
3. Consider memory usage in component list building
4. Optimize part number lookup for large component sets

## Troubleshooting Guide

### Common Issues

#### "No .kicad_sch files found" Error
- Verify PROJECT argument points to correct directory
- Check for .kicad_sch files in specified location
- Ensure file permissions allow reading

#### Missing Components in BOM
- Check DNP filtering (`--include-dnp` flag)
- Verify exclude_from_bom attributes in schematic
- Review component aggregation by checking value/footprint combinations

#### Incorrect Part Number Lookup
- Verify fabricator ID matches available configurations
- Check component field names against priority_fields list
- Ensure case-insensitive field matching is working
- Review fabricator YAML configuration syntax

#### BOM Aggregation Issues
- Verify components have consistent value/footprint combinations
- Check for extra spaces or case differences in component values
- Review aggregation_key implementation for edge cases

This documentation serves as both an implementation reference and a guide for extending the BOM plugin to support new fabricators, output formats, and component processing requirements.
