# Domain Model Layer

This directory contains jBOM's **Domain Model Layer** - shared domain concepts, value objects, and utilities used across all bounded contexts.

For domain modeling principles and patterns, see **[Domain Model Layer](../../docs/architecture/layer-responsibilities.md#domain-model-layer)** in the architecture documentation.

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

## Domain Model Implementation Notes

**Ubiquitous Language**: Consistent electronics domain terminology throughout
**Domain Invariants**: Business rules encoded in object validation methods
**Cross-Context Concepts**: Shared abstractions spanning multiple bounded contexts

## Implementation Guidance

For detailed domain modeling patterns, testing strategies, and step-by-step development guidance, see the [Developer Tutorial Series](../../docs/tutorial/README.md).
