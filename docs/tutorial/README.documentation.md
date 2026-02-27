# Documentation Tutorial: Maintaining Project Documentation

This tutorial demonstrates how to maintain jBOM's documentation when adding new services, ensuring consistency with the project's architectural approach and user needs.

## Documentation Philosophy

jBOM documentation serves different audiences with different needs:

- **README Files**: High-level architectural overview for experienced developers
- **Tutorial Series**: Step-by-step development guide with practical examples
- **API Documentation**: Service interfaces and domain models
- **User Documentation**: CLI usage and workflow guides
- **CHANGELOG**: Version-aware change tracking

## Documentation Update Process

When adding new functionality like the POS service, update documentation in this order:

1. **CHANGELOG** - Record user-visible changes
2. **CLI Help** - Update command documentation
3. **Service Documentation** - Document new domain services
4. **Architecture Documentation** - Update system overviews
5. **Tutorial Documentation** - Add practical examples

## Step 1: Update CHANGELOG

Document user-visible changes in `docs/CHANGELOG.md`:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - 2024-01-19

### Added
- **POS Command**: New `jbom pos` command for generating component placement files
  - Generate pick-and-place CSV files from KiCad PCB data
  - Filter by SMD components only with `--smd-only`
  - Filter by board layer with `--layer TOP|BOTTOM`
  - Support both metric (mm) and imperial (inch) units
  - Output to file, stdout, or console table format
- **PCB Reader Service**: New domain service for reading KiCad PCB files
  - Extract component placement data from .kicad_pcb files
  - Support for both S-expression and pcbnew API parsing modes
  - Comprehensive footprint and placement information extraction

### Enhanced
- **Common Types**: Added PCB-specific domain models
  - `BoardModel` entity for PCB board representation
  - `PcbComponent` entity for component placement data
  - `PlacementOptions` configuration object for POS generation

### Developer Experience
- **Tutorial Series**: Added comprehensive developer tutorials
  - Context tutorial explaining jBOM's design patterns
  - Implementation tutorial for TDD service development
  - Integration tutorial for CLI adapter patterns
  - Documentation tutorial for maintaining project docs
```

**Key Insight**: CHANGELOG focuses on user impact and feature capabilities, not implementation details.

## Step 2: Update CLI Help Documentation

Ensure CLI help text is comprehensive and user-focused:

```python
def register_command(subparsers) -> None:
    """Register pos command with comprehensive help documentation."""
    parser = subparsers.add_parser(
        "pos",
        help="Generate component placement files from KiCad PCB",
        description="""
        Generate component placement (pick-and-place) files from KiCad PCB data.
        Output includes component reference, coordinates, rotation, side, and package info.
        Suitable for manufacturing and assembly processes.
        """,
        epilog="""
        Examples:
          jbom pos board.kicad_pcb                    # CSV to stdout
          jbom pos board.kicad_pcb -o placement.csv  # Save to file
          jbom pos board.kicad_pcb -o console        # Console table
          jbom pos board.kicad_pcb --smd-only        # SMD components only
          jbom pos board.kicad_pcb --layer TOP       # Top layer only
          jbom pos board.kicad_pcb --units inch      # Imperial units
        """
    )

    # Detailed argument help
    parser.add_argument(
        "pcb",
        help="Path to .kicad_pcb file"
    )
    parser.add_argument(
        "-o", "--output",
        help='Output destination: file path, "stdout" for piping, "console" for table display'
    )
    parser.add_argument(
        "--smd-only",
        action="store_true",
        help="Include only surface-mount (SMD) components, exclude through-hole"
    )
    parser.add_argument(
        "--layer",
        choices=["TOP", "BOTTOM"],
        help="Include only components on specified board layer"
    )
    parser.add_argument(
        "--units",
        choices=["mm", "inch"],
        default="mm",
        help="Coordinate units in output (default: mm)"
    )
```

**Key Insight**: CLI help should include practical examples and explain business value, not just technical parameters.

## Step 3: Service Documentation Updates

Update service documentation to reflect new capabilities in `src/jbom/services/README.md`:

```markdown
## Service Domain Boundaries

### [`pos_generator.py`](pos_generator.py) - Position File Domain
**Bounded Context**: Manufacturing placement file generation
**Domain Concepts**: Pick-and-Place Data, Manufacturing Coordinates, Assembly Information
**Core Operations**:
- Generate manufacturing placement data from PCB component information
- Apply coordinate system transformations for different manufacturing standards
- Filter components based on manufacturing requirements (SMD vs through-hole, layer)
- Format placement data for various manufacturing file formats

**Business Rules**:
- SMD components use surface-mount assembly processes
- Coordinate origins may be board-based or auxiliary-based depending on manufacturer
- Rotation angles normalized to manufacturing-standard ranges (0-360°)
- Layer designation follows industry standards (TOP/BOTTOM vs F.Cu/B.Cu)

