# BOM Plugin - User Manual

The BOM (Bill of Materials) plugin generates component lists from KiCad schematic designs. These files are used for component procurement, cost analysis, and PCB assembly planning.

## Quick Start

```bash
# Generate BOM for current project
jbom bom

# Generate BOM for specific project directory
jbom bom /path/to/my_project

# Generate BOM by project basename
jbom bom my_project

# Generate BOM for specific schematic
jbom bom my_board.kicad_sch

# Output to stdout as CSV
jbom bom --stdout

# Generate for JLCPCB assembly with part numbers
jbom bom --jlc --output assembly_bom.csv
```

## Command Overview

```
jbom bom [PROJECT] [OPTIONS]
```

### PROJECT Argument

The PROJECT argument can be:
- **Directory**: Path to directory containing .kicad_pro file
- **Project basename**: Name of .kicad_pro file (without extension)
- **Specific file**: Path to .kicad_sch file
- **Omitted**: Uses current directory

The system automatically discovers all related schematic files in hierarchical designs.

### Basic Options

| Option | Description | Example |
|--------|-------------|---------|
| `-o, --output PATH` | Output file path | `--output bom.csv` |
| `--stdout` | Write CSV to stdout | `--stdout` |

### Filtering Options

| Option | Description | Example |
|--------|-------------|---------|
| `--include-dnp` | Include DNP components (excluded by default) | `--include-dnp` |
| `--include-excluded` | Include components marked 'exclude from BOM' (excluded by default) | `--include-excluded` |

**Default Behavior**: Components marked as "do not populate" (DNP) or "exclude from BOM" in KiCad are automatically excluded unless override flags are used.

### Fabricator Options

| Option | Description | Example |
|--------|-------------|---------|
| `--fabricator ID` | Use fabricator-specific format | `--fabricator jlc` |
| `--jlc` | Shorthand for JLCPCB format | `--jlc` |
| `--fields LIST` | Custom field selection | `--fields references,value,quantity,fabricator_part_number` |

### Output Format Options

| Option | Description | Result |
|--------|-------------|--------|
| (default) | CSV file in project directory | `project.bom.csv` |
| `--stdout` | CSV data to stdout | Pipe to other tools |
| `--output console` | Human-readable table | Terminal display |

## Usage Examples

### Basic Usage

Generate a standard BOM in the current directory:
```bash
# Discovers project automatically
jbom bom
# Creates: MyProject.bom.csv
```

Generate BOM for a specific project:
```bash
# By directory
jbom bom /path/to/MyProject

# By project basename
jbom bom MyProject

# By specific schematic file
jbom bom MyProject.kicad_sch
```

### Fabricator-Specific Output

Generate BOM formatted for JLCPCB with part numbers:
```bash
jbom bom --jlc --output jlcpcb_bom.csv
```

This uses JLCPCB's column headers and includes LCSC part number lookup:
- `Designator` (component references)
- `Value` (component value)
- `Footprint` (component footprint)
- `Quantity` (total quantity needed)
- `LCSC Part#` (JLCPCB/LCSC catalog number)
- `Manufacturer Part#` (original manufacturer part number)
- `Manufacturer` (component manufacturer)

Generate BOM formatted for PCBWay with distributor part numbers:
```bash
jbom bom --fabricator pcbway --output pcbway_bom.csv
```

PCBWay format uses distributor part numbers directly:
- `Designator` (component references)
- `Value` (component value)
- `Package` (component package)
- `Quantity` (total quantity)
- `Distributor Part Number` (Mouser, Digi-Key, etc.)

### Component Filtering

Include DNP components (normally excluded):
```bash
jbom bom --include-dnp --output with_dnp.csv
```

Include components marked "exclude from BOM":
```bash
jbom bom --include-excluded --output complete.csv
```

Combine filtering options:
```bash
jbom bom --include-dnp --include-excluded --jlc
# Generates complete BOM including all components for JLCPCB
```

### Custom Fields

Specify exactly which fields to include:
```bash
jbom bom --fields references,value,quantity,fabricator_part_number --stdout
```

