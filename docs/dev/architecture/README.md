# jBOM Architecture

This documentation establishes the authoritative architectural principles, design patterns, and structural constraints for the jBOM system.

## Architectural Style: Domain-Centric Design

jBOM implements a **domain-centric architecture** that prioritizes business logic clarity and interface flexibility through layered responsibilities and clear dependency management.

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Interface Layer                          │
├─────────────────────────────────────────────────────────────┤
│                   Application Layer                         │
│         (Contract-Oriented Job Orchestration)               │
├─────────────────────────────────────────────────────────────┤
│                 Domain Services Layer                       │
│               (Business Logic Core)                         │
├─────────────────────────────────────────────────────────────┤
│                 Domain Model Layer                          │
│              (Shared Concepts)                              │
└─────────────────────────────────────────────────────────────┘
```

### Core Design Principles

#### 1. Domain-Driven Design (DDD)
- **Ubiquitous Language**: Consistent electronics domain terminology throughout system
- **Bounded Contexts**: Clear service boundaries around related business functionality
- **Domain Models**: Rich business entities expressing domain rules and constraints
- **Business Logic Isolation**: Pure domain operations independent of infrastructure

#### 2. Layered Architecture
- **Clear Responsibilities**: Each layer has distinct, well-defined purposes
- **Dependency Inversion**: Dependencies flow inward toward domain core
- **Interface Agnostic**: Domain services support multiple interface types (CLI, GUI, API)
- **Evolutionary Design**: New capabilities added without modifying existing layers

#### 3. Composition Over Inheritance
- **Service Collaboration**: Business workflows through service composition
- **Configuration-Driven Behavior**: Runtime flexibility through parameter-based customization
- **Stateful Services**: Business operations encapsulated in configurable domain objects
- **Pure Functions**: Shared utilities as stateless, side-effect-free operations

## Layer Architecture

### Domain Services Layer
**Purpose**: Encapsulates core business operations and domain expertise
**Characteristics**: Stateful objects, constructor-configured behavior, pure business logic
**Examples**: BOM generation, component matching, schematic parsing, PCB processing

### Application Layer
**Purpose**: Orchestrates domain services and manages interface workflows
**Characteristics**: Stateless orchestration, input translation, output formatting
**Examples**: CLI command handlers, workflow coordination, error translation

### Domain Model Layer
**Purpose**: Shared domain concepts and cross-cutting utilities
**Characteristics**: Immutable value objects, pure functions, domain constants
**Examples**: Component entities, configuration objects, business rules

### Interface Layer
**Purpose**: User and system interfaces built on application layer
**Characteristics**: Framework-specific implementations, presentation logic
**Examples**: CLI commands, GUI components, web APIs, KiCad plugins

## Architectural Constraints

### Dependency Rules
1. **Inward Dependencies**: Higher layers depend on lower layers only
2. **No Circular Dependencies**: Clean dependency graph with clear direction
3. **Domain Isolation**: Domain layers cannot import from application or interface layers
4. **Shared Concepts**: Domain models provide common abstractions across layers

### Design Constraints
1. **Single Responsibility**: Each service handles one bounded domain context
2. **Configuration at Construction**: Service behavior established through constructor parameters
3. **Domain Purity**: Services contain only business logic with no infrastructure concerns
4. **Interface Agnostic**: Services work identically across different interface types

## Benefits

### Modularity
- Services testable in isolation with clear boundaries
- Business logic reusable across multiple interface types
- Clear separation between domain rules and interface concerns

### Flexibility
- Multiple interface patterns supported without domain changes
- Service composition enables complex workflows from simple components
- Configuration-driven behavior allows runtime customization

### Maintainability
- Architectural constraints prevent coupling violations
- Clear layer responsibilities reduce cognitive complexity
- Domain-focused organization matches business understanding

### Extensibility
- New services integrate through established patterns
- Additional interfaces built on existing domain services
- Evolutionary design supports incremental capability expansion

## Documentation Structure

This architecture documentation is organized as the authoritative source of design principles:

- **[Domain-Centric Design](domain-centric-design.md)** - DDD principles and bounded contexts
- **[Layer Responsibilities](layer-responsibilities.md)** - Detailed layer definitions and constraints
- **[Design Patterns](design-patterns.md)** - Established patterns used throughout jBOM
- **[Integration Patterns](integration-patterns.md)** - Service composition and layer interaction
- **[Shared Job Execution Contracts](job-contracts.md)** - adapter-neutral `JobRequest` / `JobContext` / `JobEvent` / `JobResult` contracts and shared application-layer runner semantics; legacy workflow registry patterns are retired
- **[Component Attribute Enrichment](component-attribute-enrichment.md)** - 3-camp attribute model, lifecycle phases, domain defaults, and write-back rules
- **[EagleLib2KiCad Adapter Requirements](eaglelib2kicad-adapter-requirements.md)** - Service-surface-first integration requirements for Eagle/KiCad library contexts
- **[ADR 0003: Search Heuristic Signal Framework](adr/0003-search-heuristic-signal-framework.md)** - typed relevance signal contract, diagnostics explainability, and defaults-governed package token baseline
- **[ADR 0004: EagleLib2KiCad Integration Boundary](adr/0004-eaglelib2kicad-adapter-boundary.md)** - service-surface-first contract policy and no-parallel-adapter-layer decision

## Architectural Evolution

Documentation of how jBOM's architecture evolved:

- **[Why jBOM-New](why-jbom-new.md)** - Refactoring summary and architectural decisions that led to simplified design
- **[Project-Centric Design](project-centric-design.md)** - Historical migration from complex plugin-based architecture

For implementation guidance, see:
- **Source Code READMEs** - Layer-specific developer overviews
- **[Developer Tutorials](../tutorial/README.md)** - Step-by-step implementation patterns

This architectural foundation supports jBOM's goal of providing flexible, maintainable business logic that can power multiple interface types while maintaining clear domain boundaries and design consistency.
