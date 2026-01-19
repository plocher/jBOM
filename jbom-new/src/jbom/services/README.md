# Domain Services Layer

This directory implements the business logic core of jBOM as **Domain Services** - stateful objects that encapsulate complex business operations and domain knowledge.

## Domain Service Characteristics

**Stateful Business Objects**: Services maintain configuration and operational state through constructor parameters
**Business Process Encapsulation**: Each service represents a complete domain operation or business capability
**Configurable Behavior**: Service behavior customized through constructor parameters and options objects
**Infrastructure Independence**: Pure domain logic with no external system dependencies

## Service Boundaries by Domain

Each service operates within a specific **bounded context** with clear domain responsibilities:

### Schematic Domain - [`schematic_reader.py`](schematic_reader.py)
**Responsibility**: Extract component data from KiCad schematic files
**Key Operations**: Hierarchical component resolution, DNP handling, multi-unit part processing

### BOM Domain - [`bom_generator.py`](bom_generator.py)
**Responsibility**: Aggregate components into bill-of-materials using configurable strategies
**Key Operations**: Component grouping, quantity calculation, reference list generation

### Inventory Domain - [`inventory_matcher.py`](inventory_matcher.py)
**Responsibility**: Match BOM requirements against available inventory
**Key Operations**: Availability checking, procurement calculation, allocation optimization

### PCB Layout Domain - [`pcb_reader.py`](pcb_reader.py)
**Responsibility**: Extract component placement data from KiCad PCB files
**Key Operations**: Coordinate extraction, layer handling, footprint processing

### Manufacturing Domain - [`pos_generator.py`](pos_generator.py)
**Responsibility**: Generate pick-and-place files for manufacturing processes
**Key Operations**: Coordinate transformation, component filtering, format standardization

## Service Integration Patterns

### Constructor Configuration
Services receive behavior configuration at instantiation through parameters like aggregation modes, matching criteria, and processing options.

### Service Composition
Services may use other services for specialized domain operations while avoiding workflow orchestration responsibilities.

### Domain Isolation
Services maintain clear boundaries - no CLI imports, no print statements, no application layer dependencies.

### Configurable Behavior
Behavior variations implemented through constructor parameters, conditional logic, and domain-specific processing methods.

## Development Guidelines

### Service Creation
- **Single Responsibility**: Each service handles one bounded domain context
- **Constructor Configuration**: Behavior defined through configuration parameters and options objects
- **Pure Domain Logic**: No infrastructure or interface dependencies
- **Domain Data**: Accept and return domain objects from `common/` layer

### Dependency Management
**Current Dependencies**: Other domain services, domain models (`common/`), standard libraries
**Avoided Dependencies**: Application layer (`cli/`), interface frameworks (argparse, click), external APIs without abstraction
**Note**: Boundaries enforced through code review and architectural discipline

### Testing Strategy
- **Unit Tests**: Isolated testing of business logic using domain objects
- **Integration Tests**: Service composition and collaboration verification
- **Domain Tests**: Business rule validation through Gherkin scenarios

## Implementation Guidance

For detailed implementation patterns, TDD workflow, and step-by-step service development guidance, see the [Developer Tutorial Series](../../docs/tutorial/README.md).
