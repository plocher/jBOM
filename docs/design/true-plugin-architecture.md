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

### Proposed Plugin Architecture (Layered)
```
┌──────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│                  (Multiple UI consumers)                     │
├──────────────────────────────────────────────────────────────┤
│  CLI              │  KiCad Plugin    │  Web UI    │  TUI     │
│  - jbom bom       │  - Eeschema      │  - REST    │  - Curse │
│  - jbom pos       │  - Pcbnew        │  - GraphQL │  - Prompt│
│  - jbom validate  │  - GUI dialogs   │  - Browser │  - Rich  │
└──────────────────────────────────────────────────────────────┘
                              ▼
                     (All consume same API)
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                   Business Logic Layer                       │
│                      (Plugin APIs)                           │
├──────────────────────────────────────────────────────────────┤
│  BOM Plugin API      │  POS Plugin API     │  Validation API │
│  • generate_bom()    │  • generate_pos()   │  • validate()   │
│  • match_inventory() │  • extract_coords() │  • check_rules()│
│  • format_bom()      │  • transform_coords()│ • report()     │
├──────────────────────────────────────────────────────────────┤
│  Cost Plugin API     │  Supply Chain API   │  Custom APIs    │
│  • calculate_cost()  │  • check_stock()    │  • workflow()   │
│  • optimize()        │  • get_lead_times() │  • transform()  │
└──────────────────────────────────────────────────────────────┘
                              ▼
                    (Plugins use Core APIs)
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

## Plugin Interface Design (Layered Architecture)

### Core Principle: API-First Design

**Plugins provide business logic APIs**. The CLI, KiCad plugin, web UI, etc. are **consumers** of these APIs.

```
Plugin = Business Logic API + Optional UI Integrations
```

### Plugin Manifest

Each plugin declares its **API** (required) and **optional UI integrations**:

```python
# jbom_bom_plugin/__init__.py

from jbom.plugin import PluginManifest, APIExport, CLIIntegration, KiCadIntegration

manifest = PluginManifest(
    name="bom",
    version="1.0.0",
    description="Bill of Materials generation with intelligent matching",
    author="jBOM Contributors",
    requires_core="4.0.0",

    # Required: Business Logic API
    api_exports=[
        APIExport(
            name="generate_bom",
            handler="jbom_bom_plugin.api:generate_bom",
            version="1.0.0",
            description="Generate BOM from schematic and inventory",
        ),
        APIExport(
            name="match_inventory",
            handler="jbom_bom_plugin.api:match_inventory",
            version="1.0.0",
            description="Match components to inventory items",
        ),
    ],

    # Optional: CLI Integration
    cli_integration=CLIIntegration(
        commands=[
            {"name": "bom", "handler": "jbom_bom_plugin.cli:BOMCommand"},
        ],
    ),

    # Optional: KiCad Plugin Integration
    kicad_integration=KiCadIntegration(
        eeschema_plugin="jbom_bom_plugin.kicad:EeschemaPlugin",
    ),

    # Dependencies
    plugin_dependencies=[],
    dependencies=["pandas>=1.3.0"],
)
```

**Key Insight**: A plugin can provide an API without any CLI/UI. Another plugin or UI can consume the API.

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

### API Implementation (Business Logic Layer)

**Primary interface** - all UIs consume this:

```python
# jbom_bom_plugin/api.py

from typing import List, Dict, Optional
from dataclasses import dataclass
from jbom.core.types import Component, InventoryItem, BOMEntry
from jbom.plugin.api import public_api

@dataclass
class BOMOptions:
    """Configuration for BOM generation."""
    verbose: bool = False
    debug: bool = False
    smd_only: bool = False
    fields: Optional[List[str]] = None
    fabricator: Optional[str] = None

@dataclass
class BOMResult:
    """Result of BOM generation."""
    entries: List[BOMEntry]
    available_fields: Dict[str, str]
    metadata: Dict[str, any]
    warnings: List[str]

@public_api(version="1.0.0")
def generate_bom(
    components: List[Component],
    inventory: List[InventoryItem],
    options: BOMOptions = None
) -> BOMResult:
    """Generate BOM from components and inventory.

    Pure business logic - no I/O, no UI concerns.

    Args:
        components: Parsed schematic components
        inventory: Parsed inventory items
        options: Generation options

    Returns:
        BOMResult with entries and metadata
    """
    # Business logic implementation
    matcher = InventoryMatcher(inventory)
    grouped = group_components(components)
    entries = []

    for group in grouped:
        matches = matcher.find_matches(group)
        best = select_best_match(matches, options)
        entry = create_bom_entry(group, best)
        entries.append(entry)

    return BOMResult(
        entries=entries,
        available_fields=discover_fields(components, inventory),
        metadata={"version": "1.0.0"},
        warnings=collect_warnings(entries),
    )