Available fields:
- `references` - Component designators (R1,R2,R3)
- `value` - Component value (10K, 100nF, etc.)
- `footprint` - Footprint name (R_0805, C_0603, etc.)
- `quantity` - Total quantity needed
- `manufacturer` - Component manufacturer
- `mpn` - Manufacturer part number
- `description` - Component description
- `fabricator_part_number` - Fabricator-specific part number

### Field Merging with Fabricators

When using both `--fabricator` and `--fields`, fabricator-required fields are automatically included:

```bash
jbom bom --jlc --fields references,value,quantity
# Output includes: references, value, quantity, fabricator_part_number, mpn, manufacturer
# (JLCPCB required fields automatically added)
```

### Pipeline Integration

Use with other command-line tools:
```bash
# Count components by value
jbom bom --stdout | cut -d, -f2 | sort | uniq -c

# Filter for specific components
jbom bom --stdout | grep "^R[0-9]" > resistors_only.csv

# Convert to different format
jbom bom --stdout | python my_converter.py > custom_format.txt
```

### Human-Readable Output

View BOM data in formatted table:
```bash
jbom bom --output console
```

Example output:
```
Bill of Materials:
==================
References    | Value | Footprint | Qty | Fabricator Part# | Manufacturer Part#
--------------+-------+-----------+-----+------------------+-------------------
R1,R2,R3      | 10K   | R_0805    |  3  | C17414           | RC0805FR-0710KL
C1,C2         | 100nF | C_0603    |  2  | C14663           | CL10B104KB8NNNC
U1            | LM358 | SOIC-8    |  1  | C7950            | LM358DR

Total: 6 components, 3 unique parts
```

## Supported Fabricators

### JLCPCB (`jlc`)
- **Part Numbers**: LCSC catalog numbers (C1234)
- **Sourcing**: Internal LCSC distributor catalog
- **Usage**: `--jlc` or `--fabricator jlc`
- **Columns**: Designator, Value, Footprint, Quantity, LCSC Part#, Manufacturer Part#, Manufacturer

### PCBWay (`pcbway`)
- **Part Numbers**: Distributor part numbers (Mouser, Digi-Key, etc.)
- **Sourcing**: External distributor catalogs
- **Usage**: `--fabricator pcbway`
- **Columns**: Designator, Value, Package, Quantity, Distributor Part Number

### Generic (`generic`)
- **Part Numbers**: Manufacturer part numbers
- **Sourcing**: Original component manufacturers
- **Usage**: `--fabricator generic` (or no fabricator)
- **Columns**: References, Value, Footprint, Quantity, Manufacturer, Part Number

### Adding New Fabricators
To request support for additional fabricators, create an issue with:
1. Fabricator name and website
2. Required column headers and field mappings
3. Part number lookup requirements
4. Sample BOM file format

## Part Number Lookup System

The BOM plugin uses a sophisticated part number lookup system that understands the electronics supply chain:

### Supply Chain Relationships
- **Developer**: Specifies components in KiCad schematic
- **Manufacturer**: Makes components (Texas Instruments, Samsung, etc.)
- **Distributor**: Sells components (Mouser, Digi-Key, LCSC, etc.)
- **Fabricator**: Assembles PCBs (JLCPCB, PCBWay, etc.)

### Part Number Fields
Add these fields to your KiCad schematic component properties:

#### For JLCPCB/LCSC:
```
LCSC: C17414
LCSC Part: C17414
JLC: C17414
JLCPCB: C17414
```

#### For PCBWay/Distributors:
```
Mouser: 603-RC0805FR-0710KL
Digi-Key: 311-10.0KCRCT-ND
Distributor Part Number: 603-RC0805FR-0710KL
```

#### For All Fabricators:
```
MPN: RC0805FR-0710KL
MFGPN: RC0805FR-0710KL
Manufacturer: Yageo
Description: Resistor, 10K, 0805, 1%
```

### Lookup Priority
The system checks component fields in priority order:

**JLCPCB**: LCSC → LCSC Part → JLC → JLCPCB → MPN → MFGPN

**PCBWay**: Mouser → Digi-Key → Newark → Farnell → Distributor Part Number → MPN → MFGPN

