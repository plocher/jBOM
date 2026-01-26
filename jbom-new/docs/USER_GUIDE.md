# jBOM User Guide

A comprehensive guide to using jBOM for Bill of Materials generation, inventory management, and component placement workflows.

## Command Overview

jBOM provides three main commands for different PCB development workflows:

- **`jbom bom`** - Generate Bills of Materials from KiCad schematics
- **`jbom inventory`** - Create and manage component inventory from projects
- **`jbom pos`** - Generate component placement files for PCB manufacturing

## Basic Usage

### Default Behavior
All commands default to human-readable console output for quick review:

```bash
# View BOM in console table format
jbom bom project.kicad_sch

# View inventory summary in console
jbom inventory project.kicad_sch

# View placement data in console
jbom pos board.kicad_pcb
```

### Saving to Files
Use `-o` to save structured output to CSV files:

```bash
# Save BOM to CSV
jbom bom project.kicad_sch -o project_bom.csv

# Save inventory to CSV
jbom inventory project.kicad_sch -o project_inventory.csv

# Save placement data to CSV
jbom pos board.kicad_pcb -o placement.csv
```

## Inventory Management Workflows

### Basic Inventory Creation

Generate an inventory file from a KiCad project:

```bash
# Create inventory with all components
jbom inventory myproject.kicad_sch -o components.csv
```

### Inventory Enhancement with Existing Data

Use existing inventory files to enhance your project's component information:

```bash
# Enhance BOM with inventory data
jbom bom project.kicad_sch --inventory existing_stock.csv -o enhanced_bom.csv

# Check which components need ordering
jbom inventory project.kicad_sch --inventory existing_stock.csv --filter-matches
```

### Multi-Source Inventory Management

Combine multiple inventory sources with priority-based selection:

```bash
# Use multiple inventory sources (priority fields determine best matches)
jbom bom project.kicad_sch \
  --inventory primary_stock.csv \
  --inventory backup_suppliers.csv \
  --inventory personal_components.csv \
  -o comprehensive_bom.csv
```

**Component Ranking**: jBOM should rank inventory items by (1) matching score, then (2) priority field. Multiple entries with the same IPN are legitimate when they represent supplier alternatives with different priority values.

**Current Limitation**: The implementation uses "first file wins" deduplication, which silently masks data integrity issues and ignores the priority ranking system.

### Inventory Data Model (Pragmatic Approach)

**The Challenge**: Represent normalized relational data in spreadsheet-friendly CSV format.

**Current "Good Enough" Approach** (with normalized intent):
```csv
IPN,Type,Value,Package,Manufacturer,MPN,Supplier,Cost,Priority
IPN-10k-E17-0603-Resistor,resistor,10k,0603,Yageo,RC0603FR-0710KL,Digikey,$0.10,1
IPN-10k-E17-0603-Resistor,resistor,10k,0603,Vishay,CRCW060310K0FKEA,Mouser,$0.12,2
IPN-100nF-X7R-0603-Capacitor,capacitor,100nF,0603,Samsung,CL10B104KB8NNNC,Digikey,$0.08,1
```

**Understanding the Intent**:
- **Same IPN rows** represent supplier alternatives for the same component
- **Component specs** (Type, Value, Package) should be identical across same-IPN rows
- **Priority field** (1=preferred) ranks suppliers within each IPN group
- **Conceptually normalized** but flattened into single CSV for spreadsheet usability

**Data Validation Rules**:
- Same IPN must have consistent component specifications
- Different Priority values indicate legitimate supplier alternatives
- Conflicting component specs for same IPN should trigger warnings

**Future Architecture**: This approach allows migration to fully normalized design (separate component/supplier tables) without breaking existing workflows.

### Incremental Inventory Updates

Add only new components to existing inventory:

```bash
# Create inventory of components NOT in existing stock
jbom inventory newproject.kicad_sch \
  --inventory existing_stock.csv \
  --filter-matches \
  -o additions_needed.csv
```

