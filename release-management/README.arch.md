# jBOM Architecture (Dec 2025)
This document summarizes the current high-level module layout supporting both BOM generation and PCB placement extraction.

## Packages

### Core Modules
- `jbom.jbom` — main implementation (schematic parsing, inventory matcher, BOM generator). Source of truth for schematic functionality.
- `jbom.cli` — command-line interface with subcommands:
  - `jbom.cli.main` → CLI parsing, `bom` and `pos` subcommands

### Schematic Module
- `jbom.sch` — schematic-focused API that re-exports from `jbom.jbom` for convenience

### PCB Module (NEW)
- `jbom.pcb` — PCB integration for placement file generation:
  - `jbom.pcb.board_loader` → `BoardLoader` (pcbnew API + S-expression parser)
  - `jbom.pcb.model` → `Board`, `BoardComponent` data models
  - `jbom.pcb.position` → `PositionGenerator` (CPL/POS file generation)

### Shared Utilities
- `jbom.common` — shared helpers for both schematic and PCB:
  - `fields` → field name normalization (`normalize_field_name`, `field_to_header`)
  - `types` → common enums and types (`ComponentType`, `DiagnosticIssue`, etc.)
  - `packages` → package lists (`SMD_PACKAGES`, `THROUGH_HOLE_PACKAGES`)
  - `values` → numeric parsers for RES/CAP/IND (`parse_res_to_ohms`, `farad_to_eia`, etc.)
  - `utils` → utility functions (currently placeholder)

### Inventory Module
- `jbom.inventory` — inventory matching API that re-exports from `jbom.jbom` for convenience

## Command-Line Interface

New subcommand-based CLI (breaking change from v1.x):

```bash
# BOM generation
python -m jbom bom PROJECT -i INVENTORY [OPTIONS]

# Placement generation
python -m jbom pos BOARD.kicad_pcb -o OUTPUT.csv [OPTIONS]
```

Both subcommands support:
- `--jlc` flag for JLCPCB-optimized field presets
- `-f/--fields` for custom field selection
- Field presets with `+` prefix (`+standard`, `+jlc`, `+minimal`, `+all`)

## API Usage

### BOM Generation
```python
# Standard import
from jbom import generate_bom_api, GenerateOptions

opts = GenerateOptions(verbose=True)
result = generate_bom_api('project/', 'inventory.xlsx', options=opts)
```

### Placement Generation (New)
```python
from jbom.pcb import BoardLoader, PositionGenerator

# Load board with auto-detection
board = BoardLoader.load('board.kicad_pcb', mode='auto')

# Generate placement file
gen = PositionGenerator(board)
gen.write_csv('output.csv',
              fields_preset='jlc',
              units='mm',
              origin='aux')
```

## Compatibility

### Maintained Compatibility
- Public API imports continue to work: `from jbom import generate_bom_api`
- Python library API unchanged for BOM generation
- KiCad Eeschema plugin wrapper unchanged

### Breaking Changes
- CLI completely redesigned with subcommands (v1.x → v2.x)
- Old CLI syntax no longer supported
- Must use `jbom bom` instead of `jbom` directly

## Design Patterns

### Dual-Mode Loading
Both schematic and PCB modules support flexible loading:
- Schematic: Auto-detects hierarchical roots vs. individual sheets
- PCB: Auto-detects pcbnew API availability, falls back to S-expression parser

### Field System
- Case-insensitive field names throughout
- Preset system with `+` prefix for common configurations
- Custom field selection with comma-separated lists
- I:/C: prefix system for disambiguating inventory vs. component fields (BOM)

### Output Flexibility
- Multiple output formats via presets
- Extensible column selection
- JLCPCB-specific optimizations
- Manufacturer-agnostic default formats

## Future Development

### Planned Enhancements
- PCB consistency checker (compare schematic vs. PCB footprints)
- Pcbnew Action Plugin for in-editor placement generation
- Board visualization and component highlighting
- Advanced placement validation (clearances, off-board components)

### Extension Points
- Additional placement format presets
- Custom coordinate transformations
- Integration with other fabrication workflows
- Advanced filtering and grouping options
