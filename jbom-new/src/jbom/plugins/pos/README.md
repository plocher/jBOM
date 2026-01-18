# POS Plugin - User Manual

The POS (Position/Placement) plugin generates component placement files from KiCad PCB designs. These files are commonly used by pick-and-place machines and PCB assembly services.

## Quick Start

```bash
# Generate POS file for current project
jbom pos

# Generate POS file for specific project directory
jbom pos /path/to/my_project

# Generate POS file by project basename
jbom pos my_project

# Generate POS file for specific PCB
jbom pos my_board.kicad_pcb

# Output to stdout as CSV
jbom pos --stdout

# Generate for JLCPCB assembly
jbom pos --jlc --output assembly.csv
```

## Command Overview

```
jbom pos [PROJECT] [OPTIONS]
```

### PROJECT Argument

The PROJECT argument can be:
- **Directory**: Path to directory containing .kicad_pro file
- **Project basename**: Name of .kicad_pro file (without extension)
- **Specific file**: Path to .kicad_pcb or .kicad_sch file
- **Omitted**: Uses current directory

### Basic Options

| Option | Description | Example |
|--------|-------------|---------|
| `-o, --output PATH` | Output file path | `--output placement.csv` |
| `--stdout` | Write CSV to stdout | `--stdout` |

### Filtering Options

| Option | Description | Values | Example |
|--------|-------------|--------|---------|
| `--layer LAYER` | Include only components on specified layer | `TOP`, `BOTTOM` | `--layer TOP` |
| `--smd-only` | Include only SMD components (exclude through-hole) | - | `--smd-only` |
| `--include-dnp` | Include DNP components (excluded by default) | - | `--include-dnp` |
| `--include-excluded` | Include components marked 'exclude from POS' (excluded by default) | - | `--include-excluded` |

**Default Behavior**: Components marked as "do not populate" (DNP) or "exclude from POS" in KiCad are automatically excluded unless override flags are used.

### Fabricator Options

| Option | Description | Example |
|--------|-------------|---------|
| `--fabricator ID` | Use fabricator-specific format | `--fabricator jlc` |
| `--jlc` | Shorthand for JLCPCB format | `--jlc` |
| `--fields LIST` | Custom field selection | `--fields reference,x,y,rotation` |

### Output Format Options

| Option | Description | Result |
|--------|-------------|--------|
| (default) | CSV file in project directory | `project.pos.csv` |
| `--stdout` | CSV data to stdout | Pipe to other tools |
| `--output console` | Human-readable table | Terminal display |

## Usage Examples

### Basic Usage

Generate a standard POS file in the current directory:
```bash
# Discovers project automatically
jbom pos
# Creates: MyProject.pos.csv
```

Generate POS for a specific project:
```bash
# By directory
jbom pos /path/to/MyProject

# By project basename
jbom pos MyProject

# By specific PCB file
jbom pos MyProject.kicad_pcb
```

### Fabricator-Specific Output

Generate placement file formatted for JLCPCB:
```bash
jbom pos --jlc --output jlcpcb_placement.csv
```

This uses JLCPCB's column headers:
- `Designator` (component reference)
- `Side` (TOP/BOTTOM)
- `Mid X`, `Mid Y` (coordinates)
- `Rotation` (degrees)
- `Package` (footprint package)
- `Comment` (component value)

### Component Filtering

Generate placement file for only top-side components:
```bash
jbom pos --layer TOP --output top_components.csv
```

Include only SMD components (exclude through-hole):
```bash
jbom pos --smd-only --output smd_only.csv
```

Include DNP components (normally excluded):
```bash
jbom pos --include-dnp --output with_dnp.csv
```

Include components marked "exclude from POS":
```bash
jbom pos --include-excluded --output complete.csv
```

Combine multiple filters:
```bash
jbom pos --layer TOP --smd-only --jlc
# Generates only top-layer SMD components for JLCPCB
# (DNP and excluded components automatically omitted)
```

### Custom Fields

Specify exactly which fields to include:
```bash
jbom pos --fields reference,x,y,footprint --stdout
```

