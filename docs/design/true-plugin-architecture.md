# True Plugin Architecture for jBOM

## Executive Summary

This document outlines a comprehensive plugin architecture that transforms jBOM from a monolithic tool into an extensible platform. Unlike the current CLI command reorganization, this architecture enables plugins to bring entirely new capabilities to jBOM by building on top of core primitives.

**Core Vision**: jBOM provides foundational services (KiCad parsing, spreadsheet I/O, component modeling), while plugins implement domain-specific features (BOM generation, placement files, validation, analysis).

## Current vs. Proposed Architecture

### Current Architecture (Post-CLI Refactor)
```
┌─────────────────────────────────────────┐
│           Monolithic jBOM               │
├─────────────────────────────────────────┤
│ CLI Commands (auto-discovered)         │
│ ├─ bom      (thin wrapper)              │
│ ├─ pos      (thin wrapper)              │
│ └─ inventory (thin wrapper)             │
├─────────────────────────────────────────┤
│ Hardcoded Generators & Business Logic   │
│ ├─ BOMGenerator (matching, grouping)    │
│ ├─ POSGenerator (placement extraction)  │
│ └─ InventoryMatcher (scoring algorithm) │
├─────────────────────────────────────────┤
│ Core Services (good foundation)         │
│ ├─ Loaders (schematic, PCB, inventory)  │
│ ├─ Data types (Component, InventoryItem)│
│ └─ Utilities (parsing, fields, values)  │
└─────────────────────────────────────────┘
```

**Problem**: Business logic is hardcoded. Adding a new feature requires modifying core code.

### Proposed Plugin Architecture
```
┌──────────────────────────────────────────────────────────────┐
│                        jBOM Plugins                          │
│  (Independently developed, versioned, and distributed)       │
├──────────────────────────────────────────────────────────────┤
│  BOM Plugin          │  POS Plugin         │  Validation     │
│  - Matching algo     │  - CPL generation   │  - Design rules │
│  - BOM generation    │  - Coord systems    │  - Checks       │
│  - CLI: bom          │  - CLI: pos         │  - CLI: validate│
│  - API: generate_bom │  - API: generate_pos│  - API: validate│
├──────────────────────────────────────────────────────────────┤
│  Cost Analysis       │  Supply Chain       │  Custom...      │
│  - Price lookup      │  - Availability     │  - User-defined │
│  - Optimization      │  - Lead times       │  - Workflows    │
│  - CLI: cost         │  - CLI: supply      │  - CLI: custom  │
└──────────────────────────────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                   jBOM Core Platform                         │
│                 (Stable, well-documented API)                │
├──────────────────────────────────────────────────────────────┤
│  Plugin Infrastructure                                       │
│  ├─ Plugin discovery & loading (entry points)               │
│  ├─ Capability registration (CLI, API, hooks)               │
│  ├─ Lifecycle management (init, cleanup, dependencies)      │
│  └─ Version compatibility checking                          │
├──────────────────────────────────────────────────────────────┤
│  Core Services (Foundation for Plugins)                     │
│  ├─ KiCad Parsing                                           │
│  │  ├─ Schematic loader (hierarchical support)             │
│  │  ├─ PCB loader (dual-mode: pcbnew/sexp)                 │
│  │  └─ S-expression parser                                 │
│  ├─ Spreadsheet I/O                                         │
│  │  ├─ CSV reader/writer                                   │
│  │  ├─ Excel support (.xlsx, .xls)                         │
│  │  └─ Numbers support (.numbers)                          │
│  ├─ Component Model                                         │
│  │  ├─ Component dataclass                                 │
│  │  ├─ InventoryItem dataclass                             │
│  │  ├─ Package/Footprint concepts                          │
│  │  └─ Field system (I:/C: prefixes)                       │
│  ├─ Value Parsing & Formatting                             │
│  │  ├─ Resistor parsing (330R, 10K, 1M0)                   │
│  │  ├─ Capacitor parsing (100nF, 1uF, 220pF)               │
│  │  ├─ Inductor parsing (10uH, 2m2H)                       │
│  │  └─ EIA formatting utilities                            │
│  └─ Common Utilities                                        │
│     ├─ Field normalization                                 │
│     ├─ File discovery (hierarchical)                       │
│     ├─ Output path resolution                              │
│     └─ Configuration system                                │
└──────────────────────────────────────────────────────────────┘
```

