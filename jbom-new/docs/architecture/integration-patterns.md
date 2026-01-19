# Integration Patterns

This document defines how services compose and layers interact within jBOM's domain-centric architecture.

## Service Composition Patterns

### Linear Composition
Sequential service operations where output of one service becomes input to the next.

**Use Case**: Standard processing pipelines with clear data flow
**Pattern**: Service A → Data → Service B → Data → Service C
**Benefits**: Simple reasoning, clear data flow, easy testing

```
Schematic Processing Pipeline:
File Path → SchematicReader → Components → BOMGenerator → BOMData
```

### Parallel Composition
Independent services operating on the same data simultaneously.

**Use Case**: Multiple analyses or outputs from the same source data
**Pattern**: Data → [Service A, Service B, Service C] → [Result A, Result B, Result C]
**Benefits**: Performance optimization, independent operations, parallel testing

```
Multi-Output Generation:
Components → [BOMGenerator, StatisticsAnalyzer, ComponentValidator]
    ↓              ↓                    ↓                      ↓
BOMData    StatisticsReport    ValidationResults
```

### Enhancement Composition
Services that augment existing data with additional information.

**Use Case**: Adding inventory data, procurement information, or analysis results
**Pattern**: Base Data + Enhancement Service → Enhanced Data
**Benefits**: Incremental enhancement, optional processing, modular capabilities

```
BOM Enhancement:
BOMData + InventoryMatcher → EnhancedBOMData (with availability info)
```

### Conditional Composition
Service workflows that vary based on configuration or data characteristics.

**Use Case**: Optional processing steps, feature toggles, data-dependent workflows
**Pattern**: Data + Condition → [Service Path A] or [Service Path B]
**Benefits**: Flexible workflows, configuration-driven behavior, efficient processing

```
Conditional Processing:
if inventory_file_provided:
    workflow = SchematicReader → BOMGenerator → InventoryMatcher
else:
    workflow = SchematicReader → BOMGenerator
```

## Layer Interaction Patterns

### Interface → Application → Domain
Standard request flow for user-initiated operations.

**Flow**: User Input → Interface Translation → Service Orchestration → Domain Processing → Result Formatting
**Characteristics**: Stateless orchestration, clear responsibility boundaries, consistent error handling

```
CLI Command Execution:
1. CLI parses arguments
2. CLI translates to domain configuration objects
3. CLI instantiates and orchestrates domain services
4. Domain services execute business logic
5. CLI formats results for presentation
6. CLI handles errors and user feedback
```

### Domain → Domain
Direct service-to-service communication within the domain layer.

**Flow**: Service A calls Service B directly for specialized domain operations
**Characteristics**: Domain object passing, business logic composition, bounded context respect

```
Service Composition:
class InventoryMatcher:
    def enhance_bom_with_inventory(self, bom_data, inventory_file):
        # Use InventoryReader service for file processing
        reader = InventoryReader(inventory_file)
        inventory_items = reader.load()
        # Perform matching logic
        return self._apply_matching(bom_data, inventory_items)
```

### Configuration → Behavior
Configuration objects driving service behavior variations.

**Flow**: Configuration Object → Service Constructor → Behavior Modification
**Characteristics**: Type-safe configuration, domain validation, immutable behavior contracts

```
Configuration-Driven Behavior:
options = PlacementOptions(smd_only=True, units="mm", layer_filter="TOP")
generator = POSGenerator(options)
# Generator behavior now configured for SMD-only, metric, top-layer processing
```

## Error Flow Patterns

### Domain Exception → Interface Error
Domain errors translated to appropriate interface responses.

**Flow**: Domain Exception → Application Layer Translation → Interface-Specific Error Response
**Characteristics**: Error context preservation, user-friendly messaging, technical detail handling

```
Error Translation Flow:
Domain Service raises ComponentProcessingError
    ↓
Application Layer catches and translates to user message
    ↓
Interface Layer presents appropriate error (CLI message, HTTP status, etc.)
```

### Validation Error Cascade
Configuration validation errors preventing invalid service instantiation.

**Flow**: Invalid Configuration → Validation Error → Early Failure → User Feedback
**Characteristics**: Fail-fast behavior, clear validation messages, prevented invalid operations

```
Configuration Validation:
PlacementOptions(units="invalid") → ValidationError → User sees clear error message
```

## Data Flow Patterns

### Domain Object Passing
Services communicate through well-defined domain objects rather than primitive types.

