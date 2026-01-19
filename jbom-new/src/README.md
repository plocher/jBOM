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

## Core Design Principles

### Domain-Driven Design (DDD)
- **Domain Services**: Stateful objects encapsulating business operations
- **Domain Models**: Immutable value objects expressing business concepts
- **Bounded Contexts**: Clear service boundaries around related functionality

### Dependency Inversion
- **Inward Flow**: Application Layer → Domain Services → Domain Models
- **No Outward Dependencies**: Domain layer is independent of infrastructure
- **Interface Agnostic**: Services work with CLI, GUI, API, or plugin interfaces

### Layered Responsibilities
- **Domain Services Layer**: Business logic and domain operations
- **Application Layer**: Workflow orchestration and interface adaptation
- **Domain Model Layer**: Shared concepts and pure functions
- **Configuration Layer**: Settings and domain configuration

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

## Design Patterns

### Domain Service Pattern
- **Stateful Configuration**: Services configured via constructor with strategies and options
- **Business Process Encapsulation**: Each service represents a complete domain operation
- **Factory Methods**: Internal creation of domain-specific processors and transformers

### Command/Query Separation
- **Commands**: Operations that modify state or perform business actions
- **queries**: Read-only operations returning domain data without side effects
- **Clear Intent**: Method names explicitly indicate command vs query behavior

### Strategy Pattern
- **Configurable Behavior**: Services accept strategy objects for varying business rules
- **Runtime Flexibility**: Aggregation, filtering, and output strategies swappable
- **Domain-Specific**: Strategies encode business domain knowledge and constraints

## Service Composition

### Composition Root
- **Centralized Wiring**: `main.py` coordinates service instantiation and configuration
- **Dependency Injection**: Services receive dependencies through constructors
- **Application Lifecycle**: Manages startup, configuration, and resource cleanup

### Workflow Patterns
- **Simple Workflows**: Single service handling complete operations
- **Collaborative Workflows**: Multiple services coordinated by Application Layer
- **Pipeline Processing**: Sequential service calls with data transformation

## Architectural Constraints

### Dependency Flow
- **Inward Dependencies**: Application Layer depends on Domain Services, Domain Services depend on Domain Models
- **No Outward Dependencies**: Domain layers cannot import from Application Layer
- **Shared Concepts**: Domain Model Layer provides common concepts to all layers

### Service Autonomy
- **Isolation**: Services testable independently with mock dependencies
- **Composability**: Services combine for complex business operations
- **Interface Agnostic**: Same services support multiple interface types (CLI, GUI, API)

### Evolutionary Design
- **Open/Closed Principle**: New capabilities added without modifying existing services
- **Extension Points**: Strategy patterns and factory methods enable customization
- **Bounded Context Respect**: Clear service boundaries prevent uncontrolled coupling

## Development Guidance

For implementation details and step-by-step development guidance, see the [Developer Tutorial Series](../docs/tutorial/README.md).