## Core Platform Responsibilities

The core platform provides **stable, versioned APIs** that plugins depend on:

### 1. KiCad File Access
```python
# Core provides
from jbom.core.loaders import SchematicLoader, PCBLoader
from jbom.core.types import Component, PcbComponent

# Plugin uses
loader = SchematicLoader(project_path)
components = loader.load()  # List[Component]
```

### 2. Spreadsheet Operations
```python
# Core provides
from jbom.core.loaders import SpreadsheetLoader
from jbom.core.types import InventoryItem

# Plugin uses
loader = SpreadsheetLoader(inventory_path)
items, field_names = loader.load()  # (List[InventoryItem], List[str])
```

### 3. Component Model
```python
# Core provides
from jbom.core.types import Component, InventoryItem, Package, Footprint
from jbom.core.values import parse_resistor, format_eia_value
from jbom.core.fields import normalize_field_name, FieldPrefix

# Plugin uses
value_ohms = parse_resistor("10K")  # 10000.0
display = format_eia_value(10000, "RES", precision=True)  # "10K0"
```

### 4. Utility Functions
```python
# Core provides
from jbom.core.utils import discover_project_files, resolve_output_path
from jbom.core.fields import FieldSystem

# Plugin uses
schematic_files = discover_project_files(path, hierarchical=True)
output = resolve_output_path(input_path, output_arg, outdir, suffix)
```

## Plugin Interface Design

### Plugin Manifest

Each plugin declares its capabilities via metadata:

```python
# jbom_bom_plugin/__init__.py

from jbom.plugin import PluginManifest, CLICapability, APICapability

manifest = PluginManifest(
    name="bom",
    version="1.0.0",
    description="Bill of Materials generation with intelligent matching",
    author="jBOM Contributors",

    # Minimum core version required
    requires_core="4.0.0",

    # What does this plugin provide?
    capabilities=[
        CLICapability(
            command="bom",
            help_text="Generate Bill of Materials from KiCad schematic",
            handler="jbom_bom_plugin.cli:BOMCommand",
        ),
        APICapability(
            function="generate_bom",
            handler="jbom_bom_plugin.api:generate_bom",
        ),
    ],

    # Dependencies on other plugins (optional)
    plugin_dependencies=[],

    # Python package dependencies
    dependencies=["pandas>=1.3.0"],
)
```

### Plugin Lifecycle Hooks

```python
from jbom.plugin import Plugin

class BOMPlugin(Plugin):
    """BOM generation plugin implementation."""

    def on_load(self, core_services):
        """Called when plugin is loaded.

        Args:
            core_services: Access to core platform services
        """
        self.core = core_services
        self.config = self.load_config("bom_config.yaml")

    def on_enable(self):
        """Called when plugin is enabled by user."""
        # Register any global hooks
        pass

    def on_disable(self):
        """Called when plugin is disabled."""
        # Clean up resources
        pass

    def on_unload(self):
        """Called before plugin is unloaded."""
        # Final cleanup
        pass
```

### CLI Command Implementation

```python
# jbom_bom_plugin/cli.py

from jbom.plugin.cli import CommandPlugin
from jbom.core.loaders import SchematicLoader, SpreadsheetLoader

class BOMCommand(CommandPlugin):
    """CLI command for BOM generation."""

    def setup_parser(self, parser):
        """Configure command arguments."""
        parser.add_argument("project")
        parser.add_argument("-i", "--inventory", required=True)
        parser.add_argument("-o", "--output")
        # ... more arguments

    def execute(self, args):
        """Execute BOM generation."""
        # Use core services
        schematic = SchematicLoader(args.project)
        components = schematic.load()

        inventory = SpreadsheetLoader(args.inventory)
        items, fields = inventory.load()

        # Plugin-specific business logic
        bom = self.generate_bom(components, items)

        # Write output
        self.write_bom(bom, args.output)

        return 0
```

### API Implementation

