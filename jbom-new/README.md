# jBOM - KiCad Bill of Materials Generator

A modern, simplified tool for generating Bill of Materials (BOM), inventory management, and placement files from KiCad projects.

## Architecture Overview

jBOM uses a **Service-Command Architecture** that eliminates complex plugin systems in favor of direct service usage:

```
src/jbom/
├── services/     # Pure business logic services
├── cli/          # Thin command wrappers
├── common/       # Shared utilities and data models
└── config/       # Configuration files

features/         # Gherkin BDD tests organized by command
tests/           # Unit tests for service logic
```

## Quick Start

### Installation
```bash
# Development installation
pip install -e .

# Or run directly
python -m jbom.cli.main --help
```

### Basic Usage
```bash
# Generate BOM from schematic
jbom bom project.kicad_sch

# Generate BOM with inventory enhancement
jbom bom project.kicad_sch --inventory components.csv

# Generate inventory from project
jbom inventory project.kicad_sch -o project_inventory.csv

# Generate placement file
jbom pos board.kicad_pcb --smd-only
```

## Architecture Principles

### Services vs Common Axiom
- **Services**: Have state and behavior (`__init__` with instance variables)
  - Example: `SchematicReader(options)`, `BOMGenerator(strategy)`
- **Common**: Stateless utilities and data structures
  - Example: `Component` dataclass, `get_component_type()` function

### Direct Service Usage
Commands import and use services directly - no plugin registry or discovery:

```python
# In cli/bom.py
from jbom.services.schematic_reader import SchematicReader
from jbom.services.bom_generator import BOMGenerator

def handle_bom(args):
    reader = SchematicReader(options)
    generator = BOMGenerator(args.aggregation)

    components = reader.load_components(args.schematic)
    bom_data = generator.generate_bom_data(components, project_name)
```

### Multi-Interface Ready
Services can be used by any interface without modification:
- CLI commands (current)
- GUI applications (future)
- Web APIs (future)
- KiCad plugins (future)

## Directory Guide

- [`src/jbom/services/`](src/jbom/services/README.md) - Business logic services
- [`src/jbom/cli/`](src/jbom/cli/README.md) - Command-line interface
- [`src/jbom/common/`](src/jbom/common/README.md) - Shared utilities and models
- [`features/`](features/README.md) - Gherkin BDD tests
- [`tests/`](tests/README.md) - Unit tests for services
- [`docs/`](docs/README.md) - Architecture documentation

## Development

### Testing
```bash
# Run Gherkin BDD tests
behave

# Run specific command tests
behave features/bom/

# Run unit tests (for internal service logic)
python -m unittest discover tests/
```

### Adding New Commands
1. Create service in `src/jbom/services/`
2. Create command handler in `src/jbom/cli/`
3. Register command in `src/jbom/cli/main.py`
4. Add Gherkin tests in `features/<command>/`

### Adding New Services
1. Create service class with `__init__` (has state/behavior)
2. Follow pure business logic - no CLI dependencies
3. Add unit tests in `tests/services/`
4. Document in `src/jbom/services/README.md`

## Key Files

- [`src/jbom/cli/main.py`](src/jbom/cli/main.py) - Main CLI entry with direct command registration
- [`src/jbom/services/bom_generator.py`](src/jbom/services/bom_generator.py) - Core BOM generation logic
- [`features/bom/bom_generation.feature`](features/bom/bom_generation.feature) - BDD tests for BOM functionality
- [`docs/architecture/SIMPLIFIED_ARCHITECTURE_PRINCIPLES.md`](docs/architecture/SIMPLIFIED_ARCHITECTURE_PRINCIPLES.md) - Detailed architecture principles

## Migration from Complex Architecture

This version of jBOM has been simplified from a complex plugin-based architecture:
- **Eliminated**: Plugin registry, discovery mechanisms, workflow abstractions
- **Reduced**: 90% reduction in architectural complexity
- **Gained**: Direct service usage, multi-interface support, simpler testing

See [`docs/architecture/`](docs/architecture/) for the complete evolution story.
