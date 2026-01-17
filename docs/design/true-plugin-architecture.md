# True Plugin Architecture for jBOM

## Executive Summary

This document outlines a comprehensive plugin architecture that transforms jBOM from a monolithic tool into an extensible platform. The architecture embraces a simple principle: **everything is a plugin**, using the same mechanism throughout.

**Core Vision**: jBOM consists of a lightweight plugin infrastructure plus coherent plugin modules. Foundation plugins (KiCad parsing, value parsing, spreadsheet I/O) provide evolvable primitives. Business logic plugins (BOM, POS, validation) build on these foundations. All plugins use the same architecture and can evolve independently via semantic versioning.

**Key Insight**: Foundation plugins are bundled with jBOM but remain independently versionable and potentially extractable as standalone packages for the broader KiCad ecosystem.

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
│                 jBOM Plugin Infrastructure                   │
│               (Minimal, focused core)                        │
├──────────────────────────────────────────────────────────────┤
│  • Plugin discovery & loading (entry points)                │
│  • Version compatibility checking (semver)                  │
│  • Dependency resolution                                    │
│  • Lifecycle hooks (on_load, on_enable, on_disable)        │
└──────────────────────────────────────────────────────────────┘
                              ▼
              ┌───────────────┴───────────────┐
              ▼                               ▼
    Foundation Plugins                Business Logic Plugins
    (Bundled with jBOM)              (Bundled with jBOM)

┌─────────────────────────┐        ┌─────────────────────────┐
│  kicad_parser v1.0      │        │  bom v2.0               │
│  ├─ load_schematic()    │        │  ├─ generate_bom()      │
│  ├─ load_pcb()          │◄───────┤  ├─ match_inventory()   │
│  ├─ Component model     │        │  └─ CLI: jbom bom       │
│  └─ S-expr parser       │        └─────────────────────────┘
└─────────────────────────┘
                                   ┌─────────────────────────┐
┌─────────────────────────┐        │  pos v1.0               │
│  value_parser v1.0      │        │  ├─ generate_pos()      │
│  ├─ parse_resistor()    │◄───────┤  ├─ extract_coords()    │
│  ├─ parse_capacitor()   │        │  └─ CLI: jbom pos       │
│  ├─ parse_inductor()    │        └─────────────────────────┘
│  └─ format_eia_value()  │
└─────────────────────────┘        Third-Party Plugins
                                   (Installed separately)
┌─────────────────────────┐
│  spreadsheet_io v1.0    │        ┌─────────────────────────┐
│  ├─ CSVHandler          │        │  validation v1.0        │
│  ├─ ExcelHandler        │◄───────┤  ├─ validate_rules()    │
│  ├─ NumbersHandler      │        │  └─ CLI: jbom validate  │
│  └─ InventoryItem model │        └─────────────────────────┘
└─────────────────────────┘
                                   External Consumers
                                   (Separate packages)

                                   ┌─────────────────────────┐
                                   │  kicad-fabrication-     │
                                   │  plugin (KiCad GUI)     │
                                   │  └─ Uses: kicad_parser, │
                                   │     bom, pos plugins    │
                                   └─────────────────────────┘
```

**Key Principles:**
1. **Simple pattern, repeated**: All capabilities use the same plugin mechanism
2. **Coherent modules**: Plugins group related functionality (not atomic singletons)
3. **Evolvable via semver**: Plugins evolve independently with version constraints
4. **Bundled but independent**: Foundation plugins ship with jBOM but remain separately versionable
5. **Externally reusable**: Foundation plugins can be extracted as standalone packages

## Plugin Types and Responsibilities

### Foundation Plugins (Bundled, Evolvable Primitives)

Foundation plugins provide **coherent modules** of related capabilities. They ship with jBOM but evolve independently via semantic versioning.

#### `kicad_parser` Plugin
Provides read-only access to KiCad project files.

```python
# Direct import for external consumers
from jbom.plugins.kicad_parser import load_schematic, load_pcb
from jbom.plugins.kicad_parser.types import Component, PcbComponent