Available fields:
- `reference` - Component designator (R1, U1, etc.)
- `value` - Component value (10K, 100nF, etc.)
- `package` - Package type (0805, QFN-48, etc.)
- `footprint` - Full footprint name
- `x`, `y` - Coordinates in mm
- `rotation` - Rotation in degrees
- `side` - Layer (TOP/BOTTOM)
- `smd` - Mount type (SMD/THT)

### Field Merging with Fabricators

When using both `--fabricator` and `--fields`, fabricator-required fields are automatically included:

```bash
jbom pos --jlc --fields reference,footprint
# Output includes: reference, footprint, side, x, y, rotation, package, value
# (JLCPCB required fields automatically added)
```

### Pipeline Integration

Use with other command-line tools:
```bash
# Count components by package type
jbom pos --stdout | cut -d, -f3 | sort | uniq -c

# Filter for specific components
jbom pos --stdout | grep "^U[0-9]" > ics_only.csv

# Convert to different format
jbom pos --stdout | python my_converter.py > custom_format.txt
```

### Human-Readable Output

View placement data in formatted table:
```bash
jbom pos --output console
```

Example output:
```
Placement Table:
================
Reference | X      | Y      | Rotation | Side | Footprint     | SMD
----------+--------+--------+----------+------+---------------+----
C1        | 2.5400 | 3.8100 |      0.0 | TOP  | C_0603_1608   | SMD
R1        | 5.0800 | 7.6200 |     90.0 | TOP  | R_0805_2012   | SMD
U1        | 0.0000 | 0.0000 |      0.0 | TOP  | QFN-48_7x7mm  | SMD

Total: 3 components
```

## Supported Fabricators

### JLCPCB (`jlc`)
- **Columns**: Designator, Side, Mid X, Mid Y, Rotation, Package, Comment
- **Usage**: `--jlc` or `--fabricator jlc`
- **Format**: Standard JLCPCB assembly service format

### Adding New Fabricators
To request support for additional fabricators, create an issue with:
1. Fabricator name
2. Required column headers
3. Field mappings
4. Sample file format

## File Discovery

The POS plugin automatically discovers KiCad files in the current directory:

1. **PCB File**: Looks for `*.kicad_pcb` files
2. **Project File**: Looks for `*.kicad_pro` or legacy `*.pro` files
3. **Output Name**: Uses project name if available, otherwise PCB filename

Example discovery:
```
MyProject/
├── MyProject.kicad_pro  ← Project file (used for naming)
├── MyProject.kicad_pcb  ← PCB file (source data)
└── MyProject.pos.csv    ← Generated output
```

## Error Handling

Common errors and solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| `No .kicad_pcb file found` | No PCB file in directory | Specify `--pcb` or run in correct directory |
| `PCB file not found: path` | Invalid PCB path | Check file path and permissions |
| `Unknown fabricator: name` | Invalid fabricator ID | Use `--fabricator jlc` or check available IDs |

## Output Formats

### CSV Format (Default)
Standard comma-separated values with headers. Default columns:
```csv
Designator,Val,Package,Mid X,Mid Y,Rotation,Layer
U1,MCU,QFN,0.0000,0.0000,0.0,TOP
```

### Fabricator CSV
Custom column headers and field ordering per fabricator requirements.

### Console Format
Human-readable table with automatic column sizing and alignment.

## Integration Notes

- **Units**: All coordinates are in millimeters
- **Origin**: KiCad coordinate system (bottom-left origin)
- **Rotation**: Degrees, typically 0, 90, 180, 270
- **Layer Names**: Normalized to "TOP"/"BOTTOM"
- **Encoding**: UTF-8 output encoding
- **Line Endings**: System-appropriate (LF on Unix, CRLF on Windows)

## Performance

- **Small boards** (< 100 components): < 1 second
- **Large boards** (1000+ components): < 5 seconds
- **Memory usage**: Minimal, processes components incrementally

## Related Commands

- `jbom plugin --list` - List all available plugins
- `jbom --help` - General help
- `jbom pos --help` - POS-specific help
