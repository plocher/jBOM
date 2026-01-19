# jBOM Source Code Architecture

This directory contains the jBOM application organized around **Domain-Driven Design** principles with clear layer separation and dependency inversion.

## Architectural Pattern: Domain-Centric Architecture

jBOM implements a domain-centric architecture with clear layer responsibilities:

```
src/jbom/
├── services/     # Domain Services Layer - business logic core
├── cli/          # Application Layer - interface orchestration
├── common/       # Domain Model Layer - shared domain concepts
├── config/       # Configuration Layer - settings management
└── main.py       # Application composition root
```

## Source Code Organization

This source tree implements jBOM's domain-centric architecture with clear layer separation and dependency management. For complete architectural principles and design rationale, see **[Architecture Documentation](../docs/architecture/README.md)**.

## Layer Overviews

### [`services/`](jbom/services/README.md) - Domain Services Layer
**Purpose**: Encapsulates business operations as stateful, configurable domain objects
**Characteristics**:
- Constructor-configured behavior using Strategy and Factory patterns
- Command/Query separation with rich domain operations
- Pure business logic isolated from infrastructure concerns
- Autonomous services testable in isolation

**Key Services**: BOM Generation, Schematic Reading, Inventory Matching, PCB Processing

### [`cli/`](jbom/cli/README.md) - Application Layer
**Purpose**: Orchestrates domain services and handles interface concerns
**Characteristics**:
- Stateless command handlers coordinating service workflows
- Input translation from interface arguments to domain configurations
- Output formatting for different presentation needs
- Error translation from domain exceptions to user messages

**Key Commands**: BOM generation, Inventory management, Position file creation

### [`common/`](jbom/common/README.md) - Domain Model Layer
**Purpose**: Shared domain concepts and cross-cutting utilities
**Characteristics**:
- Immutable value objects representing business concepts
- Pure functions for domain calculations and transformations
- Type-safe configuration objects for service behavior
- Domain-specific constants and business rules

**Key Models**: Component entities, BOM data structures, Configuration options

### [`config/`](jbom/config/) - Configuration Layer
**Purpose**: Domain and application configuration management
**Characteristics**:
- Fabricator-specific output configurations
- Domain service behavior customization
- File format and processing options
- Integration settings for external tools

## Development Resources

- **[Architecture Documentation](../docs/architecture/README.md)** - Authoritative design principles and patterns
- **[Developer Tutorial Series](../docs/tutorial/README.md)** - Step-by-step implementation guidance
- **Layer READMEs** - Specific guidance for each architectural layer