# Usage
components = load_schematic("project.kicad_sch")
pcb_components = load_pcb("project.kicad_pcb")
```

**Capabilities:**
- Schematic loading (hierarchical sheet support)
- PCB loading (dual-mode: pcbnew Python API or s-expression)
- S-expression parser (fallback for all KiCad versions)
- Component data model (reference, value, footprint, fields)

**Evolution example:**
- v1.0: S-expression parsing only
- v1.1: Add support for KiCad 7 format changes (minor bump)
- v2.0: Use official `kicad.sch` API when available (major bump, implementation change)

**External reusability:** Could be extracted as standalone `kicad-data-api` package for broader KiCad ecosystem.

#### `value_parser` Plugin
Provides component value parsing and formatting.

```python
from jbom.plugins.value_parser import parse_value, format_value

ohms = parse_value("10K", component_type="RES")  # 10000.0
farads = parse_value("100nF", component_type="CAP")  # 1e-7
display = format_value(10000, "RES", eia_format=True)  # "10K0"
```

**Capabilities:**
- Resistor parsing (330R, 10K, 1M0)
- Capacitor parsing (100nF, 1uF, 220pF)
- Inductor parsing (10uH, 2m2H)
- EIA formatting utilities

**Evolution example:**
- v1.0: Resistor, capacitor parsing
- v1.1: Add inductor parsing (minor bump)
- v1.2: Add varistor/MOV parsing (minor bump)
- v2.0: Change return type to include units metadata (major bump)

**How to extend:** Update this plugin and bump version. Business logic plugins declare `requires = ["value_parser>=1.1"]` to use new parsers.

#### `spreadsheet_io` Plugin
Provides unified interface for multiple spreadsheet formats.

```python
from jbom.plugins.spreadsheet_io import load_spreadsheet, write_spreadsheet
from jbom.plugins.spreadsheet_io.types import InventoryItem

inventory, field_names = load_spreadsheet("inventory.xlsx")
write_spreadsheet(entries, "output.csv", field_names)
```

**Capabilities:**
- CSV reader/writer
- Excel support (.xlsx, .xls)
- Numbers support (.numbers)
- InventoryItem data model
- Field normalization

**Evolution example:**
- v1.0: CSV, Excel support
- v1.1: Add Numbers format support (minor bump)
- v1.2: Add Google Sheets API support (minor bump)
- v2.0: Change field normalization rules (major bump)

### Business Logic Plugins (Bundled, Domain Features)

Business logic plugins implement specific workflows by composing foundation plugin capabilities.

#### `bom` Plugin
Bill of Materials generation with intelligent inventory matching.

```python
from jbom.plugins.bom import generate_bom, BOMOptions

# API usage
result = generate_bom(components, inventory, options=BOMOptions(smd_only=True))

# CLI integration
$ jbom bom project/ -i inventory.xlsx -o bom.csv --smd-only
```

**Dependencies:**
- `kicad_parser>=1.0` (for loading components)
- `value_parser>=1.0` (for parsing values)
- `spreadsheet_io>=1.0` (for inventory and output)

**Capabilities:**
- Component grouping algorithm
- Inventory matching with scoring
- Field selection and ordering
- Multiple output formats
- CLI command integration

#### `pos` Plugin
Placement file generation for fabrication.

```python
from jbom.plugins.pos import generate_pos

result = generate_pos(pcb_components, options)
```

**Dependencies:**
- `kicad_parser>=1.0` (for loading PCB)
- `spreadsheet_io>=1.0` (for output)

### Third-Party Plugins (Optional, Community Extensions)

Third-party plugins extend jBOM with new capabilities.

```python
# Example: validation plugin
from jbom.plugins.validation import validate_design

issues = validate_design(components, rules)
```

## Plugin Interface Design

### Core Principle: Coherent, Evolvable Modules

**A plugin is a cohesive module** that groups related capabilities. Plugins evolve via semantic versioning and declare dependencies on other plugins.

```
Plugin = Related Capabilities + Version + Dependencies
```

**For business logic plugins:**
```
Business Logic Plugin = API Functions + Optional CLI/UI Integrations
```

### Plugin Manifest

Each plugin declares its capabilities and dependencies:

```python
# jbom/plugins/bom/__init__.py

from jbom.plugin import PluginManifest

