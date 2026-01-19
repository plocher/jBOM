# Layer Responsibilities

This document defines the clear responsibilities, constraints, and interaction patterns for each layer in jBOM's domain-centric architecture.

## Layer Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Interface Layer                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  CLI Commands   │  │  GUI Components │  │ KiCad Plugins│ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                   Application Layer                         │
│                 (Workflow Orchestration)                    │
│  • Input Translation    • Service Orchestration            │
│  • Output Formatting    • Error Translation                │
├─────────────────────────────────────────────────────────────┤
│                 Domain Services Layer                       │
│                (Business Logic Core)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Schematic   │  │    PCB      │  │Manufacturing│         │
│  │   Reader    │  │   Reader    │  │  Services   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│                 Domain Model Layer                          │
│              (Shared Domain Concepts)                       │
│  • Component Entities    • Configuration Objects           │
│  • Value Objects        • Domain Constants                 │
│  • Pure Functions       • Business Rules                   │
└─────────────────────────────────────────────────────────────┘
```

## Domain Model Layer

### Purpose
Provides shared domain concepts, value objects, and pure functions used across all bounded contexts.

### Responsibilities
- **Domain Entities**: Core business objects with identity (Component, InventoryItem, BoardModel)
- **Value Objects**: Immutable domain concepts without identity (BOMEntry, PlacementData)
- **Configuration Objects**: Type-safe service configuration with domain validation
- **Pure Functions**: Stateless domain calculations and transformations
- **Domain Constants**: Business rules, categorization mappings, validation constraints
- **File Format Utilities**: Bridge between external file formats and domain objects

### Characteristics
- **Stateless**: No business process state, only data and pure functions
- **Immutable**: Prefer frozen dataclasses for value objects
- **Domain-Focused**: Electronics terminology and business rule encoding
- **Cross-Cutting**: Concepts used by multiple bounded contexts

### Constraints
- **No Dependencies**: Only standard library and typing imports
- **Pure Functions**: No side effects or external system interactions
- **Domain Language**: Consistent electronics domain terminology
- **Validation**: Business rules encoded in object validation methods

## Domain Services Layer

### Purpose
Encapsulates core business operations and domain expertise as stateful, configurable objects.

### Responsibilities
- **Business Logic**: Pure domain operations without infrastructure concerns
- **Domain Rules**: Implementation of complex business rules and domain knowledge
- **Service Composition**: Using other domain services for specialized operations
- **Configuration Management**: Constructor-based behavior customization
- **Domain Workflows**: Complete business operations within bounded contexts

### Characteristics
- **Stateful Objects**: Constructor-configured behavior and operational state
- **Single Responsibility**: Each service handles one bounded domain context
- **Constructor Configuration**: Behavior established through parameters and options
- **Business Purity**: No CLI, file I/O, or infrastructure dependencies

### Constraints
- **Domain Dependencies Only**: Can import domain models and other domain services
- **No Application Layer**: Cannot import from CLI, application layer, or interface frameworks
- **No Side Effects**: No print statements, file operations, or external API calls
- **Interface Agnostic**: Must work identically across different calling interfaces

### Service Categories

#### Data Extraction Services
- **Purpose**: Extract domain objects from external file formats
- **Examples**: `SchematicReader`, `PCBReader`, `InventoryReader`
- **Pattern**: File path input → Domain objects output

#### Processing Services
- **Purpose**: Transform domain objects through business operations
- **Examples**: `BOMGenerator`, `POSGenerator`, `InventoryMatcher`
- **Pattern**: Domain objects input → Processed domain objects output

#### Analysis Services
- **Purpose**: Analyze domain objects and provide business insights
- **Examples**: Component analysis, placement validation, procurement calculation
- **Pattern**: Domain objects input → Analysis results output

## Application Layer

### Purpose
Orchestrates domain services and manages interface workflows without containing business logic.

### Responsibilities
- **Input Translation**: Convert interface arguments to domain configuration objects
- **Service Orchestration**: Coordinate multiple domain services for complex workflows
- **Output Formatting**: Adapt domain results for interface-specific presentation
- **Error Translation**: Convert domain exceptions to user-appropriate messages
- **Workflow Management**: Handle multi-service operations and business processes

### Characteristics
- **Stateless Orchestration**: No business state, only workflow coordination
- **Interface Adaptation**: Bridge between interface concerns and domain operations
- **Service Composition**: Coordinate domain services without implementing business logic
- **Error Handling**: Translate domain exceptions to user-friendly messages

### Constraints
- **No Business Logic**: Cannot contain domain rules or business calculations
- **Stateless Operations**: No instance variables or persistent state
- **Domain Service Orchestration**: Use domain services, don't reimplement their logic
- **Interface Translation**: Handle conversion between interface and domain concerns

### Application Layer Patterns

#### Command Handler Pattern
```
1. Parse interface arguments
2. Translate to domain configuration objects
3. Instantiate and configure domain services
4. Execute service operations in logical sequence
5. Format results for interface presentation
6. Handle errors with appropriate user feedback
```

#### Service Composition Pattern
```python
# Coordinate services without business logic
reader = SchematicReader(options)
generator = BOMGenerator(aggregation_strategy)
matcher = InventoryMatcher()

