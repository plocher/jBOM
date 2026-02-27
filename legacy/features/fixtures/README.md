# jBOM Test Fixtures

This directory contains reusable test fixtures for BDD scenarios, implementing a DRY approach to test data management.

## Directory Structure

```
features/fixtures/
├── schematics/     # Standard schematic definitions
├── inventories/    # Standard inventory files
├── pcbs/           # Standard PCB layouts for POS testing
└── README.md       # This file
```

## Design Principles

### DRY (Don't Repeat Yourself)
- Define test data once, reuse across multiple scenarios
- Update fixture once, affects all dependent tests
- Reduces maintenance burden and inconsistencies

### Fixture Relationships
Fixtures are designed to work together logically:

**BasicComponents + JLC_Basic + BasicPCB**
- Schematic: R1(10K/0603), C1(100nF/0603), U1(ESP32/QFN-32)
- Inventory: JLC parts for each component
- PCB: Placement coordinates for each component

**MixedSMDTHT + MixedSMDTHT_PCB**
- Schematic: Mixed SMD and through-hole components
- PCB: Coordinates with Type classification

**ComponentProperties + SearchableInventory**
- Schematic: Components with detailed properties
- Inventory: Enhanced with manufacturer, MPN, specifications

## Usage Patterns

### Basic BOM Generation
```gherkin
Given the "BasicComponents" schematic
And the "JLC_Basic" inventory
When I generate a JLC BOM
Then the BOM contains 3 matched components
```

### Multi-Source Priority Testing
```gherkin
Given the "BasicComponents" schematic
And the "MixedFabricators" inventory
When I generate a JLC BOM
Then the BOM uses JLC parts with priority 1
```

### POS Generation
```gherkin
Given the "BasicPCB" PCB layout
When I generate a POS file
Then the POS contains 3 components with coordinates
```

### Error Handling
```gherkin
Given the "EmptySchematic" schematic
And the "JLC_Basic" inventory
When I generate a BOM
Then the BOM is empty with appropriate warning
```

## Fixture Benefits

✅ **Consistency**: Same test data across all scenarios
✅ **Maintainability**: Single point of change for each fixture
✅ **Clarity**: Well-named fixtures explain test intent
✅ **Reusability**: Mix and match fixtures for different test cases
✅ **DRY**: No duplication of component tables in scenarios

## Adding New Fixtures

1. **Document the fixture** in the appropriate README.md
2. **Define relationships** with existing fixtures
3. **Use descriptive names** that explain the fixture purpose
4. **Keep fixtures focused** - one specific test concern per fixture

## Implementation Notes

Step definitions will load fixtures from:
- `features/fixtures/schematics/{FixtureName}.json`
- `features/fixtures/inventories/{FixtureName}.csv`
- `features/fixtures/pcbs/{FixtureName}.json`

The fixture loading logic will be implemented in `features/steps/shared.py` with steps like:
```python
@given('the "{fixture_name}" schematic')
@given('the "{fixture_name}" inventory')
@given('the "{fixture_name}" PCB layout')
```
