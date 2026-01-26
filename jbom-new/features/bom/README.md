# BOM Priority and Selection Rules

## Use Case

As a hardware developer, I want predictable BOM organization that produces professional, reviewable bills of materials with consistent grouping, sorting, and formatting.

## Core Requirements

### 1. Category-Based Organization
Components should be grouped by category in a logical, configurable order:
- Default order: `CAP, RES, IND, LED, DIO, Q, REG, IC, MCU, CON, SWI, RLY, OSC, <other>`
- Categories derived from component properties (LibID, footprint patterns, etc.)

### 2. Within-Category Sorting
Within each category, components should be grouped by:
1. **Value** (natural sort: 1K < 10K < 100K)
2. **Package/Footprint** (natural sort: 0603 < 0805 < 1206)

### 3. Reference Grouping
Components with identical value+package should be grouped:
- References listed in natural order: `R1, R2, R10` (not `R1, R10, R2`)
- Quantity calculated automatically

### 4. Configurable Output Format
BOM columns and ordering determined by fabricator configuration:
- Generic fabricator provides default column set and ordering
- Other fabricator presets (JLC, PCBWay, Seeed) provide their specific formats
- Field selection configurable via `-f` / `--fields` option
- Line item numbering controlled by fabricator configuration

## Example Output

```csv
Item,Qty,Reference(s),Value,Package,Category,Description,Vendor,Vendor P/N,Manufacturer,Manufacturer P/N
1,2,"C1, C2",100nF,0805,CAP,"Capacitor 100nF 10% 50V X7R 0805",Digi-Key,1276-1004-1-ND,Samsung,CL21B104KBANFNC
2,1,R1,10k,0805,RES,"Resistor 10k Ohm 1% 1/8W 0805",Digi-Key,311-10.0KFRCT-ND,Yageo,RC0805FR-0710KL
3,1,U1,STM32F103C8T6,LQFP-48_7x7mm_P0.5mm,MCU,"Microcontroller ARM 32-bit Cortex-M3",Mouser,511-STM32F103C8T6,STMicroelectronics,STM32F103C8T6
```

## Testable Scenarios

### Category Ordering
- Capacitors appear before resistors
- Resistors appear before ICs
- Unknown categories appear last

### Value Sorting
- 1K resistors before 10K resistors
- 100nF capacitors before 1µF capacitors
- Natural numeric sorting (not alphabetic)

### Package Sorting
- 0603 packages before 0805 packages
- SOIC-8 before SOIC-16
- Natural size-based sorting where applicable

### Reference Grouping
- Identical components grouped together
- Reference list in natural order
- Correct quantity calculation

### Output Format
- Column ordering determined by fabricator configuration
- Proper CSV escaping
- Formatting behavior defined by selected fabricator preset