manifest = PluginManifest(
    name="bom",
    version="2.0.0",
    description="Bill of Materials generation with intelligent inventory matching",
    author="jBOM Contributors",

    # Plugin dependencies (semver)
    requires=[
        "kicad_parser>=1.0.0,<2.0.0",
        "value_parser>=1.0.0,<2.0.0",
        "spreadsheet_io>=1.0.0,<2.0.0",
    ],

    # Python package dependencies
    dependencies=["pandas>=1.3.0"],

    # Public API exports
    exports=[
        "generate_bom",
        "match_inventory",
        "BOMOptions",
        "BOMResult",
    ],

    # Optional CLI integration
    cli_commands=[
        {"name": "bom", "handler": "jbom.plugins.bom.cli:BOMCommand"},
    ],
)
```

**Key Insights:**
- Foundation plugins declare no plugin dependencies (they're the foundation)
- Business logic plugins declare dependencies on foundation plugins
- Semver ranges ensure compatible versions are used
- CLI commands are optional (plugins can be API-only)

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

All plugins (bundled and third-party) use the same discovery mechanism:

```toml
# jBOM's pyproject.toml (bundled plugins)
[project.entry-points."jbom.plugins"]
kicad_parser = "jbom.plugins.kicad_parser:manifest"
value_parser = "jbom.plugins.value_parser:manifest"
spreadsheet_io = "jbom.plugins.spreadsheet_io:manifest"
bom = "jbom.plugins.bom:manifest"
pos = "jbom.plugins.pos:manifest"

# Third-party plugin's pyproject.toml
[project.entry-points."jbom.plugins"]
validation = "jbom_validation_plugin:manifest"
```

### Plugin Loading Process

```python
# jbom/plugin/loader.py

class PluginLoader:
    """Loads and manages jBOM plugins."""

    def discover_plugins(self):
        """Discover all installed plugins (bundled + third-party)."""
        plugins = []

        # Same mechanism for all plugins
        for ep in entry_points(group='jbom.plugins'):
            try:
                manifest = ep.load()
                plugins.append((ep.name, manifest))
            except Exception as e:
                logger.warning(f"Failed to load plugin {ep.name}: {e}")

        return plugins

    def resolve_dependencies(self, plugins):
        """Resolve plugin dependencies and determine load order."""
        # Topological sort based on requires=[...]
        pass

    def load_plugin(self, manifest):
        """Load a plugin and its capabilities."""
        # Check plugin dependencies (semver)
        for dep in manifest.requires:
            if not self.is_plugin_compatible(dep):
                raise PluginError(f"Missing or incompatible dependency: {dep}")

        # Load CLI commands (if present)
        for cmd in manifest.cli_commands:
            self.register_command(cmd['name'], cmd['handler'])

        # Initialize plugin
        plugin = self.instantiate_plugin(manifest)
        plugin.on_load()

        return plugin
```

## Plugin Evolution and Compatibility

### Adding Capabilities to Foundation Plugins

Foundation plugins evolve to add new capabilities:

```python
# value_parser v1.0.0
def parse_resistor(value: str) -> float: ...
def parse_capacitor(value: str) -> float: ...

# value_parser v1.1.0 (minor bump - backward compatible)
def parse_resistor(value: str) -> float: ...
def parse_capacitor(value: str) -> float: ...
def parse_inductor(value: str) -> float: ...  # NEW
def parse_varistor(value: str) -> float: ...  # NEW

# value_parser v2.0.0 (major bump - breaking change)
from dataclasses import dataclass

@dataclass
class ParsedValue:
    value: float
    unit: str
    confidence: float

def parse_resistor(value: str) -> ParsedValue: ...  # Changed return type
```

**How business logic adapts:**
```python
# bom plugin v2.0.0
manifest = PluginManifest(
    requires=[
        "value_parser>=1.0.0,<2.0.0",  # Compatible with 1.x
    ]
)

# bom plugin v3.0.0 (updated for new API)
manifest = PluginManifest(
    requires=[
        "value_parser>=2.0.0,<3.0.0",  # Uses new return type
    ]
)
```

### Swapping Implementations

When better implementations become available (e.g., official KiCad API):

```python
# kicad_parser v1.0.0 - Original implementation
def load_schematic(path: str) -> List[Component]:
    """Load via s-expression parsing."""
    return parse_sexpr(path)