## Advanced Workflows

### Component Matching Logic

jBOM uses sophisticated matching to identify components across inventory sources:

1. **Exact IPN Match** (100 points) - Internal Part Numbers match exactly
2. **Type+Value+Package Match** (85 points) - All three attributes match
3. **Type+Value Match** (60 points) - Component type and value match
4. **Property-Based Match** (varies) - Custom property matching

### File Safety Features

jBOM protects existing files with safety features:

```bash
# Overwrite protection - requires --force to overwrite existing files
jbom bom project.kicad_sch -o existing_bom.csv --force

# Automatic backups when overwriting
jbom inventory project.kicad_sch -o inventory.csv --force
# Creates: inventory.backup.20240315_143022.csv
```

### Filtering and Selection

Control which components are included:

```bash
# SMD components only for placement files
jbom pos board.kicad_pcb --smd-only -o smd_placement.csv

# Filter out already-matched inventory
jbom inventory project.kicad_sch \
  --inventory stock.csv \
  --filter-matches \
  -o need_to_order.csv
```

## Common Use Cases

### 1. Project BOM Generation
Generate a complete BOM enhanced with your inventory data:

```bash
jbom bom myproject.kicad_sch \
  --inventory company_stock.csv \
  --inventory preferred_suppliers.csv \
  -o project_bom_with_sourcing.csv
```

### 2. Stock Management
Identify which components you need to order:

```bash
# What do I need to buy?
jbom inventory newproject.kicad_sch \
  --inventory current_stock.csv \
  --filter-matches \
  -o shopping_list.csv
```

### 3. Multi-Project Inventory
Build comprehensive inventory from multiple projects:

```bash
# Add Project A components
jbom inventory projectA.kicad_sch -o master_inventory.csv

# Add Project B components (only new ones)
jbom inventory projectB.kicad_sch \
  --inventory master_inventory.csv \
  --filter-matches \
  -o projectB_additions.csv

# Manually merge projectB_additions.csv into master_inventory.csv
```

### 4. Manufacturing Handoff
Create all manufacturing files with inventory enhancement:

```bash
# Enhanced BOM for procurement
jbom bom board.kicad_sch \
  --inventory suppliers.csv \
  -o manufacturing_bom.csv

# SMD placement for pick-and-place
jbom pos board.kicad_pcb --smd-only -o smd_placement.csv

# Through-hole placement for manual assembly
jbom pos board.kicad_pcb --through-hole-only -o th_placement.csv
```

## CSV File Formats

### BOM Files
```csv
Reference,Value,Footprint,Qty,Type,IPN,Manufacturer,MPN,Supplier,SPN,Cost,Stock
R1;R2;R3,10k,R_0603_1608Metric,3,resistor,RES-10K-0603,Yageo,RC0603FR-0710KL,Digikey,311-10KHRCT-ND,$0.10,1000
```

### Inventory Files
```csv
IPN,Type,Value,Package,Manufacturer,MPN,Supplier,SPN,Cost,Stock,Description
RES-10K-0603,resistor,10k,0603,Yageo,RC0603FR-0710KL,Digikey,311-10KHRCT-ND,$0.10,1000,10k resistor 1% 0603
```

### Placement Files
```csv
Ref,Val,Package,PosX,PosY,Rot,Side,Type
R1,10k,R_0603_1608Metric,45.2,32.1,0,top,SMD
```

## Verbose Output

Use `--verbose` for detailed processing information:

```bash
jbom bom project.kicad_sch --inventory stock.csv --verbose
```

This shows:
- Component matching details and scores
- Inventory lookup results
- File processing steps
- Warning messages for ambiguous matches

## Error Handling

jBOM provides clear error messages for common issues:

- **File not found**: Clear path information
- **Parse errors**: Line numbers and context
- **Permission errors**: Backup and overwrite guidance
- **Format errors**: Expected vs actual formats

Use `--verbose` to get more diagnostic information when troubleshooting issues.
