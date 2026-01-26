# Inventory Domain

## Problem Statement

Hardware engineers need to bridge the gap between KiCad project components (design intent) and physical parts inventory (sourcing reality). This domain covers generating, matching, and filtering inventory items based on project requirements.

## Core Use Cases

### UC1: Generate Project Inventory
**As a** hardware engineer
**I want to** generate an inventory file from my KiCad project
**So that I can** bootstrap my inventory system or identify all required components

```bash
jbom inventory project/ -o new_inventory.csv
```

**Expected behavior:**
- Each unique component gets an inventory item with auto-generated IPN
- Components are categorized and normalized for consistent tracking
- Output includes description, package, and category information

### UC2: Identify Missing Components
**As a** hardware engineer
**I want to** compare my project against existing inventory
**So that I can** identify what components I need to order

```bash
jbom inventory --inventory existing.csv --filter-matches -o -
```

**Expected behavior:**
- Only components not found in existing inventory are output
- Matching is based on component attributes (category, value, package)
- Helps with procurement planning

### UC3: Merge Inventories
**As a** hardware engineer
**I want to** combine project components with existing inventory
**So that I can** maintain a comprehensive parts database

```bash
jbom inventory --inventory existing.csv -o merged_inventory.csv
```

**Expected behavior:**
- Existing inventory items are preserved
- New project components are added with unique IPNs
- No duplicate entries for identical components

### UC4: Handle Multiple Inventory Sources
**As a** hardware engineer
**I want to** work with multiple inventory files with precedence rules
**So that I can** manage different suppliers or inventory locations

```bash
jbom inventory --inventory primary.csv --inventory backup.csv -o -
```

**Expected behavior:**
- Files are processed in order of precedence (first file wins)
- Components found in earlier files are not duplicated
- Missing or malformed files are handled gracefully

## Key Concepts

### IPN (Inventory Part Number)
Auto-generated unique identifier for inventory items based on component attributes. Examples: `RES_10K`, `CAP_100nF`, `IC_LM358`

### Component Matching
Components are matched between project and inventory using category, value, and package attributes rather than exact string matching.

## Error Handling

### Invalid Inventory Files
- Missing inventory files cause command failure with clear error message
- Malformed CSV files are reported but don't prevent processing of valid files
- Multiple inventory file errors are reported individually

### Invalid Command Combinations
- `--filter-matches` without `--inventory` causes command failure
- Clear error messages guide correct usage

## Feature File Organization

- `core.feature` - Basic inventory generation from projects
- `IPN_generation.feature` - IPN creation and formatting rules
- `inventory_matching.feature` - Matching and filtering workflows
- `multi_source.feature` - Multiple inventory file handling
- `multi_source_edge_cases.feature` - Complex precedence and error scenarios
- `file_safety.feature` - File handling and error cases
