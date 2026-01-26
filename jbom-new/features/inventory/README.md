# Inventory Domain

## Use Cases

As a hardware engineer, I want to manage component inventories that bridge the gap between KiCad project components (design intent) and physical parts (sourcing reality).

## Core Workflows

### Workflow A: BOM without Inventory
```bash
jbom bom project/
```
- Simple component aggregation from KiCad project
- Groups by component type + value
- No IPN needed/expected
- Pure design intent → procurement list

### Workflow B: Inventory Generation (This Domain)
The inventory command creates inventory files from KiCad projects with intelligent IPN generation.

#### B1: Generate New Inventory
```bash
jbom inventory project/ -o new_inventory.csv
```
- **Creates IPNs** as hash values for electro-mechanical attributes
- Every unique project component → Inventory Item
- Bootstraps inventory system from KiCad design

#### B2: Merge with Existing Inventory
```bash
jbom inventory --inventory existing.csv -o merged_inventory.csv
```
- "Give me all of both and I'll sort things out"
- All items from existing.csv + new items from project
- Project items get new IPNs if not already in existing inventory

#### B3: Filter for Unmatched Components
```bash
jbom inventory --inventory existing.csv --filter-matches -o console
```
- "Show me only project items not already in existing inventory"
- Identifies gaps in current inventory
- Useful for procurement planning

### Workflow C: Enhanced BOM with Inventory
```bash
jbom bom --inventory inventory.csv project/
```
- **MATCH function** finds inventory items for KiCad components
- Happy path: Component.IPN == Inventory.IPN
- Fallback: Heuristic matching on electro-mechanical attributes
- Enhanced BOM with manufacturer data, pricing, etc.

## Key Concepts

### IPN (Inventory Part Number)
- Hash values representing specific electro-mechanical component attributes
- **Only created by `jbom inventory`** command
- Exact value immaterial - only equality comparison matters
- Examples: `RES_10K`, `CAP_100nF`, `IC_LM358`

### Component Attributes (KiCad)
- Reference: R1, C1, U1
- Value: 10K, 100nF, LM358
- Footprint: R_0603_1608, C_0805_2012, SOIC-8
- LibID: Device:R, Device:C, Device:IC

### Item Attributes (Inventory)
- IPN: RES_10K, CAP_100nF
- Category: RESISTOR, CAPACITOR, IC
- Value: 10k, 100nF (normalized)
- Description: Human-readable component description
- Package: 0603, 0805, SOIC-8 (normalized footprint)
- Manufacturer: Yageo, Murata, TI
- MFGPN: RC0603FR-0710KL (Manufacturer Part Number)

### MATCH Function
- Primary: Component.IPN == Item.IPN
- Secondary: Heuristic matching on electro-mechanical attributes
- Confidence levels determine match success/failure
- Used in Workflow C (Enhanced BOM)

## IPN Generation Logic

### Category Detection
1. **From LibID**: Device:R → RESISTOR, Device:C → CAPACITOR
2. **From Reference**: R1 → RESISTOR, C1 → CAPACITOR, U1 → IC
3. **From Footprint patterns**: SOIC-* → IC, LED_* → LED
4. **From Value patterns**: LM358, NE555 → IC

### Value Normalization
- Preserve original values exactly: `4.7K` → `4.7K`, `22μF` → `22μF`
- Handle special characters: `10K Ω` → `10K_Ω`
- Space replacement: `100 nF` → `100_nF`

### IPN Format
- Pattern: `{CATEGORY}_{VALUE}`
- Examples: `RES_10K`, `CAP_100nF`, `IC_LM358`, `LED_RED`
- Unknown components: Blank IPN (no magic)

## Testing Architecture

### CSV-First Approach
- Use `jbom inventory -o -` for data validation tests
- Avoid console output formatting issues (Issue #50)
- Test business logic, not presentation

### Data Table Driven
- Use `CSV output has rows where` for multiple assertions
- Focus on content matching, not ordering
- Robust against formatting changes

### Example Test Pattern
```gherkin
Scenario: Generate inventory with proper IPN creation
  Given a schematic that contains:
    | Reference | Value | Footprint   | LibID    |
    | R1        | 10K   | R_0603_1608 | Device:R |
    | C1        | 100nF | C_0603_1608 | Device:C |
  When I run jbom command "inventory -o -"
  Then the command should succeed
  And the CSV output has rows where
    | IPN       | Category  | Value |
    | RES_10K   | RESISTOR  | 10K   |
    | CAP_100nF | CAPACITOR | 100nF |
```

## Current Implementation Status

- ✅ Basic inventory generation (`jbom inventory`)
- ✅ IPN creation for standard components
- 🔄 Merge with existing inventory (`--inventory` flag)
- 🔄 Filter unmatched components (`--filter-matches` flag)
- ❓ Advanced heuristic matching
- ❓ Multi-source inventory precedence

## File Organization

- `IPN_generation.feature` - Core IPN creation logic
- `inventory_matching.feature` - Merge and filter workflows
- `multi_source.feature` - Multiple inventory file handling
- `multi_source_edge_cases.feature` - Complex precedence scenarios