@public_api(version="1.0.0")
def match_inventory(
    component: Component,
    inventory: List[InventoryItem],
) -> List[Tuple[InventoryItem, float]]:
    """Match single component to inventory.

    Returns list of (item, score) tuples sorted by score.
    """
    # Implementation
    pass
```

### CLI Integration (Presentation Layer)

**CLI is a thin wrapper** that calls the API:

```python
# jbom_bom_plugin/cli.py

from jbom.plugin.cli import CommandIntegration
from jbom.core.loaders import SchematicLoader, SpreadsheetLoader
from jbom_bom_plugin.api import generate_bom, BOMOptions

class BOMCommand(CommandIntegration):
    """CLI integration for BOM generation."""

    def setup_parser(self, parser):
        """Configure command arguments."""
        parser.add_argument("project")
        parser.add_argument("-i", "--inventory", required=True)
        parser.add_argument("-o", "--output")
        parser.add_argument("--smd-only", action="store_true")
        parser.add_argument("-v", "--verbose", action="store_true")

    def execute(self, args):
        """Execute BOM generation via API."""
        # I/O Layer: Load inputs using core services
        components = self.core.load_schematic(args.project)
        inventory, fields = self.core.load_spreadsheet(args.inventory)

        # Business Logic Layer: Call plugin API
        options = BOMOptions(
            verbose=args.verbose,
            smd_only=args.smd_only,
        )
        result = generate_bom(components, inventory, options)

        # Presentation Layer: Format and output
        if args.output == "console":
            self.print_table(result.entries, fields)
        else:
            self.write_csv(result.entries, args.output, fields)

        return 0
```

### KiCad Plugin Integration (Presentation Layer)

**KiCad plugin also consumes the same API**:

```python
# jbom_bom_plugin/kicad.py

from jbom.plugin.kicad import EeschemaIntegration
from jbom_bom_plugin.api import generate_bom, BOMOptions

class EeschemaPlugin(EeschemaIntegration):
    """KiCad Eeschema integration for BOM."""

    def run(self):
        """Called by KiCad when user clicks button."""
        # I/O: Get data from KiCad
        components = self.get_components_from_kicad()
        inventory_path = self.show_file_dialog("Select Inventory")
        inventory, fields = self.core.load_spreadsheet(inventory_path)

        # Business Logic: Same API as CLI
        options = self.get_options_from_dialog()
        result = generate_bom(components, inventory, options)

        # Presentation: Show in KiCad dialog
        self.show_results_dialog(result)
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

## Simplification: Remove KiCad Plugin Packaging (Recommended First Step)

### Current State Complexity

The current codebase attempts to support three meta-patterns:
1. **CLI** - Command-line interface
2. **Python API** - Programmatic access
3. **KiCad Plugin** - Poorly implemented packaging for KiCad integration

**Problem**: This creates unnecessary complexity in tests and architecture without clear value. The KiCad plugin packaging is poorly implemented and complicates the layered design.

### Recommended Simplification

**Remove KiCad plugin packaging** and focus on:

1. **Python API** (Business Logic Layer)
   - Core functionality as clean, testable APIs
   - Example: `jbom.api.generate_bom(components, inventory, options)`

2. **CLI** (Presentation Layer)
   - Thin wrapper that consumes the Python API
   - Already refactored with clean command structure

**Benefits**:
- ✅ Simpler testing (test API, test CLI separately)
- ✅ Clear layering (API → CLI, not intertwined)
- ✅ Removes poorly-implemented KiCad integration
- ✅ Foundation for true plugin architecture
- ✅ KiCad integration can be reimplemented later as a proper consumer of the API

### How KiCad Integration Would Work (Future)

Once the API is solid, KiCad integration becomes trivial:

```python
# kicad_jbom_plugin.py (separate package)

import pcbnew
from jbom.api import generate_bom
from jbom.core import CoreServices

class JBOMPlugin(pcbnew.ActionPlugin):
    def Run(self):
        # Get components from KiCad
        board = pcbnew.GetBoard()
        schematic_path = board.GetFileName().replace('.kicad_pcb', '.kicad_sch')

        # Use jBOM API (same as CLI uses)
        core = CoreServices()
        components = core.load_schematic(schematic_path)
        inventory, _ = core.load_spreadsheet(self.get_inventory_path())

        result = generate_bom(components, inventory)

        # Display results in KiCad
        self.show_dialog(result)
```

