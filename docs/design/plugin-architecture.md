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

## Key Decisions

### Dependency Management
**Decision**: Use standard pip/Python packaging, not custom plugin loader.
**Rationale**: Don't reinvent package management. Pip handles versions, conflicts, resolution.

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
