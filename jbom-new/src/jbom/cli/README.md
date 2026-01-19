# Application Layer

This directory implements jBOM's **Application Layer** - stateless command handlers that orchestrate domain services and handle interface concerns.

## Application Layer Characteristics

**Stateless Orchestration**: Commands coordinate domain service workflows without maintaining state
**Interface Translation**: Convert between user interface arguments and domain configuration objects
**Workflow Management**: Handle multi-service operations and complex business processes
**Presentation Adaptation**: Format domain results for different output targets (console, files, pipes)

## Command Responsibilities by Domain

Each command handles a specific user workflow while orchestrating appropriate domain services:

## Command Organization

### Registration Pattern
Commands register explicitly in `main.py` composition root - no dynamic discovery mechanisms for maintainability and clarity.

### Orchestration Pattern
Commands coordinate multiple domain services for complete user workflows while maintaining clear separation between orchestration and business logic.

### Command/Query Separation
- **Commands**: Operations that perform business actions (generate, create, process)
- **Queries**: Read-only operations that retrieve and present information (list, validate, show)

## Key Commands

### [`main.py`](main.py) - Application Composition Root
**Responsibilities**: Command registration, argument parsing, global error handling, application lifecycle

### [`bom.py`](bom.py) - BOM Generation Workflows
**Interface**: `jbom bom <schematic> [options]`
**Domain Services**: Schematic Reader, BOM Generator, Inventory Matcher, Output Formatter
**Workflows**: Basic BOM generation, inventory-enhanced BOM, multi-format output

### [`inventory.py`](inventory.py) - Inventory Management
**Interfaces**: `jbom inventory generate|list|match [options]`
**Domain Services**: Inventory Manager, Component Matcher, Procurement Calculator
**Workflows**: Inventory creation, availability checking, procurement planning

### [`pos.py`](pos.py) - Manufacturing Position Files
**Interface**: `jbom pos <pcb> [options]`
**Domain Services**: PCB Reader, POS Generator, Coordinate Transformer
**Workflows**: Pick-and-place file generation, coordinate transformation, manufacturing filtering

## Application Layer Patterns

### Input Translation
Convert interface arguments to type-safe domain configuration objects, validating user input at the boundary.

### Output Presentation
Adapt domain results for different presentation targets: interactive console tables, scriptable CSV output, or formatted files.

### Error Translation
Translate domain exceptions into user-appropriate error messages while preserving technical context for troubleshooting.

### Workflow Orchestration
Coordinate multiple domain services in logical sequences while maintaining separation between orchestration and business logic.

## Development Guidelines

### Command Creation Principles
- **Single Interface Responsibility**: Each command handles one user-facing operation
- **Stateless Handlers**: No instance variables - pure function orchestration
- **Input Translation**: Convert interface arguments to domain configuration objects
- **Service Orchestration**: Coordinate domain services without implementing business logic
- **Output Adaptation**: Format domain results for appropriate presentation targets
- **Error Translation**: Convert domain exceptions to user-appropriate messages

### Testing Strategy
- **Orchestration Tests**: Verify correct service coordination with mocked dependencies
- **Translation Tests**: Validate input/output conversion between interface and domain
- **Integration Tests**: Test complete workflows with real domain services
- **Error Handling Tests**: Ensure proper exception translation and user feedback

## Implementation Guidance

For detailed command implementation patterns, testing strategies, and step-by-step development guidance, see the [Developer Tutorial Series](../../docs/tutorial/README.md).
