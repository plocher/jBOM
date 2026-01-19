# Domain Model Layer

This directory implements jBOM's **Domain Model Layer** - shared domain concepts, value objects, and pure functions used across all bounded contexts.

## Domain Model Characteristics

**Immutable Value Objects**: Business concepts represented as frozen dataclasses with domain validation
**Pure Functions**: Stateless operations for domain calculations and transformations
**Cross-Cutting Utilities**: Infrastructure-agnostic helper functions shared across services
**Type Safety**: Configuration objects ensuring domain constraint validation

## Key Domain Modules

### Core Domain Models - [`types.py`](types.py)
**Purpose**: Fundamental business entities and value objects
**Key Models**: Component entities, BOM data structures, Inventory items, Schematic representations
**Characteristics**: Identity-based entities with domain behavior methods and business rule validation

### Configuration Objects - [`options.py`](options.py)
**Purpose**: Type-safe configuration for domain service behavior
**Key Models**: Service configuration objects, Strategy enumerations, Processing options
**Characteristics**: Immutable frozen dataclasses with domain constraint validation

### PCB Domain Models - [`pcb_types.py`](pcb_types.py)
**Purpose**: Physical board layout and manufacturing domain concepts
**Key Models**: Board representations, Component placement data, Manufacturing specifications
**Characteristics**: Coordinate systems, layer management, manufacturing constraints

### Domain Constants - [`constants.py`](constants.py)
**Purpose**: Business rules and domain knowledge centralization
**Key Concepts**: Component categorization rules, Manufacturing standards, File format specifications
**Characteristics**: Immutable constants encoding electronics domain expertise

### Domain Utilities - [`component_utils.py`](component_utils.py)
**Purpose**: Pure functions for component analysis and transformation
**Key Functions**: Component type detection, Value parsing, Similarity calculations
**Characteristics**: Stateless functions implementing electronics domain logic

### File Format Utilities - [`sexp_parser.py`](sexp_parser.py)
**Purpose**: Infrastructure support for KiCad file format parsing
**Key Functions**: S-expression parsing, Domain object conversion, File validation
**Characteristics**: Bridge between file formats and domain objects

## Domain Model Principles

### Ubiquitous Language
Consistent terminology from electronics domain used across all contexts: "reference designator", "component value", "footprint", rather than generic technical terms.

### Domain Invariants
Business rules encoded directly in domain objects through validation methods, ensuring domain constraints are maintained throughout the system.

### Cross-Context Concepts
Shared abstractions like aggregation strategies and configuration enumerations that span multiple bounded contexts while maintaining domain meaning.

## Development Guidelines

### Domain Model Creation
- **Cross-Context Usage**: Ensure concepts are needed by multiple services or application commands
- **Domain Language**: Use terminology from electronics domain, not generic programming terms
- **Business Rules**: Encode domain constraints through validation methods and properties
- **Immutability**: Prefer frozen dataclasses for value objects to ensure consistency

### Testing Strategy
- **Invariant Tests**: Validate domain rules and business constraints
- **Function Tests**: Test pure domain logic with representative data
- **Identity Tests**: Verify entity identity and equality behavior
- **Integration Tests**: Ensure domain models work correctly with services

### Evolution Guidelines
- **Backward Compatibility**: Changes to shared models affect all dependent services
- **Domain Integrity**: Maintain consistency of ubiquitous language across contexts
- **Minimal Interface**: Keep shared concepts focused on truly cross-cutting concerns

## Implementation Guidance

For detailed domain modeling patterns, testing strategies, and step-by-step development guidance, see the [Developer Tutorial Series](../../docs/tutorial/README.md).
