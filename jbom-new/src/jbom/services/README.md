# Domain Services Layer

This directory contains jBOM's **Domain Services Layer** - the business logic core implementing domain operations as stateful, configurable objects.

For architectural principles, design patterns, and service composition guidance, see **[Domain Services Layer](../../docs/architecture/layer-responsibilities.md#domain-services-layer)** in the architecture documentation.

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

## Service Implementation Notes

**Constructor Configuration**: Services configured through parameters and options objects at instantiation
**Domain Isolation**: No dependencies on application layer, CLI frameworks, or infrastructure concerns
**Service Composition**: Services may use other domain services for specialized operations

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
