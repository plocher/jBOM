# Application Layer

This directory contains jBOM's **Application Layer** - stateless command handlers that orchestrate domain services for user workflows.

For architectural principles and application layer patterns, see **[Application Layer](../../docs/architecture/layer-responsibilities.md#application-layer)** in the architecture documentation.

## Command Responsibilities by Domain

Each command handles a specific user workflow while orchestrating appropriate domain services:

## Command Implementation Notes

**Explicit Registration**: Commands register in `main.py` composition root
**Service Orchestration**: Coordinate domain services without implementing business logic
**Stateless Handlers**: Pure functions that translate, orchestrate, and format

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

## Development Guidance

Commands implement the application layer patterns of input translation, service orchestration, output formatting, and error handling.

## Implementation Guidance

For detailed command implementation patterns, testing strategies, and step-by-step development guidance, see the [Developer Tutorial Series](../../docs/tutorial/README.md).
