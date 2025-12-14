# jBOM - KiCad BOM Generator

A powerful tool that generates Bill of Materials (BOM) files for KiCad projects by intelligently matching schematic components against your inventory. Supports CSV, Excel, and Apple Numbers inventory files with advanced component matching and customizable output formats.

## Overview

This BOM generator takes a different approach from traditional KiCad BOM workflows. Instead of hardcoding supplier part numbers into your schematic symbols, it uses intelligent matching to connect your design components with your current inventory at BOM generation time.

**Key Benefits:**
- **Keep designs supplier-neutral** - No hardcoded part numbers in schematics
- **Use current inventory data** - Match against up-to-date stock and pricing
- **Intelligent component matching** - Robust numeric matching for resistors, capacitors, inductors
- **Multiple inventory formats** - CSV, Excel (.xlsx, .xls), and Apple Numbers (.numbers)
- **Priority-based selection** - Rank suppliers and stock preferences
- **Hierarchical schematic support** - Works with multi-sheet designs
- **Flexible output options** - Customize BOM columns and formats

## Installation

### Basic Installation using CSV inventory files

**Required:**
- Python 3.9 or newer
- `sexpdata` package for KiCad file parsing

```bash
pip install sexpdata
```

### Optional Inventory Spreadsheet Support (Apple Numbers and Microsoft Excel)

**For Excel files** (.xlsx, .xls):
```bash
pip install openpyxl
```

**For Apple Numbers files** (.numbers):
```bash
pip install numbers-parser
```

**Install everything:**
```bash
pip install sexpdata openpyxl numbers-parser
```

## Quick Start

### 1. Prepare Your Inventory

Create an inventory file with your components. Supported formats:
- **CSV** - Traditional comma-separated values
- **Excel** - Microsoft Excel (.xlsx, .xls) spreadsheets  
- **Numbers** - Apple Numbers (.numbers) spreadsheets

**Required columns:**
- `IPN` - Internal Part Number (your reference)
- `Category` - Component type (RES, CAP, LED, IC, etc.)
- `Value` - Component value (10k, 100nF, etc.)
- `Package` - Physical package (0603, 0805, SOT-23, etc.)
- `LCSC` - Supplier part number
- `Priority` - Ranking between similar inventory items (1=most preferred, larger numbers indicate a lower preference)

**Optional columns for enhanced matching:**
- `Manufacturer`, `MFGPN`, `Datasheet`, `Tolerance`, `V` (voltage), `A` (current), `W` (power)
- Component-specific: `mcd` (LED brightness), `Wavelength`, `Angle`, `Pitch`, `Form`, `Frequency`, `Stability`, `Load`, `Family`, `Type`
- See **Optional Columns for Enhanced Matching** section below for complete component-specific field details

### 2. Generate Your BOM

**Basic usage:**
```bash
python jbom.py MyProject/ -i MyInventory.xlsx
```

**With manufacturer info:**
```bash
python jbom.py MyProject/ -i MyInventory.csv -m
```

**Console output (no CSV file):**
```bash
python jbom.py MyProject/ -i MyInventory.numbers -o console
```

## Usage Examples

### Basic BOM Generation
```bash
# Using project directory (auto-finds schematic files)
python jbom.py AltmillSwitches/ -i SPCoast-INVENTORY.xlsx

# Using specific schematic file
python jbom.py MyProject/MyProject.kicad_sch -i inventory.csv

# Different inventory formats
python jbom.py Project/ -i inventory.csv        # CSV format
python jbom.py Project/ -i inventory.xlsx       # Excel format
python jbom.py Project/ -i inventory.numbers    # Numbers format
```

### Advanced Options
```bash
# Include manufacturer and part number columns
python jbom.py Project/ -i inventory.xlsx -m

# Verbose output with matching scores and debug info
python jbom.py Project/ -i inventory.csv -v

# SMD components only
python jbom.py Project/ -i inventory.xlsx --smd

# Detailed debug information for troubleshooting
python jbom.py Project/ -i inventory.csv -d

# Custom output columns
python jbom.py Project/ -i inventory.xlsx -f "Reference,Value,LCSC,Manufacturer"

# List all available columns
python jbom.py Project/ -i inventory.csv --list-fields
```

## Key Features

### Intelligent Component Matching
- **Type Detection**: Automatically identifies resistors, capacitors, inductors, LEDs, ICs, etc.
- **Package Matching**: Matches footprints (0603, 0805, SOT-23) with inventory packages
- **Numeric Value Parsing**: Handles various formats (10k, 10K0, 10000, 330R, 3R3, 100nF, 1uF, etc.)
- **Tolerance Substitution**: Tighter tolerances can substitute for looser requirements

### Priority-Based Selection
- Uses `Priority` column from inventory (1=most preferred, higher=less preferred)
- Supports multiple suppliers and stock preferences
- Automatic tie-breaking when multiple options exist

### Hierarchical Schematic Support
- **Auto-detection**: Finds and processes multi-sheet designs automatically
- **Intelligent file selection**: Prefers hierarchical roots over individual sheets
- **Comprehensive processing**: Combines components from all sheets

### Flexible Output Options
- **Standard BOM**: Reference, Quantity, Description, Value, Footprint, LCSC, Datasheet
- **With Manufacturers** (`-m`): Adds Manufacturer and MFGPN columns
- **Verbose** (`-v`): Adds matching scores and priority information
- **Custom Fields** (`-f`): Select specific columns from inventory and component data
- **Debug Mode** (`-d`): Detailed matching information for troubleshooting