```python
# jbom_bom_plugin/api.py

from typing import List, Dict
from jbom.core.types import Component, InventoryItem
from jbom.plugin.api import APIFunction

@APIFunction(version="1.0.0")
def generate_bom(
    project: str,
    inventory: str,
    options: Dict = None
) -> Dict:
    """Generate BOM from project and inventory.

    This is the public API other plugins or scripts can call.

    Args:
        project: Path to KiCad project
        inventory: Path to inventory file
        options: Configuration options

    Returns:
        Dict with keys: bom_entries, available_fields, metadata
    """
    # Implementation here
    pass
```

## Plugin Discovery and Loading

### Entry Points (pyproject.toml)

```toml
[project.entry-points."jbom.plugins"]
bom = "jbom_bom_plugin:manifest"
pos = "jbom_pos_plugin:manifest"
validate = "jbom_validate_plugin:manifest"
```

### Plugin Loading Process

```python
# jbom/plugin/loader.py

class PluginLoader:
    """Loads and manages jBOM plugins."""

    def discover_plugins(self):
        """Discover all installed plugins."""
        plugins = []

        # Load from entry points
        for ep in entry_points(group='jbom.plugins'):
            try:
                manifest = ep.load()
                plugins.append((ep.name, manifest))
            except Exception as e:
                logger.warning(f"Failed to load plugin {ep.name}: {e}")

        return plugins

    def load_plugin(self, manifest):
        """Load a plugin and its capabilities."""
        # Version compatibility check
        if not self.is_compatible(manifest.requires_core):
            raise PluginError(f"Incompatible core version")

        # Load CLI commands
        for cap in manifest.cli_capabilities:
            self.register_command(cap.command, cap.handler)

        # Load API functions
        for cap in manifest.api_capabilities:
            self.register_api(cap.function, cap.handler)

        # Initialize plugin
        plugin = self.instantiate_plugin(manifest)
        plugin.on_load(self.core_services)

        return plugin
```

## Core Services Interface

The core provides a stable API contract:

```python
# jbom/core/__init__.py

class CoreServices:
    """Stable API surface for plugins."""

    @property
    def version(self) -> str:
        """Core platform version."""
        return "4.0.0"

    # File loaders
    def load_schematic(self, path: str) -> List[Component]:
        """Load KiCad schematic."""
        pass

    def load_pcb(self, path: str, mode: str = "auto") -> List[PcbComponent]:
        """Load KiCad PCB."""
        pass

    def load_spreadsheet(self, path: str) -> Tuple[List[InventoryItem], List[str]]:
        """Load spreadsheet (CSV/Excel/Numbers)."""
        pass

    # Value parsing
    def parse_component_value(self, value: str, component_type: str) -> float:
        """Parse component value to base units."""
        pass

    def format_component_value(self, value: float, component_type: str) -> str:
        """Format value for display (EIA format)."""
        pass

    # Field system
    def normalize_field(self, field_name: str) -> str:
        """Normalize field name (case-insensitive, snake_case)."""
        pass

    def split_field_prefix(self, field: str) -> Tuple[FieldPrefix, str]:
        """Split I:/C: prefix from field name."""
        pass

    # Utilities
    def discover_project(self, path: str) -> List[str]:
        """Find all relevant files in project."""
        pass

    def resolve_output_path(self, input_path: str, output_arg: str,
                           outdir: str, suffix: str) -> str:
        """Resolve output file path."""
        pass
```

## Migration Path: BOM as First Plugin

### Phase 1: Extract Core Services
1. Move loaders, types, utils to `jbom/core/`
2. Create stable `CoreServices` API
3. Version the core API (semver)
4. No functional changes yet

### Phase 2: Create BOM Plugin Package
1. Extract BOM logic to `jbom_bom_plugin` package
2. Implement plugin manifest and lifecycle
3. BOM plugin uses `CoreServices` API
4. Ship both core and BOM plugin together initially

### Phase 3: Plugin Infrastructure
1. Implement `PluginLoader` and discovery
2. Enable/disable plugins
3. Plugin dependency resolution
4. Version compatibility checking

