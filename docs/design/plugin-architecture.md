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

## Architectural Components

### System Structure

jBOM consists of four architectural layers with clear separation of concerns:

```
┌─────────────────────────────────────────────────┐
│     User Interface Layer                        │
│  ├─ CLI Driver (Entry Point)                   │
│  ├─ Configuration Loader                        │
│  └─ Output Formatter                            │
└─────────────────────────────────────────────────┘
                    ↓ requests
┌─────────────────────────────────────────────────┐
│     Command Routing Layer                       │
│  ├─ Command Registry                            │
│  ├─ Argument Parser (Schema-driven)            │
│  ├─ Validation Engine                           │
│  └─ Plugin Dispatcher                           │
└─────────────────────────────────────────────────┘
                    ↓ invokes
┌─────────────────────────────────────────────────┐
│     Plugin Ecosystem                            │
│  ├─ Foundation Plugins (Data Access)           │
│  └─ Business Logic Plugins (Domain Workflows)  │
└─────────────────────────────────────────────────┘
                    ↓ uses
┌─────────────────────────────────────────────────┐
│     Shared Services                             │
│  ├─ Configuration Manager                       │
│  ├─ Test Harness                                │
│  └─ Introspection Service                       │
└─────────────────────────────────────────────────┘
```

### Component Responsibilities

#### User Interface Layer

**CLI Driver (Entry Point)**
- Responsibility: Bootstrap application, initialize command routing
- Collaborates with: Configuration Loader, Command Registry
- Produces: Validated command request

**Configuration Loader**
- Responsibility: Discover and merge config files (env, project, user, system)
- Collaborates with: Configuration Manager
- Produces: Unified configuration object

**Output Formatter**
- Responsibility: Transform plugin results into user-facing formats (CSV, table, JSON)
- Collaborates with: Plugin results
- Consumes: Structured result objects

#### Command Routing Layer

**Command Registry**
- Responsibility: Maintain catalog of available commands and their schemas
- Collaborates with: Plugin Dispatcher, CLI Driver
- Data: Command metadata (name, plugin source, argument schema)

**Argument Parser**
- Responsibility: Parse raw CLI input against command schema
- Collaborates with: Validation Engine, Command Registry
- Produces: Structured argument object
- Pattern: Schema-driven processing (not hardcoded flags)

**Validation Engine**
- Responsibility: Validate parsed arguments against schema constraints
- Collaborates with: Argument Parser
- Checks: Required fields, type correctness, mutual exclusivity, value ranges
- Produces: Valid arguments or detailed error messages

**Plugin Dispatcher**
- Responsibility: Route validated request to appropriate plugin
- Collaborates with: Command Registry, Plugin Ecosystem
- Manages: Plugin lifecycle (load, execute, cleanup)

#### Plugin Ecosystem

**Foundation Plugins**
- Responsibility: Provide primitive data access (KiCad files, spreadsheets, value parsing)
- Collaborates with: Business Logic Plugins
- Interface: Public API functions (no UI concerns)
- Evolution: Semantic versioning enables independent evolution

**Business Logic Plugins**
- Responsibility: Implement domain workflows (BOM generation, validation, etc.)
- Collaborates with: Foundation Plugins, Shared Services
- Depends on: Foundation plugin APIs (declared via semver)
- Interface: Public API + optional CLI registration

#### Shared Services

**Configuration Manager**
- Responsibility: Provide configuration access to all components
- Pattern: Hierarchical namespaces (core, plugins.bom, fabricators)
- Interface: `get_config(namespace)` → config object

**Test Harness**
- Responsibility: Provide common test infrastructure to all plugins
- Pattern: Reusable fixtures, assertions, Gherkin steps
- Enables: Consistent testing across plugin ecosystem

**Introspection Service**
- Responsibility: Discover and document plugin APIs at runtime
- Pattern: Reflection over type hints and docstrings
- Produces: API documentation, command help, validation schemas

### Key Architectural Relationships

**CLI Driver → Command Registry**
- Driver queries registry: "What commands are available?"
- Registry responds with command catalog
- Pattern: Service locator

**Command Registry → Plugin Dispatcher**
- Registry provides plugin reference for command
- Dispatcher loads and invokes plugin
- Pattern: Factory + dependency injection

**Argument Parser → Validation Engine**
- Parser produces structured arguments
- Validator checks against schema
- Pattern: Pipeline processing

**Business Logic Plugin → Foundation Plugin**
- Business logic declares dependency (e.g., "kicad_parser>=1.0")
- Foundation provides stable API
- Pattern: Dependency inversion (depend on interface, not implementation)

**All Components → Configuration Manager**
- Components request configuration by namespace
- Manager provides merged, validated config
- Pattern: Centralized configuration service

**All Plugins → Test Harness**
- Plugins inherit common test patterns
- Harness provides fixtures and assertions
- Pattern: Template method (abstract test structure, concrete implementations)

### Architectural Qualities

**Modularity**
- Components have clear boundaries and single responsibilities
- Plugins are independently deployable Python packages
- Foundation plugins can be extracted as standalone tools

**Extensibility**
- New plugins add commands without core modification
- Foundation plugins add capabilities via minor version bumps
- Third-party plugins extend ecosystem via pip install

**Testability**
- Each layer tested in isolation
- Shared test harness ensures consistency
- Behavior-driven tests validate contracts

**Evolvability**
- Semantic versioning enables compatible changes
- Plugin dependencies isolate breaking changes
- Interface stability allows implementation swapping

**Discoverability**
- Introspection service exposes available APIs
- Command registry provides command catalog
- Type hints and docstrings enable auto-documentation

### Collaboration Flows

**User Request Processing (Primary Flow)**

1. **User** invokes: `jbom bom project/ -i inventory.csv -o bom.csv`

2. **CLI Driver**
   - Parses command name ("bom")
   - Queries Command Registry for "bom" schema
   - Passes raw args + schema to Argument Parser

3. **Argument Parser**
   - Breaks input into structured arguments
   - Sends to Validation Engine

4. **Validation Engine**
   - Checks against schema (required fields, types, constraints)
   - Either: Returns validated args OR sends error to Output Formatter

5. **Plugin Dispatcher**
   - Receives validated request
   - Loads "bom" plugin
   - Invokes plugin's execute function

6. **BOM Plugin (Business Logic)**
   - Requests config from Configuration Manager
   - Calls Foundation Plugins (kicad_parser, spreadsheet_io)
   - Performs BOM generation
   - Returns structured result

7. **Output Formatter**
   - Transforms result to requested format (CSV)
   - Writes to specified destination
   - Returns success/failure to user

**Plugin Discovery (Secondary Flow)**

1. **CLI Driver** (at startup)
   - Queries Introspection Service: "What plugins are available?"

2. **Introspection Service**
   - Scans installed packages for jBOM plugins
   - Reads plugin metadata (name, version, commands, API)
   - Registers with Command Registry

3. **Command Registry**
   - Builds command catalog
   - Provides to CLI Driver for help text

**Configuration Resolution (Cross-cutting)**

1. **Component** needs config: `config = get_config("plugins.bom")`

2. **Configuration Manager**
   - Loads configs from hierarchy (system → user → project → env)
   - Merges with precedence rules
   - Validates against schema
   - Caches and returns

3. **Component** uses config values for behavior customization

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
