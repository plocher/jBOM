# Component Filtering Refactoring

## Problem Solved
Eliminated DRY violations in component filtering across BOM, Parts, and POS commands by creating a common filtering module.

## Changes Made

### New Common Module: `src/jbom/common/component_filters.py`
- **`add_component_filter_arguments()`**: Adds consistent filtering flags to CLI parsers
- **`create_filter_config()`**: Creates filter configuration from CLI arguments
- **`apply_component_filters()`**: Common filtering logic for all generators
- **`get_filter_summary()`**: Human-readable filter description

### Filtering Logic Unified
All commands now use identical filtering logic:

```python
# Apply filters using common logic
filtered_components = apply_component_filters(components, filters or {})
```

### Command-Specific Flag Support

#### BOM & Parts Commands (`command_type="full"`)
- `--include-dnp`: Include DNP components
- `--include-excluded`: Include components excluded from BOM
- `--include-all`: Include everything (DNP + excluded + virtual symbols)

#### POS Command (`command_type="pos"`)
- `--include-dnp`: Include DNP components in placement file
- No `--include-excluded` or `--include-all` (not applicable to placement)

### Correct DNP Understanding for POS
**DNP (Do Not Populate) components:**
- Are **NOT placed/populated** during PCB assembly
- Should **NOT appear** in POS files by default
- **Can be included** with `--include-dnp` for design review/optional placement scenarios

### Updated CLI Commands
1. **BOM CLI** (`src/jbom/cli/bom.py`): Uses common filtering
2. **Parts CLI** (`src/jbom/cli/parts.py`): Uses common filtering
3. **POS CLI** (`src/jbom/cli/pos.py`): Added `--include-dnp` support

### Updated Service Generators
1. **BOMGenerator** (`src/jbom/services/bom_generator.py`): Removed duplicate filtering code
2. **PartsListGenerator** (`src/jbom/services/parts_list_generator.py`): Removed duplicate filtering code

### Consistent Behavior Across Commands
- **Virtual Symbols** (`#PWR*`): Always excluded except with `--include-all` (BOM/Parts only)
- **DNP Components**: Excluded by default, included with `--include-dnp`
- **BOM-Excluded Components**:
  - BOM/Parts: Excluded by default, included with `--include-excluded`
  - POS: Always included (mounting holes, logos still need placement coordinates)

## Benefits Achieved
1. **No more DRY violations**: Single source of truth for filtering logic
2. **Consistent UX**: Same flags work the same way across commands
3. **Easier maintenance**: Changes to filtering logic only need to be made once
4. **Better documentation**: Command-specific help text for filtering flags
5. **Extensible**: Easy to add new commands with consistent filtering support

## Testing
- All existing filtering scenarios continue to pass
- Common filtering logic tested through existing BOM and Parts test suites
- POS filtering ready for future DNP support when PCB/schematic cross-referencing is implemented