### [`pcb_reader.py`](pcb_reader.py) - PCB Layout Domain
**Bounded Context**: Component placement and physical layout data extraction
**Domain Concepts**: Board Layout, Component Placement, Physical Footprints, Layer Information
**Core Operations**:
- Extract component placement information from KiCad PCB files
- Parse footprint data and convert to domain objects
- Handle coordinate system interpretation from design files
- Validate PCB file format and structural integrity

**Integration Points**:
- Provides placement data to POS Generator service
- Supplies component information to BOM enhancement workflows
- Integrates with common PCB parsing utilities
```

**Key Insight**: Service documentation focuses on business domain and integration points, not implementation details.

## Step 4: Update Architecture Documentation

Reflect new services in `src/README.md`:

```markdown
## Service Composition Workflows

**Enhanced Workflow** (multiple service collaboration):
```python
# PCB-based workflows
pcb_reader = PCBReader()
pos_generator = POSGenerator(placement_options)
bom_enhancer = BOMEnhancer(enhancement_strategy)

# Extract placement and component data
board_model = pcb_reader.read_pcb_file(pcb_path)
placement_data = pos_generator.generate_pos_data(board_model)
enhanced_bom = bom_enhancer.correlate_placement_with_bom(placement_data, bom_data)
```

**Cross-Domain Integration**:
```python
# Services spanning multiple bounded contexts
schematic_reader = SchematicReader()
pcb_reader = PCBReader()
correlator = SchematicPCBCorrelator()

# Integrate schematic and layout data
schematic = schematic_reader.read_schematic(sch_path)
board = pcb_reader.read_pcb_file(pcb_path)
correlated_data = correlator.correlate_design_data(schematic, board)
```
```

**Key Insight**: Architecture documentation shows how new services fit into existing patterns and collaboration workflows.

## Step 5: Update CLI Documentation

Update `src/jbom/cli/README.md` to include new command patterns:

```markdown
### [`pos.py`](pos.py) - Position File Command Adapter
**Interface**: `jbom pos <pcb> [options]`
**Adaptation Responsibilities**:
- CLI placement options → `PlacementOptions` domain configuration
- PCB domain services orchestration for manufacturing workflows
- Placement data → Manufacturing file formats (CSV, console table)
- PCB processing exceptions → User-friendly manufacturing error messages

**Domain Services Used**:
- `PCBReader` - Extract component placement from PCB files
- `POSGenerator` - Generate manufacturing placement data
- `CoordinateTransformer` - Handle manufacturing coordinate systems
- `OutputFormatter` - Present placement data in various formats

**Command Workflows**:
```python
def handle_pos(args):
    """Manufacturing placement workflow orchestration."""
    # Input translation: CLI → Domain
    placement_options = PlacementOptions(
        units=args.units,
        smd_only=args.smd_only,
        layer_filter=args.layer
    )

    # Service orchestration: Manufacturing workflow
    pcb_reader = PCBReader()
    pos_generator = POSGenerator(placement_options)

    board = pcb_reader.read_pcb_file(args.pcb_file)
    placement_data = pos_generator.generate_pos_data(board)

    # Output adaptation: Domain → CLI formats
    return present_placement_results(placement_data, args.output)
```
```

**Key Insight**: CLI documentation emphasizes orchestration patterns and interface adaptation responsibilities.

## Step 6: Common Types Documentation

Update `src/jbom/common/README.md` with new domain models:

```markdown
### PCB Domain Models ([`pcb_types.py`](pcb_types.py))
**Pattern**: PCB layout and manufacturing domain entities
**Bounded Context**: Physical board design and component placement

```python
@dataclass
class BoardModel:
    """Domain Entity: PCB board with comprehensive component placement data.

    Represents the physical board design including all placed components,
    board metadata, and manufacturing-relevant information.
    """
    path: Path                                    # Design file location
    title: str = ""                              # Board project title
    kicad_version: str = ""                      # Design tool version
    footprints: List[PcbComponent] = field(default_factory=list)

    @property
    def component_count(self) -> int:
        """Business query: Total number of placed components."""
        return len(self.footprints)

    @property
    def smd_component_count(self) -> int:
        """Business query: Count of surface-mount components."""
        return sum(1 for fp in self.footprints if fp.is_smd)

@dataclass
class PlacementOptions:
    """Configuration Value Object: Manufacturing placement generation options.

    Captures manufacturing-specific requirements and coordinate system
    preferences for placement file generation.
    """
    units: str = "mm"                           # Manufacturing coordinate units
    origin: str = "board"                       # Coordinate system reference
    smd_only: bool = False                      # Assembly process filter
    layer_filter: Optional[str] = None          # Manufacturing layer selection

    def __post_init__(self):
        """Domain validation: Manufacturing constraint validation."""
        if self.units not in ("mm", "inch"):
            raise ValueError("Manufacturing units must be 'mm' or 'inch'")
        if self.origin not in ("board", "aux"):
            raise ValueError("Origin must be 'board' or 'aux' reference")
```
```

**Key Insight**: Domain model documentation emphasizes business meaning and manufacturing context over technical implementation.

## Step 7: User Documentation

Create user-focused documentation in `docs/README.md`:

```markdown
# jBOM User Guide

