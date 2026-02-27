# jBOM Developer Tutorial: Adding a New Service

This tutorial series demonstrates jBOM's development approach by walking through adding a new POS (Position) service. The tutorial assumes you are an experienced software engineer familiar with design patterns and want to understand jBOM's architectural approach.

## Tutorial Goal

Add a new POS service to jBOM that generates component placement files from KiCad PCB data, following jBOM's established patterns and TDD workflow.

## Prerequisites

Before implementing any service, you need to understand jBOM's design language and architectural patterns.

## jBOM's Design Philosophy

### Domain-Centric Architecture

jBOM implements a domain-centric architecture with clear layer responsibilities:

- **Domain Services Layer** (`services/`) - Pure business logic, stateful process objects
- **Application Layer** (`cli/`) - Interface orchestration, stateless workflow managers
- **Domain Model Layer** (`common/`) - Shared domain concepts and pure functions
- **Configuration Layer** (`config/`) - Domain and application configuration

### Domain-Driven Design Patterns

**Services as Stateful Domain Objects**
- Services have `__init__` methods configuring business behavior
- They maintain process state and encapsulate domain operations
- Pure business logic with no infrastructure dependencies

**Application Layer as Stateless Orchestrators**
- Commands coordinate domain services but contain no business logic
- Translate between interface concerns and domain concepts
- Thin orchestration layer handling workflow-specific concerns

**Domain Model Layer for Shared Concepts**
- Immutable value objects representing business concepts
- Pure functions for domain calculations
- Cross-cutting utilities with no business state

### Service Design Patterns

**Strategy Pattern**: Configurable behavior through constructor injection
```python
generator = BOMGenerator(aggregation_strategy="value_footprint")
matcher = InventoryMatcher(matching_criteria)
```

**Factory Pattern**: Complex object creation within services
```python
def _build_processors(self) -> Dict[str, ComponentProcessor]:
    return {'resistor': ResistorProcessor(), 'capacitor': CapacitorProcessor()}
```

**Command/Query Separation**: Distinct operations vs data retrieval
- Commands: `generate_bom_data()`, `create_inventory()`
- Queries: `validate_bom()`, `list_components()`

## Architectural Constraints

**Dependency Direction**: Application Layer → Domain Services → Domain Models (never outward)
**Service Autonomy**: Testable in isolation, interface-agnostic
**State Management**:
- Domain Services Layer: Business process state
- Domain Model Layer: Stateless and pure
- Application Layer: Stateless orchestrators

## Development Workflow

jBOM uses **Test-Driven Development** with Gherkin specifications:

1. **Feature Definition**: Write Gherkin scenarios describing user behavior
2. **Step Implementation**: Create step functions that orchestrate services
3. **Service Development**: Build domain services to fulfill business requirements
4. **CLI Integration**: Add command adapters for user interface

## Key Integration Points

**Configuration Objects**: Type-safe options from `common/options.py`
**Domain Models**: Shared concepts from `common/types.py`
**File Parsing**: Utilities in `common/sexp_parser.py`
**Error Handling**: Domain-specific exceptions with user-friendly messages

## Anti-Patterns to Avoid

- Services depending on CLI modules
- Business logic in CLI commands
- Infrastructure concerns in domain services
- Raw CLI args passed to domain services
- Print statements in service methods

## Next Steps

The following tutorials demonstrate these principles in practice:

- [Implementation Tutorial](README.implementation.md) - Step-by-step service development
- [Integration Tutorial](README.integration.md) - CLI and testing integration
- [Documentation Tutorial](README.documentation.md) - Maintaining project documentation

Each tutorial builds on the POS service example while highlighting jBOM's architectural decisions and development practices.