# kicad_parser v2.0.0 - New implementation, same interface
def load_schematic(path: str) -> List[Component]:
    """Load via official KiCad API (if available) or s-expression fallback."""
    try:
        import kicad.sch
        return load_via_official_api(path)
    except ImportError:
        return parse_sexpr(path)  # Fallback
```

**Impact on business logic plugins:** ✅ Zero changes

They depend on the interface, not the implementation.

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

## Testing Strategy for Plugin Architecture

### Current Testing Landscape

**Unit tests** (`tests/unit/`):
- Component parsing (`test_loaders_schematic.py`, `test_processors_value_parsing.py`)
- Business logic (`test_generators_bom.py`, `test_inventory_matching.py`)
- CLI commands (`test_cli_inventory_command.py`, `test_cli.py`)
- ~20 test files testing internal implementation details

**Functional tests** (`tests/functional/`):
- End-to-end CLI execution (`test_functional_bom.py`, `test_functional_pos.py`)
- Format validation (`test_functional_inventory_formats.py`)
- Error cases (`test_functional_bom_errors.py`)
- **Problem**: `test_integration_all_interfaces.py` tests consistency between CLI, Python API, and KiCad plugin

**Current problem**: Tests are tightly coupled to monolithic implementation, making refactoring difficult.

### BDD/TDD Strategy for Plugin Refactoring

#### Principle: Behavior Over Implementation

**Test the contract, not the internals**. Each plugin exposes a public API—test that API's behavior, not how it's implemented.

```python
# BAD: Tests internal implementation
def test_bom_generator_uses_specific_matching_algorithm():
    generator = BOMGenerator()
    assert generator.matcher.__class__.__name__ == "InventoryMatcher"

# GOOD: Tests behavior (API contract)
def test_bom_generation_matches_components_to_inventory():
    components = [Component(ref="R1", value="10K")]
    inventory = [InventoryItem(mpn="RC0805FR-0710KL", value="10K")]

    result = generate_bom(components, inventory)

    assert len(result.entries) == 1
    assert result.entries[0].matched_item.mpn == "RC0805FR-0710KL"
```

#### Test Distribution Strategy

**Foundation Plugin Tests** (`tests/plugins/foundation/`):

```python
# tests/plugins/foundation/test_kicad_parser.py
class TestKiCadParserPlugin:
    """Test kicad_parser plugin API contract."""

    def test_load_schematic_returns_components():
        components = load_schematic("project.kicad_sch")
        assert all(hasattr(c, 'reference') for c in components)
        assert all(hasattr(c, 'value') for c in components)

    def test_hierarchical_schematic_flattens_components():
        components = load_schematic("hierarchical.kicad_sch")
        # Should include components from child sheets
        refs = [c.reference for c in components]
        assert any(ref.startswith("U1/") for ref in refs)

# tests/plugins/foundation/test_value_parser.py
class TestValueParserPlugin:
    """Test value_parser plugin API contract."""

    @pytest.mark.parametrize("input_val,expected", [
        ("10K", 10000.0),
        ("1M0", 1000000.0),
        ("330R", 330.0),
    ])
    def test_parse_resistor_handles_formats(input_val, expected):
        result = parse_value(input_val, component_type="RES")
        assert result == expected
```

**Business Logic Plugin Tests** (`tests/plugins/business_logic/`):

```python
# tests/plugins/business_logic/test_bom.py
class TestBOMPlugin:
    """Test bom plugin API contract."""

    def test_generate_bom_groups_identical_components():
        components = [
            Component(ref="R1", value="10K", footprint="0805"),
            Component(ref="R2", value="10K", footprint="0805"),
        ]

        result = generate_bom(components, [])

        assert len(result.entries) == 1  # Grouped
        assert result.entries[0].quantity == 2
        assert "R1" in result.entries[0].references
        assert "R2" in result.entries[0].references

    def test_generate_bom_respects_smd_only_filter():
        components = [
            Component(ref="R1", value="10K", footprint="0805"),
            Component(ref="R2", value="10K", footprint="TH"),
        ]

        opts = BOMOptions(smd_only=True)
        result = generate_bom(components, [], opts)

        # Only SMD component should appear
        assert len(result.entries) == 1
        assert "R1" in result.entries[0].references
        assert "R2" not in result.entries[0].references
