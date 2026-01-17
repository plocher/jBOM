# jBOM Plugin Architecture

## Executive Summary

Transform jBOM from a monolithic tool into an extensible platform using standard Python packaging. **Simple principle: plugins are just Python packages.**

**Core Infrastructure**: Minimal - just standard Python imports and dependency management (pip)
**Foundation Plugins**: Bundled packages providing primitives (kicad_parser, value_parser, spreadsheet_io)
**Business Logic Plugins**: Bundled packages implementing workflows (bom, pos)
**Third-Party Plugins**: Community extensions installed via pip

All evolve independently using semantic versioning. Foundation plugins could become standalone packages for the broader KiCad ecosystem.

## Current vs. Proposed

### Current Architecture
```
Monolithic jBOM
├─ CLI layer (thin, recently refactored)
├─ Business logic (hardcoded: BOMGenerator, POSGenerator)
└─ Utilities (good: loaders, parsers, data models)
```

**Problem**: Adding features requires modifying core code. Everything is entangled.

### Proposed Architecture
```
Core Infrastructure (minimal)
└─ Standard Python packaging + imports

Bundled Plugins (ship with jBOM):
├─ kicad_parser (foundation)
├─ value_parser (foundation)
├─ spreadsheet_io (foundation)
├─ bom (business logic, depends on foundation plugins)
└─ pos (business logic, depends on foundation plugins)

Third-Party Plugins (installed separately):
└─ validation, cost_analysis, etc.
```

**Key insight**: Plugins are just Python packages declared in jBOM's `dependencies = [...]`. No custom plugin loader needed - pip handles everything.

## Core Infrastructure

### Minimal Core Components

The core provides **shared infrastructure** that all plugins can use:

1. **CLI Integration Framework** - Config-driven command registration
2. **Configuration System** - Unified config file handling
3. **Test Harness** - Common test patterns for plugins
4. **API Introspection** - Automatic documentation generation

### CLI Integration Framework

Plugins declare CLI commands via **simple configuration**, not code:

```yaml
# Plugin's cli_config.yaml
command:
  name: bom
  help: Generate Bill of Materials
  arguments:
    - name: project
      type: path
      default: "."
      help: KiCad project directory
    - name: --inventory
      type: file
      multiple: true
      help: Inventory spreadsheet(s)
    - name: --output
      short: -o
      type: output
      help: Output destination (file, console, stdout)
```

**Core provides:**
- Automatic argparse setup from config
- Standard argument types (path, file, output)
- Common argument patterns (--verbose, --output, fabricator flags)
- Error handling and output formatting

**Plugin provides:**
- Just the business logic function: `def execute(args) -> Result`

**Benefit**: Plugin authors don't write CLI boilerplate. Core handles all UI concerns.

### Configuration System

**Unified configuration** across all plugins:

```yaml
# ~/.jbom/config.yaml
core:
  cache_dir: ~/.cache/jbom
  log_level: INFO

plugins:
  kicad_parser:
    hierarchical_refs: true
  value_parser:
    tolerance_matching: strict
  bom:
    default_fields: +standard
    smd_filter: auto

fabricators:
  - name: jlcpcb
    cli_flags: [--jlc]
    fields: [LCSC, Basic_Part]
```

**Core provides:**
- Config file discovery (~/.jbom/config.yaml, ./.jbom.yaml, env vars)
- Validation and schema checking
- Per-plugin config sections
- Runtime config overrides

**Plugins access:**
```python
from jbom.core.config import get_plugin_config

config = get_plugin_config("bom")
default_fields = config.get("default_fields", "+standard")
```

### Common Test Harness

**Core provides test utilities** for all plugins:

```python
# jbom/core/testing/__init__.py

class PluginTestBase:
    """Base class for plugin tests."""

    @staticmethod
    def load_fixture(name: str) -> Path:
        """Load test fixture by name."""
        pass

    @staticmethod
    def create_temp_project() -> Path:
        """Create temporary test project."""
        pass

    def assert_valid_component(self, component):
        """Assert component has required fields."""
        assert hasattr(component, 'reference')
        assert hasattr(component, 'value')
```

**Gherkin step definitions** for functional tests:

```python
# jbom/core/testing/steps.py

@given('a schematic with components')
def schematic_with_components(context):
    context.schematic = load_fixture('minimal_project')

@when('I run "jbom {command} {args}"')
def run_jbom_command(context, command, args):
    context.result = run_cli(command, args.split())

@then('the output should contain {count:d} entries')
def assert_entry_count(context, count):
    assert len(context.result.entries) == count
```

