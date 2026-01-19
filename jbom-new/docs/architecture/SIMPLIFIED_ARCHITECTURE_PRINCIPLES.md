# Simplified Architecture Principles

**Date**: 2026-01-19
**Status**: Adopted from successful POC
**Branch**: `poc/service-workflow-command-decomposition`

## Key Learnings from POC

The Service/Workflow/Command POC proved that the **plugin architecture was unnecessary complexity**. The POC demonstrated that services can be consumed directly by CLI commands, GUIs, web interfaces, and KiCad plugins without any plugin registry or discovery mechanism.

## Architecture Axioms

### Services vs Common Distinction

**The Core Principle**: "Does it hold state and perform operations, or is it just data/utilities?"

**Services:**
- Classes with `__init__` that store configuration/state
- Objects that perform business operations
- Things you instantiate and call methods on
- Example: `reader = SchematicReader(options); components = reader.load(file)`

**Common:**
- Data classes/types (even with methods like `__str__`)
- Pure functions
- Constants, enums, mappings
- Configuration classes (just data containers)
- Utility functions that take input and return output
- Example: `Component(ref="R1")` or `parse_value("10K")`

**Future Application Rule**: If it has `__init__()` with instance variables → Services. If it's just functions, classes without state, or constants → Common.

## Target File Structure

Based on POC validation, the simplified structure eliminates artificial abstractions:

```
src/jbom/
├── services/           # All business logic services (flat structure)
│   ├── schematic_reader.py    # Read KiCad schematic files
│   ├── pcb_reader.py          # Read KiCad PCB files
│   ├── inventory_reader.py    # Load inventory CSV files
│   ├── bom_generator.py       # Generate BOM data
│   ├── inventory_matcher.py   # Match components to inventory
│   └── pos_generator.py       # Generate position files
├── cli/                # All CLI-related code together
│   ├── main.py         # Main CLI entry point with direct registration
│   ├── bom.py          # BOM command handler
│   ├── inventory.py    # Inventory command handler
│   └── pos.py          # Position file command handler
├── common/             # Utilities and shared code
│   ├── types.py        # Data models (Component, BOMEntry, etc.)
│   ├── options.py      # Configuration classes
│   ├── constants.py    # Business constants/mappings
│   ├── sexp_parser.py  # KiCad S-expression parser
│   └── packages.py     # Package/footprint utilities
└── sch_api/            # KiCad schematic API
    └── kicad_sch.py
```

## What Gets Deleted

**Complete elimination** of over-engineered abstractions:
- `src/jbom/plugins/` - Plugin architecture proven unnecessary
- `src/jbom/core/` - Plugin loader infrastructure
- `src/jbom/workflows/` - Over-engineered orchestration layer
- `src/jbom/commands/` - Merged into `cli/` for consolidation

## Service Design Principles

### Pure Business Logic
Services contain only business logic with no dependencies on:
- CLI frameworks
- Plugin infrastructure
- Other services (they can import and use other services directly)

### Direct Consumption
Services are directly importable by any interface:
```python
# CLI usage
from jbom.services.schematic_reader import SchematicReader
from jbom.services.bom_generator import BOMGenerator

# GUI usage (same imports)
# Web API usage (same imports)
# KiCad plugin usage (same imports)
```

### Flat Service Organization
No arbitrary subdivisions like `services/readers/`, `services/generators/`. All services are peers in the same directory, eliminating unnecessary hierarchy.

## CLI Design Principles

### Direct Registration
No plugin discovery or registry. Commands register directly in `cli/main.py`:
```python
# Direct registration - no complexity
from jbom.cli import bom, inventory, pos

def create_parser():
    subparsers = parser.add_subparsers()
    bom.register_command(subparsers)
    inventory.register_command(subparsers)
    pos.register_command(subparsers)
```

### Thin Command Handlers
Command handlers in `cli/` are thin wrappers that:
1. Parse CLI arguments
2. Import and instantiate needed services
3. Call service methods directly
4. Handle output formatting

Example:
```python
def handle_bom(args):
    reader = SchematicReader()
    generator = BOMGenerator()

    components = reader.load_components(args.schematic)
    bom_data = generator.generate_bom_data(components)

    if args.inventory:
        matcher = InventoryMatcher()
        bom_data = matcher.enhance_bom_with_inventory(bom_data, args.inventory)

    return output_bom(bom_data, args.output)
```

## Migration Strategy

1. **Phase 1**: Apply simplified structure to existing codebase
   - Flatten services directory
   - Consolidate CLI code
   - Remove plugin infrastructure

2. **Phase 2**: Update existing services to follow pure business logic pattern
   - Remove CLI dependencies from services
   - Update tests to focus on service logic

3. **Phase 3**: Migrate Gherkin tests
   - Move feature files from plugin directories to project-level `features/`
   - Update step definitions to use simplified command structure

## Benefits Proven by POC

- **90% reduction in CLI complexity** - no registry, no discovery
- **True modularity** - services work independently
- **Multi-interface ready** - same services for CLI, GUI, web, plugins
- **Simplified testing** - unit tests for services, integration tests as needed
- **Maintainable** - flat structure, clear separation of concerns

This architecture eliminates artificial abstraction layers while maintaining clean separation of concerns and supporting multiple interface patterns.