### Phase 4: Separate Distribution
1. Distribute BOM plugin separately
2. Core ships with "recommended plugins"
3. Users can install/uninstall plugins
4. Third-party plugins possible

## Example: Custom Validation Plugin

A user wants to add design rule validation:

```python
# jbom_validation_plugin/__init__.py

from jbom.plugin import PluginManifest, CLICapability

manifest = PluginManifest(
    name="validation",
    version="1.0.0",
    description="KiCad schematic validation against design rules",
    requires_core="4.0.0",
    capabilities=[
        CLICapability(
            command="validate",
            help_text="Validate schematic against rules",
            handler="jbom_validation_plugin.cli:ValidateCommand",
        ),
    ],
)

# jbom_validation_plugin/cli.py

from jbom.plugin.cli import CommandPlugin

class ValidateCommand(CommandPlugin):
    def setup_parser(self, parser):
        parser.add_argument("project")
        parser.add_argument("--rules", help="Path to rules file")

    def execute(self, args):
        # Use core services
        components = self.core.load_schematic(args.project)

        # Plugin logic
        rules = self.load_rules(args.rules)
        issues = self.validate(components, rules)

        # Report
        for issue in issues:
            print(f"Error: {issue}")

        return 1 if issues else 0

# Install and use
$ pip install jbom-validation-plugin
$ jbom validate my_project/ --rules my_rules.yaml
```

## Benefits of True Plugin Architecture

### For Users
- **Extensibility**: Add features without modifying jBOM
- **Flexibility**: Install only plugins you need
- **Choice**: Multiple plugins can solve same problem differently
- **Community**: Plugins from community extend capabilities

### For Developers
- **Modularity**: Develop features independently
- **Stability**: Core API provides stable foundation
- **Testing**: Test plugins in isolation
- **Distribution**: Publish plugins independently

### For Project
- **Maintainability**: Core stays focused and stable
- **Innovation**: Plugins can experiment freely
- **Compatibility**: Semver ensures version compatibility
- **Growth**: Ecosystem can grow without core bloat

## Technical Considerations

### Version Compatibility
```python
# Core announces breaking changes
CORE_VERSION = "4.0.0"  # Major bump = breaking API change

# Plugin declares requirements
requires_core = ">=4.0.0,<5.0.0"  # Compatible with 4.x
```

### Plugin Dependencies
```python
manifest = PluginManifest(
    name="advanced-bom",
    plugin_dependencies=[
        "bom>=1.0.0",  # Extends base BOM plugin
        "cost-analysis>=2.0.0",  # Uses cost data
    ],
)
```

### Configuration
```yaml
# ~/.jbom/config.yaml
plugins:
  enabled:
    - bom
    - pos
    - validation
  disabled:
    - legacy-exporter

bom:
  default_fields: "+standard"
  smd_only: false
```

### Error Handling
```python
try:
    plugin.on_load(core_services)
except PluginError as e:
    logger.error(f"Failed to load plugin {plugin.name}: {e}")
    # Core continues without this plugin
except Exception as e:
    logger.critical(f"Unexpected error loading {plugin.name}: {e}")
    # May need to abort if critical plugin
```

## Next Steps

1. **Validate Design**: Review with maintainers and community
2. **Core API Definition**: Finalize `CoreServices` interface
3. **Reference Implementation**: Extract BOM as first plugin
4. **Plugin SDK**: Create plugin development kit with templates
5. **Documentation**: Plugin developer guide
6. **Community**: Establish plugin directory/marketplace

## Open Questions

1. Should core ship with any plugins bundled, or all separate?
2. How to handle plugin conflicts (two plugins register same command)?
3. Plugin sandboxing/security model?
4. Hot-reloading of plugins during development?
5. Plugin GUI/TUI for enable/disable/configure?
6. Telemetry/analytics for plugin usage?

## Conclusion

This true plugin architecture transforms jBOM from a tool into a **platform**. The core provides stable, well-documented primitives for KiCad file access, spreadsheet operations, and component modeling. Plugins bring domain expertise in BOM generation, placement files, validation, analysis, and custom workflows.

Users benefit from extensibility without complexity. Developers benefit from modularity and stability. The project benefits from focused core development while enabling ecosystem growth.