**Purpose**: Maintain domain integrity, enable rich behavior, ensure type safety
**Implementation**: Services accept and return domain entities and value objects
**Benefits**: Type safety, domain behavior availability, clear contracts

```
Domain Object Flow:
SchematicReader.read_schematic(file_path) → List[Component]
    ↓
BOMGenerator.generate_bom_data(components) → BOMData
    ↓
InventoryMatcher.enhance_bom_with_inventory(bom_data, inventory) → EnhancedBOMData
```

### Immutable Data Transformation
Services create new objects rather than modifying input objects.

**Purpose**: Prevent side effects, enable functional composition, simplify reasoning
**Implementation**: Services return new domain objects based on input transformation
**Benefits**: No side effects, functional composition, easier testing and debugging

```
Immutable Transformation:
original_components = [Component(...), ...]
filtered_components = filter_service.apply_filters(original_components, filters)
# original_components unchanged, filtered_components is new list
```

### Configuration Inheritance
Services inherit configuration from parent configuration objects.

**Purpose**: Consistent behavior across related services, reduced configuration duplication
**Implementation**: Configuration objects with inheritance relationships
**Benefits**: Consistent configuration, reduced duplication, hierarchical behavior control

```
Configuration Inheritance:
base_options = GeneratorOptions(verbose=True, debug=False)
bom_options = BOMOptions(base=base_options, smd_only=True)
# BOM service inherits verbose and debug settings
```

## Composition Coordination Patterns

### Application Layer Orchestration
Complex workflows coordinated by application layer without business logic.

**Purpose**: Separate workflow orchestration from business logic
**Implementation**: Application layer coordinates services in appropriate sequence
**Benefits**: Clear orchestration, business logic isolation, testable workflows

```
Application Layer Orchestration:
def generate_enhanced_bom(schematic_file, inventory_file, output_format):
    # Service instantiation
    reader = SchematicReader()
    generator = BOMGenerator("value_footprint")
    matcher = InventoryMatcher()
    formatter = OutputFormatter(output_format)

    # Workflow coordination
    components = reader.read_schematic(schematic_file)
    bom_data = generator.generate_bom_data(components)
    enhanced_bom = matcher.enhance_bom_with_inventory(bom_data, inventory_file)
    formatted_output = formatter.format_bom(enhanced_bom)

    return formatted_output
```

### Service Factory Pattern
Centralized service creation with appropriate configuration.

**Purpose**: Consistent service instantiation, configuration management, dependency injection
**Implementation**: Factory functions that create properly configured services
**Benefits**: Consistent configuration, centralized creation logic, easier testing

```
Service Factory:
def create_bom_workflow_services(options):
    """Create services for BOM generation workflow."""
    reader_options = SchematicOptions(
        verbose=options.verbose,
        include_dnp=options.include_dnp
    )

    return {
        'reader': SchematicReader(reader_options),
        'generator': BOMGenerator(options.aggregation_strategy),
        'matcher': InventoryMatcher() if options.inventory_file else None
    }
```

### Event-Driven Integration
Services communicate through domain events for loose coupling.

**Purpose**: Loose coupling between services, extensible workflows, audit trails
**Implementation**: Services emit domain events that other services can handle
**Benefits**: Loose coupling, extensible processing, clear event history

```
Event-Driven Flow:
BOMGenerator generates BOM → emits BOMGeneratedEvent
    ↓
InventoryMatcher handles BOMGeneratedEvent → enhances with inventory
    ↓
StatisticsCollector handles BOMGeneratedEvent → updates project statistics
```

## Testing Integration Patterns

### Service Isolation Testing
Test services independently with mock dependencies and domain objects.

**Purpose**: Validate business logic without external dependencies
**Implementation**: Unit tests with domain object inputs and mock service dependencies
**Benefits**: Fast tests, clear failure isolation, business logic focus

### Workflow Integration Testing
Test service composition with real services and controlled data.

**Purpose**: Validate service orchestration and data flow
**Implementation**: Integration tests that exercise complete workflows
**Benefits**: Workflow validation, real service interaction, end-to-end confidence

### Contract Testing
Validate service interfaces remain stable across implementations.

**Purpose**: Ensure service contracts don't break during implementation changes
**Implementation**: Tests that validate service input/output contracts
**Benefits**: Interface stability, implementation flexibility, evolutionary design

These integration patterns ensure that jBOM's services compose cleanly while maintaining architectural boundaries and enabling flexible, maintainable workflows.