**Plugin tests use common infrastructure:**
```python
# src/jbom/plugins/bom/tests/features/steps/bom_steps.py
from jbom.core.testing.steps import *  # Import common steps

# Add plugin-specific steps
@then('entries should be grouped by value')
def assert_grouped_by_value(context):
    # Plugin-specific assertion
    pass
```

### API Introspection & Documentation

**Plugins declare their API** using docstrings and type hints:

```python
# jbom/plugins/bom/__init__.py

def generate_bom(
    components: List[Component],
    inventory: List[InventoryItem],
    options: BOMOptions = None
) -> BOMResult:
    """Generate Bill of Materials with intelligent matching.

    Args:
        components: Parsed schematic components
        inventory: Available inventory items
        options: Generation options (filters, fields, etc.)

    Returns:
        BOMResult containing grouped entries with matches

    Example:
        >>> components = load_schematic("project.kicad_sch")
        >>> inventory = load_spreadsheet("inventory.csv")
        >>> result = generate_bom(components, inventory)
        >>> print(f"Generated {len(result.entries)} BOM lines")

    Raises:
        ValueError: If components list is empty
    """
    pass
```

**Core provides introspection tools:**

```python
# jbom/core/introspection.py

def discover_plugin_api(plugin_module) -> PluginAPI:
    """Extract API information from plugin module.

    Returns:
        PluginAPI containing:
        - Public functions (no leading underscore)
        - Type signatures (from type hints)
        - Documentation (from docstrings)
        - Examples (from docstring examples)
    """
    pass

def generate_api_docs(plugin_name: str) -> str:
    """Generate markdown documentation for plugin API."""
    api = discover_plugin_api(plugin_name)
    return render_template('api_docs.md.j2', api=api)
```

**Automatic documentation generation:**
```bash
# Generate docs for all plugins
$ jbom docs --generate

# Generated files:
# docs/api/kicad_parser.md
# docs/api/value_parser.md
# docs/api/bom.md
```

**API discovery at runtime:**
```bash
# Introspect plugin API
$ jbom api bom --show

Plugin: bom v2.0.0
Functions:
  generate_bom(components, inventory, options) -> BOMResult
    Generate Bill of Materials with intelligent matching

  match_inventory(component, inventory) -> List[Match]
    Find matching inventory items for a component

Types:
  BOMOptions(verbose, debug, smd_only, fields, fabricator)
  BOMResult(entries, available_fields, metadata, warnings)
```

## Design Patterns

### Pattern 1: Plugins Are Python Packages

**Foundation plugin structure:**
```
src/jbom/plugins/kicad_parser/
├── __init__.py          # Public API
├── schematic.py         # Implementation
├── pcb.py              # Implementation
├── types.py            # Data models (Component, etc.)
└── tests/              # Plugin-specific tests
    ├── unit/
    └── features/       # Gherkin scenarios
```

**Public API** (just functions):
```python
# jbom/plugins/kicad_parser/__init__.py
def load_schematic(path: str) -> List[Component]:
    """Load KiCad schematic and return components."""
    pass

def load_pcb(path: str) -> List[PcbComponent]:
    """Load KiCad PCB and return placement data."""
    pass
```

**No base classes, no manifests, no registration magic** - just importable functions.

### Pattern 2: Dependencies via Standard Packaging

**jBOM's pyproject.toml:**
```toml
[project]
dependencies = [
    # Foundation plugins (bundled but versioned)
    "jbom-kicad-parser>=1.0.0,<2.0.0",
    "jbom-value-parser>=1.0.0,<2.0.0",
    "jbom-spreadsheet-io>=1.0.0,<2.0.0",
    # Business logic plugins
    "jbom-bom>=2.0.0,<3.0.0",
    "jbom-pos>=1.0.0,<2.0.0",
]
```

**Runtime**: pip resolves dependencies at install time. No custom dependency resolution needed.

### Pattern 3: Evolution via Semver

**Adding capabilities (minor version):**
```python
# value_parser v1.0: resistors, capacitors
# value_parser v1.1: + inductors (backward compatible)
# value_parser v1.2: + varistors (backward compatible)
```

Business logic plugins: `requires = ["jbom-value-parser>=1.0"]` automatically get new parsers.