### Missing Part Numbers
Components without matching part numbers will have blank entries in the fabricator part number column, but will still include manufacturer and value information.

## File Discovery

The BOM plugin automatically discovers KiCad files in the project:

1. **Schematic Files**: Looks for `*.kicad_sch` files
2. **Project File**: Looks for `*.kicad_pro` for project naming
3. **Hierarchical Designs**: Includes all schematic sheets automatically
4. **Output Name**: Uses project name if available, otherwise schematic filename

Example discovery:
```
MyProject/
├── MyProject.kicad_pro     ← Project file (used for naming)
├── MyProject.kicad_sch     ← Main schematic (source data)
├── PowerSupply.kicad_sch   ← Sub-schematic (included automatically)
├── CPU.kicad_sch           ← Sub-schematic (included automatically)
└── MyProject.bom.csv       ← Generated output
```

## Component Aggregation

The BOM plugin intelligently aggregates components:

### Aggregation Rules
Components are grouped by:
1. **Value** (10K, 100nF, etc.)
2. **Footprint** (R_0805, C_0603, etc.)

Components with the same value AND footprint become a single BOM line item.

### Reference Handling
- Multiple references are comma-separated: `R1,R2,R3`
- References are sorted naturally: `R1,R10,R2` becomes `R1,R2,R10`
- Quantity reflects total count: `Qty: 3` for `R1,R2,R3`

### Examples

**Input Components**:
```
R1: 10K, R_0805
R2: 10K, R_0805
R3: 10K, R_1206
C1: 100nF, C_0603
```

**BOM Output**:
```
References | Value | Footprint | Qty
-----------+-------+-----------+----
R1,R2      | 10K   | R_0805    | 2
R3         | 10K   | R_1206    | 1
C1         | 100nF | C_0603    | 1
```

## Error Handling

Common errors and solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| `No .kicad_sch files found` | No schematic files in directory | Specify PROJECT or run in correct directory |
| `Schematic file not found: path` | Invalid schematic path | Check file path and permissions |
| `Unknown fabricator: name` | Invalid fabricator ID | Use `--fabricator jlc` or check available IDs |
| `Error parsing schematic` | Corrupted schematic file | Check file integrity, try opening in KiCad |

## Output Formats

### CSV Format (Default)
Standard comma-separated values with headers. Default columns:
```csv
References,Value,Footprint,Qty
R1,10K,R_0805,1
```

### Fabricator CSV
Custom column headers and field ordering per fabricator requirements.

### Console Format
Human-readable table with automatic column sizing and alignment.

## Integration Notes

- **Component Data**: Extracted from KiCad schematic properties
- **Hierarchical Sheets**: All sheets included automatically
- **Field Mapping**: Flexible field name matching (case-insensitive)
- **Encoding**: UTF-8 output encoding
- **Line Endings**: System-appropriate (LF on Unix, CRLF on Windows)

## Performance

- **Small designs** (< 100 components): < 1 second
- **Medium designs** (100-1000 components): < 2 seconds
- **Large designs** (1000+ components): < 5 seconds
- **Memory usage**: Minimal, processes components incrementally

## Related Commands

- `jbom pos` - Generate position/placement files
- `jbom --help` - General help
- `jbom bom --help` - BOM-specific help

## Supply Chain Integration

The BOM plugin is designed for real-world electronics manufacturing:

### Procurement Workflow
1. **Design**: Add part numbers to KiCad schematic components
2. **Generate**: Create fabricator-specific BOMs with `jbom bom`
3. **Source**: Use part numbers to order components from distributors
4. **Assemble**: Submit BOMs to fabricators for PCB assembly

### Cost Analysis
- Export to spreadsheet tools for cost analysis
- Compare fabricator pricing using different part number sources
- Identify components without part numbers for manual sourcing

### Manufacturing Integration
- JLCPCB: Upload BOM directly to assembly service
- PCBWay: Provide distributor part numbers for sourcing
- Generic: Use manufacturer part numbers for custom assembly

This BOM plugin bridges the gap between KiCad design and real-world manufacturing, supporting the complete electronics supply chain from design to production.
