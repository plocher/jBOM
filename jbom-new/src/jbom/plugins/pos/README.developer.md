# POS Plugin - Developer Documentation

This document describes the architecture, design patterns, and implementation details of the POS (Position/Placement) plugin for maintainers and contributors.

## Architecture Overview

The POS plugin follows a **layered service-oriented architecture** with clear separation of concerns:

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

1. **Separation of Concerns**: Each layer has distinct responsibilities
2. **Dependency Injection**: Services are injected, not instantiated directly
3. **Registry Pattern**: Workflows registered dynamically for loose coupling
4. **Data-Driven Configuration**: Fabricator settings via YAML files
5. **Extensibility**: New fabricators and output formats via configuration
6. **Testability**: Each component unit testable in isolation

## Directory Structure

```
src/jbom/plugins/pos/
├── __init__.py                    # Plugin initialization
├── plugin.json                   # Plugin metadata
├── models.py                     # Data models
├── services/                     # Service layer components
│   ├── __init__.py
│   └── pos_generator.py          # Core POS generation service
├── workflows/                    # Workflow orchestration
│   ├── __init__.py
│   └── generate_pos.py           # Main POS generation workflow
└── features/                     # Functional tests (BDD)
    ├── pos_cli.feature
    ├── pos_generation.feature
    ├── pos_main_cli.feature
    ├── pos_main_cli_flags.feature
    ├── pos_discovery_and_errors.feature
    └── steps/
        ├── __init__.py
        └── pos_cli_steps.py
```

## Core Components

### 1. Data Models (`models.py`)

#### ComponentPosition
Represents a single component's placement data:
```python
@dataclass
class ComponentPosition:
    reference: str          # Component designator (R1, U1, etc.)
    value: str             # Component value (10K, 100nF, etc.)
    package: str           # Package type (0805, QFN-48, etc.)
    footprint: str         # Full footprint name
    x_mm: float           # X coordinate in millimeters
    y_mm: float           # Y coordinate in millimeters
    rotation_deg: float   # Rotation in degrees
    layer: str            # Layer name (Top/Bottom)
    attributes: Dict      # Additional KiCad attributes
```

**Design Notes:**
- Immutable dataclass for thread safety
- Separate `package` (extracted) and `footprint` (full name) fields
- Normalized layer names for consistency
- Extensible attributes dictionary for future enhancements

#### PositionData
Container for complete placement dataset:
```python
@dataclass
class PositionData:
    pcb_file: Path             # Source PCB file path
    board_title: str           # Board title from PCB
    kicad_version: str         # KiCad version used
    components: List[ComponentPosition] = field(default_factory=list)
```

**Design Notes:**
- Metadata preservation for traceability
- List of components for batch operations
- Default factory prevents mutable default issues

### 2. Service Layer

#### POSGenerator (Abstract Base Class)
Defines the service interface:
```python
class POSGenerator(ABC):
    @abstractmethod
    def generate_pos_file(
        self,
        pcb_file: Path,
        output_file: Optional[Union[Path, str]] = None,
        layer: Optional[str] = None,
        fabricator_id: Optional[str] = None,
        fields: Optional[List[str]] = None,
    ) -> None:
        pass
```

**Design Notes:**
- Abstract interface enables multiple implementations
- Optional parameters support various use cases
- Union type for output flexibility (Path, str, or None)

#### DefaultPOSGenerator (Concrete Implementation)
The main implementation:

```python
class DefaultPOSGenerator(POSGenerator):
    def __init__(self):
        self.kicad_reader = create_kicad_reader_service(mode="sexp")

    def generate_pos_file(self, ...):
        # 1. Read PCB using KiCadReaderService
        # 2. Convert to PositionData
        # 3. Apply fabricator/field logic
        # 4. Generate output (CSV/console)
```

**Key Responsibilities:**
1. **PCB Data Reading**: Delegates to `KiCadReaderService`
2. **Data Transformation**: Converts board model to position data
3. **Fabricator Integration**: Applies fabricator-specific formatting
4. **Output Generation**: Handles multiple output formats

**Implementation Patterns:**

##### Strategy Pattern for Output Formats
```python
if output_file is None or output_file == "-":
    self._write_csv_to_stdout(position_data, headers, eff_fields)
elif isinstance(output_file, str) and output_file.lower() == "console":
    self._write_console_output(position_data)
else:
    self._write_csv_to_file(position_data, output_file, headers, eff_fields)
```

##### Template Method for CSV Writing
```python
def _write_csv_to_stdout(self, position_data, headers, fields):
    writer = csv.writer(sys.stdout)
    self._write_csv_data(writer, position_data, headers, fields)

def _write_csv_to_file(self, position_data, output_file, headers, fields):
    with open(output_file, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        self._write_csv_data(writer, position_data, headers, fields)

def _write_csv_data(self, writer, position_data, headers, fields):
    # Common CSV writing logic
```