```

**Functional Tests** (remain in `tests/functional/`):

```python
# tests/functional/test_functional_bom.py
class TestBOMFunctional(FunctionalTestBase):
    """Test BOM functionality end-to-end via CLI."""

    def test_bom_command_produces_valid_csv():
        """Test behavior: CLI produces valid CSV output."""
        output = self.output_dir / "bom.csv"

        rc, stdout, stderr = self.run_jbom([
            'bom', str(self.minimal_proj),
            '-i', str(self.inventory_csv),
            '-o', str(output)
        ])

        # Behavior verification
        assert rc == 0
        rows = self.assert_csv_valid(output)
        assert len(rows) > 1  # Header + data

    def test_bom_matches_components_to_inventory():
        """Test behavior: BOM includes matched inventory items."""
        output = self.output_dir / "bom.csv"

        self.run_jbom(['bom', str(self.minimal_proj),
                       '-i', str(self.inventory_csv), '-o', str(output)])

        rows = self.assert_csv_valid(output)
        # Check that inventory fields appear in output
        headers = rows[0]
        assert 'MPN' in headers or 'Manufacturer Part Number' in headers
```

#### What to DELETE During Refactoring

**Remove KiCad plugin packaging tests:**
```python
# DELETE: tests/functional/test_kicad_plugin.py
# DELETE: tests/functional/test_integration_all_interfaces.py (lines testing KiCad plugin)
```

**Rationale**: The poorly-implemented KiCad plugin wrapper adds test complexity without value. KiCad integration will be reimplemented later as an external consumer.

**Simplify multi-interface tests:**
```python
# BEFORE: Test CLI, Python API, and KiCad plugin produce same results
def test_fabricator_consistency_across_interfaces():
    python_result = test_python_api()
    cli_result = test_cli_interface()
    kicad_result = test_kicad_plugin()  # DELETE THIS
    compare_results(python_result, cli_result, kicad_result)

# AFTER: Test API behavior, then test CLI calls API correctly
def test_bom_api_with_fabricator():
    result = generate_bom(components, inventory, BOMOptions(fabricator="jlc"))
    assert "LCSC" in result.entries[0].fields

def test_cli_passes_fabricator_to_api():
    # Just verify CLI → API integration, not duplicate behavior
    output = run_jbom(['bom', 'project/', '--jlc', '-o', 'out.csv'])
    rows = read_csv(output)
    assert "LCSC" in rows[0]  # Header includes fabricator field
```

#### Unit Test Refactoring Strategy

**Audit each unit test:**
1. **Keep** if it tests a public plugin API
2. **Update** if it tests internal implementation details (make it test behavior instead)
3. **Delete** if it's redundant with functional tests

**Example refactoring:**
```python
# tests/unit/test_generators_bom.py - BEFORE
class TestBOMGenerator:
    def test_bom_generator_initializes_with_inventory():
        gen = BOMGenerator(inventory=[...])
        assert gen.inventory_loaded == True
        assert isinstance(gen.matcher, InventoryMatcher)

# AFTER refactor to plugin - tests/plugins/business_logic/test_bom.py
class TestBOMPlugin:
    def test_generate_bom_with_inventory_produces_matches():
        # Test behavior, not initialization
        result = generate_bom(components, inventory)
        assert all(e.matched_item is not None for e in result.entries)
