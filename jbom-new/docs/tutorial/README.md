# jBOM Developer Tutorial Series

This tutorial series demonstrates jBOM's development methodology. The tutorials focus on jBOM's architectural patterns, design philosophy, and TDD workflow rather than implementation details.

## Tutorial Example: POS Service

The tutorial introduces a service and CLI and to generate Component Placement Lists for PCB fabrication.  The example is based on the production `jbom pos` implementation.

The premise for this feature is
  * **Business Domain**: Generate component placement files for PCB manufacturing
  * **User Interface**: `jbom pos board.kicad_pcb [options]`
  * **Key Services**: PCB Reader, POS Generator, Coordinate Transformer
  * **Integration Points**: CLI adapter, Gherkin features, unit/integration tests

This example demonstrates:
- Multi-service collaboration (PCB Reader → POS Generator)
- Configuration-driven behavior (units, filters, coordinate systems)
- Domain-specific business rules (SMD vs through-hole, layer separation)
- Manufacturing workflow integration (CSV output, console presentation)

## Using These Tutorials

1. Start with [Context](README.context.md) to understand jBOM's design philosophy and learn why jBOM made specific design decisions
2. Follow [Implementation](README.implementation.md) to see these test-driven design patterns used in service development
3. Study [Integration](README.integration.md) for CLI integration and layered testing strategies
4. Reference [Documentation](README.documentation.md) when adding new features

Each tutorial demonstrates extensibility points:
- **New Services**: Follow implementation patterns for domain logic
- **New CLI Commands**: Use integration patterns for interface adaptation
- **New Domain Models**: Apply shared foundational core patterns
- **New Testing**: Implement

## Beyond the Tutorials

After completing these tutorials, you should be able to:

- Add new domain services following jBOM's patterns
- Create CLI adapters that properly separate interface and business concerns
- Write appropriate tests for each architectural layer
- Maintain documentation that communicates architectural decisions
- Extend jBOM while preserving its design integrity

The tutorial approach emphasizes understanding architectural principles over implementation details to encourage consistency in feature evolution.

## Tutorial Structure

### [1. Context: Design Patterns & Architecture](README.context.md)

**Goal**: Understand jBOM's design philosophy before writing code.

**Topics Covered**:
- Domain-centric architecture with layered responsibilities
- Domain-driven design patterns (services, value objects, shared kernel)
- Architectural constraints and dependency management
- Development workflow using TDD and Gherkin specifications

**Key Takeaway**: jBOM uses stateful domain services for business logic, stateless application layer for workflow orchestration, and pure domain models for shared concepts.

### [2. Implementation: Building Domain Services](README.implementation.md)

**Goal**: Implement a complete domain service following jBOM's patterns.

**Topics Covered**:
- Gherkin feature definition and step implementation
- Domain model creation with business rules
- Service implementation using strategy and factory patterns
- Configuration objects and error handling
- Unit testing with domain-focused test data

**Key Takeaway**: Domain services encapsulate business operations as stateful objects with business logic, tested in isolation from infrastructure concerns.

### [3. Integration: CLI Adapters & Testing](README.integration.md)

**Goal**: Connect domain services to user interfaces through adapter patterns.

**Topics Covered**:
- Application layer command implementation as stateless orchestrators
- Input translation from interface arguments to domain configuration
- Output presentation adapting domain results for different formats
- Error translation from domain exceptions to user messages
- Integration and functional testing strategies

**Key Takeaway**: Application layer orchestrates workflows between interface concerns and domain services without containing business logic, enabling multiple interface types.

### [4. Documentation: Maintaining Project Docs](README.documentation.md)

**Goal**: Keep project documentation aligned with architectural changes.

**Topics Covered**:
- Documentation philosophy and audience-specific content
- CHANGELOG maintenance for version management
- Service and architecture documentation updates
- CLI help and user workflow documentation
- Testing documentation and maintenance guidelines

**Key Takeaway**: Documentation should reflect architectural decisions and provide practical guidance for different audiences (users, developers, architects).