# Linear workflow orchestration
components = reader.read_schematic(file_path)
bom_data = generator.generate_bom_data(components)
enhanced_bom = matcher.enhance_bom_with_inventory(bom_data, inventory)
```

## Interface Layer

### Purpose
Provides user and system interfaces built on the application layer foundation.

### Responsibilities
- **User Interface**: CLI commands, GUI components, web interfaces
- **Framework Integration**: Interface-specific framework implementations
- **Presentation Logic**: Display formatting, user interaction handling
- **Interface Protocols**: API endpoints, plugin interfaces, configuration management

### Characteristics
- **Framework-Specific**: Uses interface frameworks (argparse, GUI toolkits, web frameworks)
- **Presentation Focus**: Handles user interface and display concerns
- **Application Layer Dependent**: Builds on application layer services
- **Multiple Implementations**: Same functionality across different interface types

### Constraints
- **No Business Logic**: All domain operations handled by lower layers
- **Framework Isolation**: Interface framework dependencies isolated to this layer
- **Application Layer Use**: Must use application layer, not domain services directly
- **Interface-Specific**: Implementation details specific to interface type

## Dependency Management

### Dependency Rules
1. **Inward Flow**: Dependencies flow toward domain core
2. **Layer Isolation**: No dependencies on higher layers
3. **Clear Boundaries**: Each layer has well-defined import constraints
4. **Shared Concepts**: Domain model layer accessible to all other layers

### Allowed Dependencies
```
Interface Layer      → Application Layer, Domain Model Layer
Application Layer    → Domain Services Layer, Domain Model Layer
Domain Services Layer → Domain Model Layer, Other Domain Services
Domain Model Layer   → Standard Library Only
```

### Forbidden Dependencies
- Domain Services → Application Layer or Interface Layer
- Domain Model → Any application-specific concerns
- Cross-layer circular dependencies
- Infrastructure concerns in domain layers

### Boundary Enforcement
Currently enforced through:
- **Code Review**: Architectural discipline during development
- **Layer Structure**: Clear filesystem organization by layer
- **Import Conventions**: Established patterns for cross-layer communication

Future enforcement mechanisms:
- **Static Analysis**: Automated dependency checking
- **Architecture Tests**: Unit tests validating dependency constraints
- **CI/CD Integration**: Automated boundary validation in build pipeline

## Benefits

### Clear Separation of Concerns
- Each layer has distinct, well-defined responsibilities
- Business logic isolated from interface and infrastructure concerns
- Clear boundaries prevent coupling violations

### Interface Flexibility
- Multiple interface types supported without domain changes
- Application layer provides consistent orchestration across interfaces
- Domain services reusable across different interface implementations

### Evolutionary Design
- New capabilities added without modifying existing layers
- Layer boundaries support incremental enhancement
- Clear extension points through established patterns

### Testing Strategy
- **Domain Services**: Unit tests with domain objects
- **Application Layer**: Integration tests with mocked domain services
- **Interface Layer**: End-to-end tests with real workflows
- **Cross-Layer**: Validation of architectural constraints

This layered architecture provides the foundation for maintainable, extensible software that clearly separates domain expertise from interface and infrastructure concerns.