### Multiple Inventory Formats
- **CSV**: Traditional comma-separated format
- **Excel**: Microsoft Excel (.xlsx, .xls) with intelligent header detection
- **Numbers**: Apple Numbers (.numbers) with automatic table processing

## Output

The tool generates:
1. **BOM CSV file** - `ProjectName_bom.csv` with your selected columns
2. **Console summary** - Statistics about components found and matched
3. **Debug warnings** - Issues with unmatched components (when using `-d`)

### Console Output Example
```
Schematic: 14 Components from AltmillSwitches.kicad_sch

Inventory:
   96 Items       SPCoast-INVENTORY.xlsx

BOM:
    6 Entries     AltmillSwitches/AltmillSwitches_bom.csv
```

## Troubleshooting

### Common Issues

**"No .kicad_sch file found"**
- Ensure you're pointing to the correct project directory
- Check that your schematic files have the `.kicad_sch` extension

**"Excel/Numbers support requires..."**
- Install the required packages: `pip install openpyxl numbers-parser`

**"Could not find 'IPN' header column"**
- Ensure your inventory file has an 'IPN' column
- Check that the spreadsheet data starts in the expected location

**Components not matching**
- Use `-d` flag to see detailed matching information
- Verify component types and values in your inventory
- Check that `Category` and `Package` columns are populated correctly

### Debug Mode

Use the `-d` flag to see detailed matching information:

```bash
python jbom.py Project/ -i inventory.csv -d
```

This provides:
- Component analysis (type detection, package extraction)
- Specific reasons why components can't be matched
- Available alternatives for mismatched packages
- Filtering statistics

## Inventory Requirements

### Required Columns
- `IPN` - Internal Part Number (your reference)
- `Category` - Component type (RES, CAP, LED, IC, etc.)
- `Value` - Component value (10k, 100nF, etc.)
- `Package` - Physical package (0603, 0805, SOT-23, etc.)
- `LCSC` - Supplier part number
- `Priority` - Ranking (1=preferred, higher=less preferred)

### Optional Columns for Enhanced Matching

#### General Component Specifications
- `Manufacturer`, `MFGPN`, `Datasheet` - Part identification and documentation
- `SMD` - Surface mount indicator (SMD/PTH/TH) 
- `Tolerance` - Component tolerance (±5%, ±1%, etc.) - **used for intelligent substitution**
- `V` (voltage) - Voltage rating - **used for matching and safety validation**
- `A` (current) - Current rating - **used for matching power components**  
- `W` (power) - Power rating - **used for matching resistors and power components**

#### Component-Specific Matching Fields

**Resistors** (Category: RES):
- `Tolerance` - Component tolerance matching with intelligent substitution (tighter tolerances can substitute looser)
- `V` - Voltage rating matching
- `W` or `Power` - Power rating matching
- `Temperature Coefficient` - Temperature coefficient matching

**Capacitors** (Category: CAP):
- `V` or `Voltage` - Voltage rating matching (critical for safety)
- `Type` - Dielectric type matching (ceramic, electrolytic, film, etc.)
- `Tolerance` - Capacitance tolerance matching

**Inductors** (Category: IND):
- `A` - Current rating matching (saturation current)
- `W` - Power rating matching

**LEDs** (Category: LED):
- `V` - Forward voltage matching
- `A` - Forward current matching  
- `mcd` - Light intensity/brightness matching
- `Wavelength` - Color/wavelength matching
- `Angle` - Beam angle matching

**Diodes** (Category: DIO):
- `V` - Voltage rating (reverse voltage, forward voltage)
- `A` - Current rating matching

**Transistors** (Category: Q):
- `V` - Voltage rating matching
- `A` - Current rating matching
- `W` - Power dissipation matching

**Oscillators** (Category: OSC):
- `Frequency` - Operating frequency matching
- `Stability` - Frequency stability/accuracy matching
- `Load` - Load capacitance matching

**Connectors** (Category: CON):
- `Pitch` - Pin pitch matching (2.54mm, 1.27mm, etc.)

**Microcontrollers** (Category: MCU):
- `Family` - MCU family matching (STM32, ESP32, etc.)
- `V` - Operating voltage matching

**Regulators** (Category: REG):
- `V` - Input/output voltage matching
- `A` - Current capacity matching
- `W` - Power handling matching

**Switches/Relays** (Category: SWI/RLY):
- `Form` - Contact configuration (SPDT, DPDT, etc.)

#### Matching Behavior
The BOM generator uses these fields for:
1. **Exact matching** - Finds components with identical specifications
2. **Intelligent substitution** - E.g., ±1% resistors can substitute ±5% requirements
3. **Safety validation** - Ensures voltage/current ratings meet or exceed requirements  
4. **Scoring priority** - Components with better matching specifications get higher scores

### Priority System
The `Priority` column encodes all business logic (cost, availability, sourcing preferences):
- **1** = Most preferred choice
- **2-5** = Good alternatives
- **Higher numbers** = Less preferred options

Example: `SPCoast-INVENTORY-new.csv` in this repo shows the improved inventory structure with descriptive IPN names and Priority column.

## Advanced Usage

See `README.developer.md` for detailed information about:
- Internal matching algorithms
- Component type detection logic
- Custom field system
- Data flow and processing details
- Extension and customization options