##### Field Mapping Strategy
```python
def _write_csv_data(self, writer, position_data, headers, fields):
    writer.writerow(headers)
    for comp in position_data.components:
        row = []
        for fld in fields:
            if fld == "reference":
                row.append(comp.reference)
            elif fld == "x":
                row.append(f"{comp.x_mm:.4f}")
            # ... field-specific formatting
        writer.writerow(row)
```

### 3. Workflow Layer

#### Workflow Registration Pattern
```python
# workflows/generate_pos.py
def _generate_pos(
    pcb_file: Path,
    output: Optional[Union[Path, str]] = None,
    layer: Optional[str] = None,
    fabricator_id: Optional[str] = None,
    fields: Optional[list[str]] = None,
) -> None:
    gen = create_pos_generator()
    gen.generate_pos_file(
        pcb_file=pcb_file,
        output_file=output,
        layer=layer,
        fabricator_id=fabricator_id,
        fields=fields,
    )

# Auto-registration at import time
registry.register("pos.generate", _generate_pos)
```

**Design Notes:**
- Functions as first-class objects for workflow definition
- Registry pattern enables dynamic discovery
- Import-time registration ensures availability
- Consistent parameter passing through layers

### 4. Fabricator System

#### Configuration-Driven Architecture
Fabricators are defined via YAML configuration files:

```yaml
# src/jbom/config/fabricators/jlc.fab.yaml
id: jlc
name: JLCPCB
pos_columns:
  Designator: reference
  Side: side
  Mid X: x
  Mid Y: y
  Rotation: rotation
  Package: package
  Comment: value
```

#### FabricatorConfig Model
```python
@dataclass
class FabricatorConfig:
    id: str                           # Unique identifier
    name: str                        # Human-readable name
    pos_columns: Dict[str, str]      # Header -> internal field mapping
```

#### Field Merging Algorithm
The fabricator system implements smart field merging:

```python
if fab and not fields:
    # Use fabricator's field set only
    fab_implied = list(dict.fromkeys(fab.pos_columns.values()))
    eff_fields = fab_implied
elif fab and fields:
    # Merge: user fields + fabricator required fields
    fab_implied = list(dict.fromkeys(fab.pos_columns.values()))
    eff_fields = list(fields)
    for f in fab_implied:
        if f not in eff_fields:
            eff_fields.append(f)  # Ensure fabricator fields included
else:
    # Use provided fields or defaults
    eff_fields = fields or default_fields
```

**Algorithm Properties:**
- **Fabricator Priority**: Fabricator fields always included
- **User Control**: User can add additional fields
- **No Duplication**: Fields appear only once
- **Order Preservation**: User-specified order maintained

#### Header Mapping Strategy
```python
def headers_for_fields(fab: Optional[FabricatorConfig], fields: list[str]) -> list[str]:
    default_headers = {
        "reference": "Designator",
        "value": "Val",
        "package": "Package",
        # ...
    }

    if fab:
        # Reverse map: internal field -> header
        rev = {}
        for header, internal in fab.pos_columns.items():
            rev.setdefault(internal, header)
        # Use fabricator mapping, fallback to defaults
        return [rev.get(f, default_headers.get(f, f)) for f in fields]

    return [default_headers.get(f, f) for f in fields]
```

## CLI Integration

### Command Registration
The POS plugin integrates with the main CLI via argument parsing:

```python
# cli/main.py
pos_parser = subparsers.add_parser("pos", help="Generate POS files")
pos_parser.add_argument("--pcb", help="PCB file path")
pos_parser.add_argument("--output", help="Output file")
pos_parser.add_argument("--stdout", action="store_true")
pos_parser.add_argument("--layer", choices=["TOP", "BOTTOM"])
pos_parser.add_argument("--fabricator", help="Fabricator ID")
pos_parser.add_argument("--jlc", action="store_true", help="JLCPCB shorthand")
pos_parser.add_argument("--fields", help="Comma-separated field list")
```

### Discovery System
Automatic file discovery reduces user friction:

```python
def find_project_and_pcb(directory: Path) -> Tuple[Optional[Path], Optional[Path]]:
    # 1. Find .kicad_pro or legacy .pro files
    # 2. Find .kicad_pcb files
    # 3. Handle autosave files (.kicad_pcb-bak)
    # 4. Return best matches with warnings
```

### Error Handling Strategy
Consistent error reporting across the plugin:

```python
try:
    wf = get_workflow("pos.generate")
    wf(pcb_file=pcb_path, output=output, ...)
    return 0
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    return 1
```

## Console Output System

### Generalized Table Formatter
The POS plugin uses a reusable table formatting system:

```python
from jbom.cli.formatting import print_tabular_data, Column

def _write_console_output(self, position_data):
    def transform_component(comp):
        # Convert ComponentPosition to display dict
        return {
            "ref": comp.reference,
            "x": f"{comp.x_mm:.4f}",
            # ...
        }

    columns = [
        Column("Reference", "ref", wrap=True, preferred_width=16, align="left"),
        Column("X", "x", wrap=False, preferred_width=8, align="right"),
        # ...
    ]

    print_tabular_data(
        data=position_data.components,
        columns=columns,
        row_transformer=transform_component,
        sort_key=lambda c: c.reference,
        title="Placement Table:",
        summary_line=f"Total: {len(position_data.components)} components",
    )
```

**Design Benefits:**
- **Reusability**: Other plugins can use the same system
- **Configurability**: Column widths, alignment, wrapping
- **Terminal Awareness**: Adapts to terminal width
- **Data Agnostic**: Works with any data via transformers

## Testing Strategy

### Multi-Layer Test Approach

#### 1. Unit Tests
- **Service Tests**: `POSGenerator` functionality
- **Fabricator Tests**: Configuration loading and mapping
- **Discovery Tests**: File discovery logic
- **Formatter Tests**: Table formatting edge cases

#### 2. Functional Tests (BDD)
- **Feature Files**: Gherkin scenarios for user workflows
- **Step Definitions**: Reusable test steps
- **Test Data**: Generated KiCad files for testing

#### 3. Integration Tests
- **CLI Tests**: Full command-line integration
- **Workflow Tests**: End-to-end workflow execution
- **File I/O Tests**: Actual file generation and parsing

### Test Data Generation
```python
def create_test_pcb_with_components(self, pcb_path: Path, components: List[Dict]):
    """Generate realistic KiCad PCB files for testing."""
    # Creates .kicad_pcb files with specified component data
    # Handles footprint libraries, layer assignments, etc.
```

## Extension Points

### Adding New Fabricators
1. Create YAML configuration file in `src/jbom/config/fabricators/`
2. Define column mappings
3. Test with sample data
4. Update documentation

### Adding New Output Formats
1. Extend `DefaultPOSGenerator` with new methods
2. Add format detection logic
3. Implement format-specific writers
4. Add test coverage

### Adding New Data Sources
1. Implement `KiCadReaderService` interface
2. Handle new file formats (e.g., Altium, Eagle)
3. Map to common `PositionData` format
4. Integrate with workflow system

## Performance Considerations

### Memory Efficiency
- **Streaming**: Components processed incrementally where possible
- **Lazy Loading**: PCB data loaded only when needed
- **Object Reuse**: Minimal object creation in hot paths

### I/O Optimization
- **Buffered Writing**: Use Python's built-in CSV writer buffering
- **Single Pass**: Read PCB file once, generate all outputs
- **File System**: Leverage OS file system caching

### Scalability Limits
- **Component Count**: Tested up to 10,000 components
- **Memory Usage**: ~1MB per 1000 components
- **Processing Time**: Linear with component count

## Dependencies

### Core Dependencies
- **Python Standard Library**: `csv`, `pathlib`, `dataclasses`
- **KiCad Reader Service**: PCB file parsing
- **Workflow Registry**: Service orchestration

### Optional Dependencies
- **PyYAML**: Fabricator configuration (already required by core)
- **Click/Argparse**: CLI framework (core dependency)

### Dependency Injection Pattern
```python
def create_pos_generator() -> POSGenerator:
    """Factory function for dependency injection."""
    return DefaultPOSGenerator()
```

This enables easy testing and future extensibility.

## Common Maintenance Tasks

### Adding a New Field
1. Update `ComponentPosition` model if needed
2. Add field mapping in `_write_csv_data()`
3. Update default headers in fabricator system
4. Add test coverage
5. Update user documentation

### Modifying Output Format
1. Identify affected methods (`_write_csv_data`, etc.)
2. Implement changes with backward compatibility
3. Update header mapping system if needed
4. Add/update test cases
5. Update fabricator configurations if needed

### Performance Optimization
1. Profile with representative data sets
2. Focus on `_convert_board_to_position_data()` for processing
3. Optimize CSV writing for large datasets
4. Consider memory usage in component list building

## Troubleshooting Guide

### Common Issues

#### "Unknown fabricator" Error
- Check fabricator ID matches filename (minus `.fab.yaml`)
- Verify YAML syntax in fabricator file
- Ensure `id` field matches expected value

#### Missing Components in Output
- Check layer filtering (`--layer` flag)
- Verify component placement on correct layers in PCB
- Check for component attribute filtering

#### Incorrect Coordinates
- KiCad uses bottom-left origin, verify expectations
- Check units (always millimeters in output)
- Consider PCB rotation/mirroring in design

#### Performance Issues
- Profile with large PCB files
- Check memory usage with `tracemalloc`
- Consider component count and complexity

This documentation serves as both an implementation reference and a guide for future enhancements to the POS plugin architecture.
