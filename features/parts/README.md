# Parts Domain

## Use Case
As a hardware engineer, I want to generate a complete parts list from my KiCad project showing individual components (not aggregated like BOMs), so I can understand exactly which physical parts I need to procure or validate in my design.

## Core User Needs
1. "I want to see every individual component from my schematic in a simple list"
2. "I want to exclude components that shouldn't be manufactured (DNP, excluded from BOM)"
3. "I want to exclude KiCad's internal virtual symbols unless I specifically need them for debugging"
4. "I want control over what gets included without having to understand KiCad's internal implementation"

## KiCad Component Filtering Context

### Exclude from BOM vs Do Not Populate (DNP)
KiCad distinguishes between two types of component exclusion:

**Exclude from BOM**: Used for virtual components like mounting holes, fiducials, or logos that are part of the design but not physical parts to be procured. This completely removes them from BOM exports.

**Do Not Populate (DNP)**: Used for components that should appear in the BOM (for procurement) but should not be assembled on the final board. These still show up in parts lists but are marked as DNP.

### Virtual Symbols (# prefix)
KiCad automatically creates virtual symbols with references starting with '#' for:
- **Power Ports**: #PWR01, #PWR02 (VCC, GND connections)
- **PWR_FLAG Symbols**: Virtual components for Electrical Rules Check (ERC)
- **Unannotated Symbols**: Components that failed automatic annotation
- **Hierarchical Connection Points**: Internal schematic connectivity

These are KiCad implementation details, not physical components.

## Parts Command Behavior

### Default Filtering (Real Components Only)
```bash
jbom parts project.kicad_sch -o parts.csv
```
**Includes**: Normal components (R1, C1, U1, etc.)
**Excludes**: DNP components, components excluded from BOM, virtual symbols

### Selective Inclusion
```bash
jbom parts --include-dnp              # Include DNP components
jbom parts --include-excluded         # Include components excluded from BOM
jbom parts --include-all               # Include everything (DNP + excluded + virtual)
```

**Important**: `--include-excluded` does NOT include virtual symbols - users want excluded real components (mounting holes), not KiCad noise.

### Complete Override
```bash
jbom parts --include-all               # Everything including virtual symbols
```
For debugging or complete component analysis.

## Feature File Organization

- `filtering.feature` - Tests all component filtering scenarios
- `core.feature` - Basic parts list generation

## Testing Architecture

All scenarios use CSV output (`-o -`) and data table assertions to avoid brittle text matching:

```gherkin
When I run jbom command "parts -o -"
Then the CSV output has rows where:
  | Reference | Value |
  | R1        | 10K   |
And the CSV output does not contain components where:
  | Reference |
  | R2        |  # DNP component
```

This tests functional behavior (which components appear) rather than output formatting.