## Position File Generation

Generate component placement files for PCB manufacturing and assembly.

### Basic Usage

```bash
# Generate placement CSV to stdout
jbom pos board.kicad_pcb

# Save placement data to file
jbom pos board.kicad_pcb -o placement.csv

# View placement data as formatted table
jbom pos board.kicad_pcb -o console
```

### Manufacturing Workflows

**SMD Assembly Process**:
```bash
# Generate SMD-only placement for surface-mount assembly
jbom pos board.kicad_pcb --smd-only -o smd_placement.csv
```

**Layer-Specific Assembly**:
```bash
# Top layer placement for first assembly pass
jbom pos board.kicad_pcb --layer TOP -o top_placement.csv

# Bottom layer placement for second assembly pass
jbom pos board.kicad_pcb --layer BOTTOM -o bottom_placement.csv
```

**Imperial Units for US Manufacturers**:
```bash
# Generate placement with imperial coordinates
jbom pos board.kicad_pcb --units inch -o placement_imperial.csv
```

### Integration with Manufacturing Tools

The generated CSV format is compatible with most pick-and-place machines:

| Column | Description | Format |
|--------|-------------|--------|
| Reference | Component designator | R1, C5, U3 |
| X(mm/in) | X coordinate | Decimal degrees |
| Y(mm/in) | Y coordinate | Decimal degrees |
| Rotation | Component rotation | 0.0-360.0 degrees |
| Side | Board layer | TOP, BOTTOM |
| Footprint | Component footprint | Library:Package |
| Package | Package type | 0805, SOIC-8, QFN-32 |
```

**Key Insight**: User documentation focuses on practical workflows and manufacturing integration, not technical architecture.

## Step 8: Testing Documentation

Update testing approach in `tests/README.md`:

```markdown
## Service Testing Strategy

### POS Service Testing (`tests/services/test_pos_generator.py`)

**Domain Logic Testing**:
- Component filtering business rules (SMD-only, layer-specific)
- Coordinate transformation accuracy
- Manufacturing data format validation
- Configuration validation and error handling

**Integration Testing** (`tests/integration/test_pos_workflow.py`):
- PCB Reader → POS Generator service composition
- End-to-end placement data generation workflows
- Error propagation between services

### CLI Testing Strategy

**Command Integration Testing** (`tests/cli/test_pos_command.py`):
- CLI argument translation to domain configuration
- Service orchestration verification
- Output format validation (CSV, console, file)
- Error message translation and user feedback

**Functional Testing** (`features/pos/`):
- Complete user workflow validation
- Real KiCad PCB file processing
- Manufacturing file format compliance
- Cross-platform compatibility verification
```

## Step 9: Maintenance Guidelines

Establish documentation maintenance patterns:

```markdown
# Documentation Maintenance Guidelines

## When Adding New Services

1. **Update CHANGELOG** with user-facing functionality
2. **Add CLI help** with practical examples
3. **Document service boundaries** and domain responsibilities
4. **Update architecture diagrams** showing service relationships
5. **Add user workflow examples** for common use cases
6. **Create tutorial content** for complex integration patterns

## Documentation Review Criteria

**Architecture Documentation**:
- [ ] Service responsibilities clearly defined
- [ ] Domain boundaries and integration points documented
- [ ] Design patterns and architectural constraints explained
- [ ] Code examples show architectural principles

**User Documentation**:
- [ ] Common workflows with practical examples
- [ ] Clear error messages and troubleshooting guidance
- [ ] Integration examples with external tools
- [ ] Performance and compatibility considerations

**Developer Documentation**:
- [ ] TDD workflow examples with real code
- [ ] Testing strategies for each architectural layer
- [ ] Extension points and customization guidance
- [ ] Contributing guidelines and code standards
```

## Documentation Benefits

**Architectural Clarity**: Clear service boundaries and integration patterns
**Developer Onboarding**: Practical tutorials with working examples
**User Adoption**: Workflow-focused documentation with real use cases
**Maintainability**: Consistent documentation patterns across all components

The documentation approach ensures that jBOM's architectural principles are clearly communicated while providing practical guidance for both users and developers extending the system.