**Key insight**: KiCad plugin is just another **consumer** of the Python API, like CLI. No special packaging needed in core.

## Migration Path: API-First Refactoring

### Phase 0: Simplification (Immediate)
1. **Remove KiCad plugin packaging code**
   - Delete `kicad_jbom_plugin.py` or mark as deprecated
   - Remove KiCad-specific tests that test packaging (not functionality)
   - Keep KiCad file parsing (that's core functionality)

2. **Clarify testing strategy**
   - API tests: Test business logic directly
   - CLI tests: Test that CLI correctly calls API and formats output
   - No need for "meta-pattern" tests

### Phase 1: Extract Core Services
1. Move loaders, types, utils to `jbom/core/`
2. Create stable `CoreServices` API
3. Version the core API (semver)
4. No functional changes yet

### Phase 2: Solidify Python API
1. Define clean API surface in `jbom/api/`
2. API functions should NOT do I/O directly (take parsed objects)
3. Keep current `jbom.api.generate_bom()` but refactor internals
4. Document API contract with types and examples

### Phase 3: Refactor CLI as API Consumer
1. CLI commands become thin wrappers
2. CLI does: I/O → Call API → Format output
3. No business logic in CLI layer
4. Already started with command reorganization

### Phase 4: Plugin Infrastructure
1. Extract business logic to plugin packages
2. Implement `PluginLoader` and discovery
3. Enable/disable plugins
4. Version compatibility checking

### Phase 5: Optional UI Integrations
1. KiCad plugin as separate package (optional)
2. Web UI as separate package (optional)
3. TUI as separate package (optional)
4. All consume the same Python API

## Example: Custom Validation Plugin (Layered)

A user wants to add design rule validation:

```python
# jbom_validation_plugin/__init__.py

from jbom.plugin import PluginManifest, APIExport, CLIIntegration

manifest = PluginManifest(
    name="validation",
    version="1.0.0",
    description="KiCad schematic validation against design rules",
    requires_core="4.0.0",

    # API First: Business logic
    api_exports=[
        APIExport(
            name="validate",
            handler="jbom_validation_plugin.api:validate",
            version="1.0.0",
        ),
    ],

    # Optional: CLI wrapper
    cli_integration=CLIIntegration(
        commands=[{"name": "validate", "handler": "jbom_validation_plugin.cli:ValidateCommand"}],
    ),
)

# jbom_validation_plugin/api.py - Business Logic

from typing import List
from dataclasses import dataclass
from jbom.core.types import Component
from jbom.plugin.api import public_api

@dataclass
class ValidationRule:
    name: str
    check: callable
    severity: str  # "error", "warning", "info"

@dataclass
class ValidationIssue:
    rule: str
    component: str
    message: str
    severity: str

@public_api(version="1.0.0")
def validate(
    components: List[Component],
    rules: List[ValidationRule],
) -> List[ValidationIssue]:
    """Validate components against rules.

    Pure business logic - works in any context.
    """
    issues = []
    for component in components:
        for rule in rules:
            if not rule.check(component):
                issues.append(ValidationIssue(
                    rule=rule.name,
                    component=component.reference,
                    message=f"Component {component.reference} violates {rule.name}",
                    severity=rule.severity,
                ))
    return issues

# jbom_validation_plugin/cli.py - Presentation Layer

from jbom.plugin.cli import CommandIntegration
from jbom_validation_plugin.api import validate

class ValidateCommand(CommandIntegration):
    def setup_parser(self, parser):
        parser.add_argument("project")
        parser.add_argument("--rules", help="Path to rules file")

    def execute(self, args):
        # I/O: Load inputs
        components = self.core.load_schematic(args.project)
        rules = self.load_rules_file(args.rules)

        # Business Logic: Call API
        issues = validate(components, rules)

        # Presentation: Format output
        for issue in issues:
            print(f"{issue.severity.upper()}: {issue.message}")

        return 1 if any(i.severity == "error" for i in issues) else 0

# Usage examples:

# 1. CLI usage
$ pip install jbom-validation-plugin
$ jbom validate my_project/ --rules my_rules.yaml

# 2. Python API usage (no CLI needed)
from jbom.core import CoreServices
from jbom_validation_plugin.api import validate

core = CoreServices()
components = core.load_schematic("project/")
rules = load_my_rules()
issues = validate(components, rules)

# 3. Web UI usage (same API)
@app.post("/api/validate")
def validate_endpoint(project_id: str):
    components = load_from_db(project_id)
    rules = get_project_rules(project_id)
    issues = validate(components, rules)
    return {"issues": [asdict(i) for i in issues]}
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