**Changing interfaces (major version):**
```python
# value_parser v1.x returns float
# value_parser v2.0 returns ParsedValue(value, unit, tolerance)
```

Business logic plugins upgrade when ready: `requires = ["jbom-value-parser>=2.0,<3.0"]`

**Swapping implementations:**
```python
# kicad_parser v1.x: S-expression parsing
# kicad_parser v2.0: Official kicad.sch API (same interface, new impl)
```

Dependents automatically benefit from improvements without code changes.

### Pattern 4: Component Data Types

**Rich data types over primitive arguments:**
```python
# Poor API
format_value(10000, "RES", tolerance=0.01, eia_format=True)  # Too many args

# Better API
component = Component(value=10000, type="RES", tolerance=0.01)
display = component.format(eia=True)  # "10K0" (knows tolerance)
```

Component types encapsulate their own formatting rules, tolerance knowledge, etc.

### Pattern 5: Test Organization

**Plugin-local tests:**
```
src/jbom/plugins/bom/
├── __init__.py
├── generator.py
└── tests/
    ├── unit/                    # Internal algorithm tests (pytest)
    └── features/               # API contract tests (Gherkin)
        └── bom_generation.feature
```

**Global functional tests:**
```
tests/functional/
└── features/
    ├── cli_bom.feature         # End-to-end CLI behavior (Gherkin)
    └── cli_pos.feature
```

**Principle**: Functional tests define the contract (GIVEN-WHEN-THEN). Unit tests can break during refactoring. **When tests and code disagree, trust functional tests, rewrite unit tests.**

## Migration Strategy

### Option A: Greenfield Development (Recommended)

Build new plugin-based jBOM alongside existing codebase:

1. **Create new structure**
   - Start with minimal foundation plugin (e.g., kicad_parser)
   - Write Gherkin scenarios for desired behavior
   - Implement until scenarios pass

2. **Extract and iterate**
   - Extract one plugin at a time from current jBOM
   - Reach feature parity for each plugin independently
   - Current jBOM continues working during development

3. **Cutover when ready**
   - Replace jBOM internals OR
   - Release as jBOM v4.0.0 with migration guide

**Benefit**: No risk to current users, can develop/test in parallel, merge when confident.

### Option B: Incremental Refactoring

Refactor existing jBOM in place:

1. **Simplify** - Remove poorly-implemented KiCad plugin packaging
2. **Extract foundation plugins** - One at a time, TDD-style
3. **Extract business logic plugins** - BDD-style with Gherkin
4. **Update packaging** - Convert to plugin dependencies

**Risk**: Potential disruption to existing functionality during transition.

### Recommendation

**Start greenfield.** Proves the architecture works before committing to full migration. Foundation plugins can be used by both old and new jBOM during transition.

## Core Infrastructure Details

### CLI Integration Implementation

**Pattern**: Config-driven command registration avoids boilerplate

Current jBOM already uses this pattern (see `commands/base.py`):
- `Command` base class with metadata
- Auto-registration via `__init_subclass__`
- Common argument helpers (`add_project_argument`, `add_common_output_args`)
- Standard error handling

**Extension for plugins**: Extract this into core so plugins inherit it without reimplementation.

```python
# Core provides
from jbom.core.cli import PluginCommand

# Plugin uses
class BOMCommand(PluginCommand):
    config_file = "cli_config.yaml"  # Core loads config

    def execute(self, args):
        # Just business logic, no argparse setup
        return generate_bom(args.project, args.inventory)
```

### Configuration Implementation

**Pattern**: Hierarchical config with plugin namespaces

Current jBOM uses `common/config.py` with fabricator config. Extend this:

```python
# Core provides unified config access
from jbom.core.config import Config

config = Config.load()  # Discovers files, merges, validates
core_settings = config.core
plugin_settings = config.plugins.bom
fabricators = config.fabricators
```

**Config file locations** (precedence order):
1. Environment: `JBOM_CONFIG=/path/to/config.yaml`
2. Current dir: `./.jbom.yaml`
3. User home: `~/.jbom/config.yaml`
4. System: `/etc/jbom/config.yaml`

### Test Harness Implementation

**Pattern**: Reusable test fixtures and step definitions

Current jBOM has `tests/functional/test_functional_base.py` with common utilities. Extract and enhance:

```python
# Core provides (extracted from current FunctionalTestBase)
from jbom.core.testing import PluginTestBase

class PluginTestBase:
    fixtures_dir: Path  # Common test fixtures

    def run_cli(self, *args) -> Result:
        """Run jBOM CLI and capture result."""

    def assert_valid_csv(self, path: Path):
        """Assert file is valid CSV."""
```

**Gherkin integration** (using behave or pytest-bdd):
```python
# Core provides common steps (extracted from current patterns)
from jbom.core.testing.steps import *

# Steps available to all plugins:
# - Given a schematic with components
# - When I run "jbom {command}"
# - Then the output should contain
```

### API Introspection Implementation

**Pattern**: Standard Python introspection + structured docstrings

```python
import inspect
from typing import get_type_hints

def introspect_plugin(module):
    """Extract API from module using introspection."""
    api_functions = {}

    for name, obj in inspect.getmembers(module):
        if inspect.isfunction(obj) and not name.startswith('_'):
            api_functions[name] = {
                'signature': inspect.signature(obj),
                'type_hints': get_type_hints(obj),
                'docstring': inspect.getdoc(obj),
            }

    return api_functions
```

**Documentation generation** uses templates:
- Jinja2 templates for markdown
- Sphinx integration for API docs
- OpenAPI/JSON Schema for API specifications

## Key Decisions

### Dependency Management
**Decision**: Use standard pip/Python packaging, not custom plugin loader.
**Rationale**: Don't reinvent package management. Pip handles versions, conflicts, resolution.

### CLI Integration
**Decision**: Config-driven command registration in core.
**Rationale**: Plugin authors provide business logic only, not UI boilerplate. Reduces duplication, ensures consistency.

### Configuration System
**Decision**: Unified hierarchical config with plugin namespaces.
**Rationale**: Single source of truth, easy for users to configure all plugins in one place.

### Plugin Discovery
**Decision**: Use standard Python imports, not entry points/manifests (unless needed for CLI commands).
**Rationale**: Simpler. Plugins are just imports: `from jbom.plugins.kicad_parser import load_schematic`

### CLI Command Registration
**Decision**: Entry points for CLI commands only (if plugin provides CLI).
**Rationale**: Standard pattern for extending CLIs. Optional - plugins can be API-only.

```toml
[project.entry-points."jbom.cli"]
bom = "jbom.plugins.bom.cli:BOMCommand"
```

### Foundation Plugin Reusability
**Decision**: Design for external extraction from day one.
**Rationale**: `kicad_parser` could become community standard for KiCad data access. Clean APIs enable this.

### Testing Strategy
**Decision**: Gherkin for functional tests, pytest for unit tests.
**Rationale**: GIVEN-WHEN-THEN captures user behavior clearly. Unit tests for implementation details.

### Lifecycle Hooks
**Decision**: None needed initially. Revisit if plugins need initialization/cleanup.
**Rationale**: YAGNI. Most plugins are stateless functions. Add hooks only when proven necessary.

## Open Questions

1. **Foundation plugin extraction timeline**: When to publish as separate packages?
2. **Backward compatibility**: How long to support current monolithic API?
3. **KiCad project file (.kicad_pro) parsing**: Which plugin owns this?
4. **Plugin conflicts**: What if two plugins register same CLI command? (Low priority - unlikely with bundled plugins)
5. **Configuration system**: Per-plugin config files? Global config? Environment variables?

## Benefits

**For Users:**
- Same functionality, better architecture underneath
- Can install only needed plugins (future third-party extensions)
- Foundation plugins could work with other tools (e.g., separate KiCad utilities)

**For Developers:**
- Clear boundaries between components
- Independent evolution via semver
- Test plugins in isolation
- Foundation plugins reusable across projects

**For Project:**
- Fight bloat: new parsers update `value_parser` plugin, don't add to monolith
- Enable ecosystem: community can extend without forking
- Future-proof: when official KiCad API ships, swap `kicad_parser` implementation without breaking dependents
- Potential ecosystem value: foundation plugins become de facto KiCad data API

## Conclusion

Plugins as Python packages - nothing more, nothing less. Use standard packaging tools (pip, pyproject.toml, semver) instead of custom infrastructure. Simple pattern repeated: foundation plugins provide primitives, business logic plugins compose them into workflows, all evolve independently.

Start greenfield to prove the pattern, then migrate incrementally. Foundation plugins designed for external reuse from the start.