```

### Migration Path: Test-First Refactoring

#### Phase 0: Test Simplification (Before Plugin Work)
1. **Remove KiCad plugin tests**
   - Delete `test_kicad_plugin.py`
   - Remove KiCad plugin sections from `test_integration_all_interfaces.py`
   - **Run tests to ensure 0 failures** (these tests are likely skipped or broken anyway)

2. **Document current behavior via functional tests**
   - Ensure functional tests cover all user-facing behaviors
   - These become the acceptance criteria for refactoring

#### Phase 1: Foundation Plugin Extraction (TDD)
1. **Create plugin API contract tests** (`tests/plugins/foundation/test_kicad_parser.py`)
   - Write tests for desired `kicad_parser` plugin API
   - Tests FAIL (plugin doesn't exist yet)

2. **Extract foundation plugin**
   - Move code to `src/jbom/plugins/kicad_parser/`
   - Expose public API: `load_schematic()`, `load_pcb()`
   - Tests PASS

3. **Update unit tests**
   - Change imports: `from jbom.loaders import ...` → `from jbom.plugins.kicad_parser import ...`
   - Delete tests of internal implementation details
   - **All functional tests still pass** (behavior unchanged)

4. **Repeat for other foundation plugins** (value_parser, spreadsheet_io)

#### Phase 2: Business Logic Plugin Extraction (BDD)
1. **Write behavior tests** for BOM plugin
   - `test_generate_bom_groups_components()`
   - `test_generate_bom_matches_inventory()`
   - `test_generate_bom_respects_filters()`

2. **Extract BOM plugin**
   - Move to `src/jbom/plugins/bom/`
   - Declare dependencies on foundation plugins
   - Tests PASS

3. **Update CLI tests**
   - CLI tests just verify: "CLI calls BOM plugin API correctly"
   - Don't duplicate BOM behavior tests

4. **Repeat for POS, inventory, etc.**

#### Phase 3: Plugin Infrastructure
1. **Write plugin loader tests**
   - Test discovery via entry points
   - Test dependency resolution
   - Test version compatibility

2. **Implement plugin infrastructure**
   - Tests drive implementation

### Test Organization After Refactoring

```
tests/
├── plugins/
│   ├── foundation/
│   │   ├── test_kicad_parser.py      # API contract tests
│   │   ├── test_value_parser.py      # Behavior tests
│   │   └── test_spreadsheet_io.py    # Format support tests
│   ├── business_logic/
│   │   ├── test_bom.py               # BOM generation behavior
│   │   ├── test_pos.py               # POS generation behavior
│   │   └── test_inventory.py         # Inventory matching behavior
│   └── infrastructure/
│       ├── test_plugin_loader.py     # Discovery & loading
│       ├── test_dependencies.py      # Dependency resolution
│       └── test_versioning.py        # Semver compatibility
├── functional/
│   ├── test_functional_bom.py        # End-to-end CLI tests
│   ├── test_functional_pos.py        # End-to-end CLI tests
│   └── test_functional_base.py       # Shared utilities
└── integration/
    └── test_real_projects.py          # Real-world project validation
```

**Key principles:**
- **Plugin tests** = Test public API contracts (behavior)
- **Functional tests** = Test end-to-end CLI workflows
- **Integration tests** = Test against real projects (regression prevention)
- **No duplicate behavior tests** across layers

## Migration Path: API-First Refactoring

### Phase 0: Simplification (Immediate)
1. **Remove KiCad plugin packaging code**
   - Delete `kicad_jbom_plugin.py` or mark as deprecated
   - Delete `tests/functional/test_kicad_plugin.py`
   - Remove KiCad plugin sections from `test_integration_all_interfaces.py`
   - Keep KiCad file parsing (that's core functionality)
   - **Verify**: All remaining tests pass

2. **Document behaviors via functional tests**
   - Ensure functional tests cover all user-facing CLI behaviors
   - These become acceptance criteria for refactoring
   - Add tests for any uncovered behaviors

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

## Example: External Consumer (KiCad Fabrication Plugin)

A separate package that integrates jBOM into KiCad's GUI:

```python
# kicad_fabrication_plugin/plugin.py (separate PyPI package)

import pcbnew
from jbom.plugins.kicad_parser import load_schematic, load_pcb
from jbom.plugins.spreadsheet_io import load_spreadsheet
from jbom.plugins.bom import generate_bom, BOMOptions
from jbom.plugins.pos import generate_pos

