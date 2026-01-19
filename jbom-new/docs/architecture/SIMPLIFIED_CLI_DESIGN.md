# Simplified CLI Architecture

## Current Problem: Over-Engineered Plugin Registry

The current CLI uses a complex plugin registry system where:
- CLI handlers are buried in plugin directories
- Commands register themselves via import side effects
- Main CLI must discover and import all plugins
- Business logic is mixed with CLI argument parsing

## Service/Workflow/Command Solution: Direct Command Files

With proven Service → Workflow → Command decomposition, CLI becomes much simpler:

### **Simple Directory Structure**
```
src/jbom/commands/
├── __init__.py
├── bom.py          # Direct command handler
├── inventory.py    # Direct command handler
├── pos.py          # Direct command handler
└── search.py       # Direct command handler
```

### **Simple Main CLI**
```python
# src/jbom/cli/main.py
import argparse
from jbom.commands import bom, inventory, pos, search

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    # Direct command registration - no registry needed
    bom.register_command(subparsers)
    inventory.register_command(subparsers)
    pos.register_command(subparsers)
    search.register_command(subparsers)

    args = parser.parse_args()
    return args.handler(args) if hasattr(args, 'handler') else 0
```

### **Clean Command Handler Example**
```python
# src/jbom/commands/bom.py
import argparse
from pathlib import Path
from jbom.workflows.bom_workflows import generate_basic_bom, generate_inventory_enhanced_bom

def register_command(subparsers):
    """Register BOM command with argument parser."""
    parser = subparsers.add_parser('bom', help='Generate bill of materials')
    parser.add_argument('schematic', help='Path to .kicad_sch file')
    parser.add_argument('-o', '--output', help='Output file or stdout')
    parser.add_argument('--inventory', help='Enhance with inventory file')
    parser.set_defaults(handler=handle_bom)

def handle_bom(args):
    """Handle BOM command - pure CLI logic."""
    schematic_file = Path(args.schematic)

    if args.inventory:
        # Use inventory-enhanced workflow
        result = generate_inventory_enhanced_bom(
            schematic_file, Path(args.inventory)
        )
    else:
        # Use basic workflow
        result = generate_basic_bom(schematic_file)

    # Output handling (CSV formatter, console formatter, etc.)
    if args.output == 'stdout':
        print_csv(result)
    else:
        write_csv(result, args.output)

    return 0
```

## Benefits of Simplified Architecture

### **🚀 Massive Simplification**
- **No plugin registry** - commands register directly
- **No import side effects** - explicit registration
- **No plugin discovery** - commands are just modules
- **Clean separation** - CLI logic vs business logic

### **🔧 Perfect for Multiple Interfaces**
```python
# CLI uses commands
from jbom.commands.bom import handle_bom

# GUI uses workflows directly
from jbom.workflows.bom_workflows import generate_basic_bom

# Web API uses workflows directly
from jbom.workflows.bom_workflows import generate_inventory_enhanced_bom

# KiCad plugin uses services directly
from jbom.services.readers.schematic_reader import SchematicReader
```

### **🧪 Easy Testing**
- **Commands**: Test CLI argument parsing and output formatting
- **Workflows**: Test service orchestration
- **Services**: Test business logic in isolation

### **📦 Natural API Layers**
```python
# Public Python API = Workflows
from jbom.workflows import generate_basic_bom, generate_inventory_enhanced_bom

# Internal API = Services
from jbom.services import SchematicReader, BOMGenerator, InventoryMatcher

# CLI = Commands (thin wrapper over workflows)
from jbom.commands import bom, inventory, pos
```

## Migration Strategy

### **Phase 1**: Create Clean Commands
1. Create `src/jbom/commands/` directory
2. Extract CLI logic from plugin handlers into clean command modules
3. Commands use workflows (not services directly)

### **Phase 2**: Simplify Main CLI
1. Replace plugin registry with direct command imports
2. Remove plugin discovery complexity
3. Clean up import side effects

### **Phase 3**: Remove Plugin CLI Infrastructure
1. Delete plugin registry system
2. Delete plugin CLI handlers
3. Clean up main.py imports

## Result: Python API + Simple CLI

The CLI becomes what it should be - a **thin layer over the Python API**:

- **Python API** = Workflows (compose services)
- **CLI** = Commands (parse args, call workflows, format output)
- **GUI/Web/Plugins** = Call workflows directly

No complex registry, no plugin discovery, no import side effects - just clean, simple, testable code.