class FabricationPlugin(pcbnew.ActionPlugin):
    """KiCad GUI integration for jBOM (separate package)."""

    def Run(self):
        # Get current project from KiCad
        board = pcbnew.GetBoard()
        project_path = board.GetFileName().replace('.kicad_pcb', '')

        # Use jBOM foundation plugins (direct import)
        schematic_path = f"{project_path}.kicad_sch"
        components = load_schematic(schematic_path)

        # Show dialog for inventory file
        inventory_path = self.show_file_dialog("Select Inventory File")
        inventory, fields = load_spreadsheet(inventory_path)

        # Use jBOM business logic (same as CLI)
        options = BOMOptions(smd_only=False, verbose=True)
        bom_result = generate_bom(components, inventory, options)

        # Generate POS file
        pcb_components = load_pcb(f"{project_path}.kicad_pcb")
        pos_result = generate_pos(pcb_components)

        # Display results in KiCad dialog
        self.show_results_dialog(bom_result, pos_result)
```

**Key benefits:**
- ✅ Reuses all jBOM parsing logic (no duplication)
- ✅ Same BOM algorithm as CLI (consistency)
- ✅ Thin UI adapter (< 100 lines)
- ✅ Version pinning: `requires = ["jbom>=4.0.0,<5.0.0"]`
- ✅ External package evolution independent of jBOM core

## Example: Third-Party Validation Plugin

Community member wants to add design rule validation:

```python
# jbom_validation_plugin/__init__.py

from jbom.plugin import PluginManifest

manifest = PluginManifest(
    name="validation",
    version="1.0.0",
    description="KiCad schematic validation against design rules",

    # Depends on foundation plugin
    requires=[
        "kicad_parser>=1.0.0,<2.0.0",
    ],

    # Public API
    exports=["validate", "ValidationRule", "ValidationIssue"],

    # Optional CLI
    cli_commands=[
        {"name": "validate", "handler": "jbom_validation_plugin.cli:ValidateCommand"},
    ],
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

## Benefits of This Architecture

### For Users
- **Extensibility**: Community can add features without forking jBOM
- **Flexibility**: Install only plugins needed for specific workflows
- **Reliability**: Semver ensures compatible updates
- **Ecosystem**: Foundation plugins (like `kicad_parser`) can benefit broader KiCad community

### For Developers
- **Simplicity**: Same plugin pattern used throughout (foundation and business logic)
- **Modularity**: Develop features independently with clear dependencies
- **Evolvability**: Add capabilities via minor versions, change interfaces via major versions
- **Reusability**: Foundation plugins can be extracted as standalone packages
- **Testing**: Test plugins in isolation from each other

### For Project
- **No artificial stability**: Acknowledge that "core" evolves, manage it via semver
- **Fight bloat**: New parsers update `value_parser` plugin, don't add to monolith
- **Enable innovation**: Plugins experiment freely while foundations remain stable
- **External value**: Foundation plugins could become de facto KiCad data API
- **Future-proof**: When official KiCad API ships, swap implementation without breaking dependents

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

1. ~~Should core ship with any plugins bundled, or all separate?~~ **Resolved**: Foundation + business logic plugins are bundled (required dependencies) but use same mechanism as third-party plugins.
2. How to handle plugin conflicts (two plugins register same CLI command)?
3. Plugin sandboxing/security model for third-party plugins?
4. Hot-reloading of plugins during development?
5. Should foundation plugins be extractable to separate PyPI packages? Timeline?
6. Plugin GUI/TUI for enable/disable/configure?
7. Deprecation strategy when major versions change (e.g., `kicad_parser` v1 → v2)?

## Conclusion

This plugin architecture transforms jBOM from a monolithic tool into an **extensible platform** while embracing simplicity: **one pattern, repeated throughout**.

**Foundation plugins** (kicad_parser, value_parser, spreadsheet_io) provide evolvable primitives that could benefit the broader KiCad ecosystem. **Business logic plugins** (bom, pos, validation) compose these foundations into complete workflows. **External consumers** (kicad-fabrication-plugin) reuse jBOM's capabilities without duplication.

All plugins—bundled and third-party—use the same discovery, versioning, and dependency mechanisms. Evolution happens via semantic versioning, not by pretending the "core" is immutable. When better implementations emerge (like official KiCad APIs), plugins swap internally without breaking dependents.

Users benefit from extensibility. Developers benefit from coherent, evolvable modules. The project benefits from controlled evolution that fights bloat while enabling growth.
