# ADR 0013: Domain-Centric Design
Date: 2026-02-25
Status: Accepted

## Context

These four documents — `domain-centric-design.md`, `design-patterns.md`, `layer-responsibilities.md`, and `integration-patterns.md` — were originally authored separately as reference material in `docs/dev/architecture/`. Together they record the architectural commitment to a domain-centric, layered design that underpins all of jBOM's services. They are unified here as a single ADR to make that commitment legible as one coherent decision.

jBOM's architecture prioritizes domain logic clarity through Domain-Driven Design principles, establishing clear bounded contexts and ubiquitous language throughout the electronics design domain.

## Decision

### Domain-Driven Design Principles

#### Ubiquitous Language
Consistent terminology from the electronics domain used throughout the system:

**Electronics Terminology**:
- **Reference Designator**: Component identifier (R1, C5, U3)
- **Component Value**: Electrical specification (10K, 100nF, STM32F4)
- **Symbol**: KiCad schematic library object for electrical representation
- **Footprint**: KiCad PCB library reference for physical representation
- **Package**: Physical component specification (0805, SOIC-8, QFN-32)
- **Component**: Generalized business concept encompassing symbol + footprint + properties
- **Library ID**: Schematic symbol reference (Device:R, Device:C)
- **Bill of Materials (BOM)**: Component procurement list with quantities
- **Pick and Place (POS)**: Manufacturing placement coordinates

**Domain Operations**:
- **Aggregation**: Grouping similar components for BOM generation
- **Matching**: Correlating components with inventory availability
- **Placement**: Physical component positioning on PCB
- **Enhancement**: Adding inventory data to component information

#### Bounded Contexts

Each bounded context represents a cohesive area of domain functionality with clear boundaries and responsibilities:

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Schematic     │  │      PCB        │  │  Manufacturing  │
│    Domain       │  │    Domain       │  │    Domain       │
├─────────────────┤  ├─────────────────┤  ├─────────────────┤
│• Component Data │  │• Placement Data │  │• BOM Generation │
│• Hierarchies    │  │• Coordinates    │  │• POS Files      │
│• Multi-unit     │  │• Layer Info     │  │• Procurement    │
│• DNP Handling   │  │• Rotations      │  │• Enhancement    │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

##### Schematic Domain
**Core Concepts**: Component extraction, hierarchy resolution, design rule application
**Business Rules**:
- DNP (Do Not Populate) components excluded by default
- Multi-unit components consolidated by reference designator
- Hierarchical designs flattened with proper reference prefixing
- Component properties merged from schematic and library sources

**Domain Service**: `SchematicReader`

##### PCB Domain
**Core Concepts**: Physical component placement, coordinate systems, manufacturing layers
**Business Rules**:
- Component placement coordinates in millimeters
- Layer designation (TOP/BOTTOM) determines assembly sequence
- Rotation angles normalized to manufacturing standards (0-360°)
- SMD components identified by footprint characteristics

**Domain Service**: `PCBReader`

##### Manufacturing Domain
**Core Concepts**: BOM aggregation, component procurement, placement file generation
**Business Rules**:
- Components aggregated by value/footprint combinations
- Quantity calculations include all instances of aggregated components
- Inventory matching enhances components with procurement data
- Manufacturing files formatted for pick-and-place equipment

**Domain Services**: `BOMGenerator`, `POSGenerator`, `InventoryMatcher`

#### Service Boundaries

Domain services maintain clear boundaries to prevent coupling and ensure single responsibility:

##### Boundary Enforcement
1. **Domain Isolation**: Services only import from domain model layer and other domain services
2. **Business Logic Purity**: No infrastructure concerns (CLI, file I/O, external APIs)
3. **Interface Agnostic**: Services work identically regardless of calling interface
4. **Configuration Independence**: Service behavior established through constructor parameters

##### Cross-Boundary Communication
Services communicate through well-defined domain objects:

```
SchematicReader → Component[] → BOMGenerator → BOMData
                                     ↓
PCBReader → BoardModel → POSGenerator → PlacementData[]
                              ↓
InventoryMatcher → EnhancedBOMData
```

### Domain Model Design

#### Entity vs Value Object Distinction

**Domain Entities**: Objects with identity representing core business concepts
- `Component`: Electronic component with reference designator identity
- `InventoryItem`: Inventory record with internal part number identity
- `BoardModel`: PCB design with file path identity

**Value Objects**: Immutable objects representing domain concepts through attributes
- `BOMEntry`: Aggregated component information without individual identity
- `PlacementData`: Component placement coordinates and orientation
- `ComponentValue`: Parsed electrical specification (numeric value + unit)

#### Domain Rules Encoding

Business rules encoded directly in domain objects:

```
@dataclass
class Component:
    """Domain Entity: Electronic component with business rule validation"""

    @property
    def is_passive_component(self) -> bool:
        """Domain rule: Passive vs active component classification"""
        return self.lib_id.startswith(('Device:R', 'Device:C', 'Device:L'))

    @property
    def component_family(self) -> str:
        """Domain rule: Component family derivation from library ID"""
        return self.lib_id.split(':')[0] if ':' in self.lib_id else 'Unknown'
```

#### Configuration Objects

Type-safe configuration capturing domain intentions:

```
@dataclass(frozen=True)
class PlacementOptions:
    """Manufacturing placement configuration with domain validation"""

    def __post_init__(self):
        """Domain constraint validation"""
        if self.units not in ("mm", "inch"):
            raise ValueError("Manufacturing units must be 'mm' or 'inch'")
        if self.layer_filter and self.layer_filter not in ("TOP", "BOTTOM"):
            raise ValueError("Layer filter must be 'TOP' or 'BOTTOM'")
```

### Domain Evolution

#### Adding New Bounded Contexts
1. **Domain Analysis**: Identify coherent business functionality requiring separate service
2. **Boundary Definition**: Establish clear input/output contracts with existing contexts
3. **Service Creation**: Implement domain service following established patterns
4. **Integration Testing**: Validate service composition with existing workflows

#### Extending Existing Contexts
1. **Backward Compatibility**: Maintain existing service contracts during enhancement
2. **Domain Integrity**: Ensure new functionality aligns with established domain language
3. **Boundary Respect**: Avoid feature creep that violates single responsibility
4. **Configuration Extension**: Add new behavior through constructor parameters

#### Cross-Cutting Concerns
Handle concerns that span multiple bounded contexts:

- **Configuration Management**: Shared options objects in domain model layer
- **File Format Parsing**: Utility functions bridging file formats to domain objects
- **Error Handling**: Domain-specific exceptions with business context
- **Validation**: Business rule validation in domain objects and configuration

### Design patterns

This document establishes the design patterns consistently applied throughout jBOM's domain-centric architecture.

#### Domain Service Patterns

##### Constructor Configuration Pattern
Services establish behavior through constructor parameters rather than method arguments or property settings.

**Purpose**: Ensure consistent service behavior throughout its lifecycle
**Implementation**: Constructor parameters configure strategies, options, and operational behavior
**Benefits**: Immutable service configuration, clear behavioral contracts, easier testing

```
Service Creation → Configuration → Operational Use
     ↓                  ↓              ↓
Constructor         Parameters      Method Calls
Parameters          Validate        Execute with
Configure           Domain          Configured
Behavior           Constraints      Behavior
```

##### Single Responsibility Pattern
Each domain service handles one bounded context with clear business purpose.

**Purpose**: Maintain clear service boundaries and prevent coupling
**Implementation**: Services focus on one area of domain expertise
**Benefits**: Testable in isolation, composable workflows, clear domain boundaries

**Service Categories**:
- **Data Extraction**: File format parsing to domain objects
- **Business Processing**: Domain transformations and calculations
- **Data Enhancement**: Augmenting domain objects with additional information

##### Service Composition Pattern
Complex workflows achieved by composing single-purpose services rather than creating monolithic operations.

**Purpose**: Enable flexible workflow construction from reusable components
**Implementation**: Services use other services for specialized domain operations
**Benefits**: Reusable components, flexible workflows, clear separation of concerns

```
Workflow Composition:
SchematicReader → BOMGenerator → InventoryMatcher → OutputFormatter
      ↓               ↓               ↓               ↓
   Components    →   BOMData    → EnhancedBOM   → FormattedOutput
```

#### Application Layer Patterns

##### Command Handler Pattern
Application layer commands orchestrate domain services without containing business logic.

**Purpose**: Separate interface concerns from domain operations
**Implementation**: Stateless functions that translate, orchestrate, and format
**Benefits**: Clean separation, interface flexibility, testable orchestration

**Command Structure**:
```
1. Input Validation & Translation
2. Domain Service Instantiation
3. Service Orchestration
4. Output Formatting
5. Error Handling
```

##### CLI-to-Workflow Extraction Pattern
Each command family (`bom`, `pos`, `gerbers`, `fab`) follows the same adapter-thin extraction contract.

**Purpose**: Make command refactors repeatable with one stable application-layer template
**Implementation**: Workflow logic lives in `src/jbom/application/<command>_workflow.py`; CLI files are adapters only
**Benefits**: Consistent contracts, easier cross-command reviews, predictable test shape, reusable across CLI and plugin adapters

**Extraction Contract**:
1. Define a request dataclass (`<Command>Request`) that normalizes adapter input.
2. Define explicit mode enum + result dataclass (`<Command>Mode`, `<Command>Result`) with mode-gated payload invariants.
3. Carry diagnostics as immutable result data (`tuple[str, ...]`) rather than callback side effects.
4. Keep CLI responsibilities limited to argument mapping, diagnostics rendering, output rendering, and exit code mapping.
5. Expose a single public method `.run(request)` — name reflects *what you do with the object*, not the internal mechanism.

##### Input Translation Pattern
Convert interface-specific arguments to type-safe domain configuration objects.

**Purpose**: Bridge between interface representations and domain concepts
**Implementation**: Translation functions create domain objects from interface data
**Benefits**: Type safety, domain validation, interface independence

##### Output Adaptation Pattern
Transform domain results for interface-appropriate presentation formats.

**Purpose**: Present domain data in interface-specific formats
**Implementation**: Formatting functions adapt domain objects for presentation
**Benefits**: Interface flexibility, consistent domain data, presentation separation

##### Error Translation Pattern
Convert domain exceptions to user-appropriate error messages and response codes.

**Purpose**: Provide meaningful error feedback while preserving domain exception information
**Implementation**: Exception handling that maps domain errors to interface responses
**Benefits**: User-friendly errors, technical context preservation, consistent error handling

#### Domain Model Patterns

##### Value Object Pattern
Immutable objects representing domain concepts through their attributes rather than identity.

**Purpose**: Model domain concepts that are defined by their characteristics
**Implementation**: Frozen dataclasses with domain validation in `__post_init__`
**Benefits**: Immutability, domain validation, clear semantic meaning

**Characteristics**:
- No identity-based equality
- Immutable after creation
- Domain validation built-in
- Rich domain behavior through properties

##### Entity Pattern
Objects with identity representing core business concepts that change over time.

**Purpose**: Model domain objects that have identity independent of their attributes
**Implementation**: Dataclasses with identity-based equality and hash methods
**Benefits**: Clear identity semantics, lifecycle management, domain behavior encapsulation

**Characteristics**:
- Identity-based equality and hashing
- Can change attributes while maintaining identity
- Domain behavior methods
- Business rule validation

##### Pure Function Pattern
Stateless functions that perform domain calculations without side effects.

**Purpose**: Provide reusable domain logic without coupling to business process state
**Implementation**: Functions that take domain objects as input and return domain objects
**Benefits**: Testability, reusability, functional composition, no side effects

##### Configuration Object Pattern
Type-safe configuration objects that capture domain intentions and validate business constraints.

**Purpose**: Ensure valid service configuration with domain-appropriate validation
**Implementation**: Frozen dataclasses with domain-specific validation logic
**Benefits**: Type safety, domain validation, configuration immutability, clear contracts

#### Composition Patterns

##### Composition Root Pattern
Central location for service instantiation, configuration, and dependency wiring.

**Purpose**: Manage service creation and configuration in a single, controlled location
**Implementation**: Main application entry point handles service composition
**Benefits**: Centralized configuration, clear dependencies, testable composition

##### Dependency Injection Pattern
Services receive dependencies through constructor parameters rather than creating them internally.

**Purpose**: Enable flexible service composition and testability
**Implementation**: Constructor parameters for service dependencies and configuration
**Benefits**: Testability with mock dependencies, flexible composition, clear contracts

##### Factory Method Pattern
Services create complex internal objects through factory methods rather than constructor logic.

**Purpose**: Encapsulate complex object creation while maintaining clean constructor interfaces
**Implementation**: Private methods that create internal processors, strategies, or utilities
**Benefits**: Clean constructors, encapsulated complexity, consistent object creation

#### Integration Patterns

##### Adapter Pattern
Interface layers adapt between external frameworks and internal domain concepts.

**Purpose**: Isolate framework-specific code from domain logic
**Implementation**: Interface-specific adapters that translate between frameworks and domain
**Benefits**: Framework isolation, domain protection, interface flexibility

##### Strategy Pattern (Configuration-Based)
Behavior variations implemented through constructor parameters and conditional logic.

**Purpose**: Enable runtime behavior customization without complex inheritance hierarchies
**Implementation**: Constructor parameters that influence internal processing logic
**Benefits**: Runtime flexibility, simple implementation, clear behavior contracts

**Note**: jBOM uses parameter-based strategies rather than strategy object injection, keeping implementation simple while maintaining flexibility.

##### Observer Pattern (Event-Based)
Domain services communicate state changes through well-defined domain events.

**Purpose**: Enable loose coupling between services while maintaining domain integrity
**Implementation**: Domain events that carry business-relevant information
**Benefits**: Loose coupling, domain event history, extensible workflows

#### Testing Patterns

##### Isolated Unit Testing Pattern
Domain services tested with domain objects and mock dependencies.

**Purpose**: Validate business logic in isolation from infrastructure concerns
**Implementation**: Unit tests that create domain objects and test service methods
**Benefits**: Fast execution, clear failure indication, business logic focus

##### Integration Testing Pattern
Application layer tested with real domain services and mock infrastructure.

**Purpose**: Validate service orchestration and workflow logic
**Implementation**: Integration tests that use real services with controlled inputs
**Benefits**: Workflow validation, service collaboration testing, realistic scenarios

##### Contract Testing Pattern
Services tested against well-defined input/output contracts.

**Purpose**: Ensure service contracts remain stable across implementation changes
**Implementation**: Tests that validate service behavior against documented contracts
**Benefits**: Contract stability, implementation flexibility, clear service boundaries

#### Extension Patterns

##### Plugin Interface Pattern
Well-defined extension points for adding new capabilities without modifying existing code.

**Purpose**: Enable system extension while maintaining architectural integrity
**Implementation**: Abstract interfaces with clear contracts for extension implementations
**Benefits**: Extensibility, stability, architectural consistency

##### Configuration Extension Pattern
New behavior added through configuration objects rather than code modification.

**Purpose**: Add capabilities through configuration rather than code changes
**Implementation**: Configuration objects that enable new processing options
**Benefits**: Runtime flexibility, backward compatibility, minimal code impact

#### Naming Convention

Established in issues #224 and #237; documented in `src/WARP.md`.

**Rule**: Names reflect the *promise* (what is produced/delivered), not the mechanism.

| Principle | Correct | Avoid |
|---|---|---|
| Class names | `BOMWorkflow`, `GerberExporter` | `BOMOrchestrationService`, `GerberService` |
| `Service` suffix | Omit when module path provides context | `jbom.application.BOMWorkflowService` |
| `Orchestration` in names | Never — describes *how*, not *what* | `BOMOrchestrationRequest` |
| Public workflow method | `.run(request)` | `.orchestrate(request)`, `.execute(request)` |
| Private helpers | `_list_fields`, `_generate` | `_orchestrate_field_listing`, `_do_generation` |
| Module file names | `bom_workflow.py`, `pos_workflow.py` | `bom_orchestration.py`, `pos_orchestration.py` |

#### Diagnostic Collection Pattern
Established in ADR 0006 (issue #226).

Services **always collect and return all diagnostics** in the result contract (`tuple[str, ...]`).
Adapters decide what to display and when.

**Rule**: No service module may read `os.environ` to gate diagnostic generation.
`os.environ.get("JBOM_QUIET")` and equivalents are adapter concerns only.

**Rule**: Request dataclasses must not carry a `quiet` field. Suppression of output
is a presentation decision belonging to the adapter, not the service.

**CLI adapter pattern**:
```
result = SomeWorkflow().run(request)
for diag in result.diagnostics:
    if args.verbose or is_warning_or_error(diag):
        print(diag, file=sys.stderr)
```

**Plugin adapter pattern**: Store `result.diagnostics` and surface via a "details" panel
or popup — the full set is always available regardless of verbose state.

**Future enhancement**: Replace `tuple[str, ...]` with `tuple[Diagnostic, ...]` where
`Diagnostic(severity: Literal["info", "warning", "error"], message: str)` enables
adapter-side filtering without parsing message text.

#### Friend Serializer Pattern
Established in ADR 0006 (issue #226).

When a workflow (e.g., `FabricationWorkflow`) needs to write BOM or POS artifacts to disk,
it must not call CLI adapter code to do so. Instead, it uses a *friend serializer*:
a service-layer module that accepts the data structure produced by the workflow service
and writes it to the requested path.

```
BOMWorkflow.run()   → BOMResult (data structure, no file I/O)
BOMWriter.write(result, output_path)   → writes jbom.csv
```

This keeps workflows as pure orchestrators and serialization as a separately testable concern.
CLI adapters continue to call `_output_bom` / `_output_pos` for console and stdout rendering;
those remain adapter concerns. File-writing for the `fab` workflow uses the friend serializer.

These design patterns provide the foundation for consistent, maintainable, and extensible software architecture throughout the jBOM system.

### Layer responsibilities

This document defines the clear responsibilities, constraints, and interaction patterns for each layer in jBOM's domain-centric architecture.

#### Layer Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Interface Layer                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  CLI Commands   │  │  GUI Components │  │ KiCad Plugins│ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                   Application Layer                         │
│          (Contract-Oriented Orchestration Services)         │
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

#### Domain Model Layer

##### Purpose
Provides shared domain concepts, value objects, and pure functions used across all bounded contexts.

##### Responsibilities
- **Domain Entities**: Core business objects with identity (Component, InventoryItem, BoardModel)
- **Value Objects**: Immutable domain concepts without identity (BOMEntry, PlacementData)
- **Configuration Objects**: Type-safe service configuration with domain validation
- **Pure Functions**: Stateless domain calculations and transformations
- **Domain Constants**: Business rules, categorization mappings, validation constraints
- **File Format Utilities**: Bridge between external file formats and domain objects

##### Characteristics
- **Stateless**: No business process state, only data and pure functions
- **Immutable**: Prefer frozen dataclasses for value objects
- **Domain-Focused**: Electronics terminology and business rule encoding
- **Cross-Cutting**: Concepts used by multiple bounded contexts

##### Constraints
- **No Dependencies**: Only standard library and typing imports
- **Pure Functions**: No side effects or external system interactions
- **Domain Language**: Consistent electronics domain terminology
- **Validation**: Business rules encoded in object validation methods

#### Domain Services Layer

##### Purpose
Encapsulates core business operations and domain expertise as stateful, configurable objects.

##### Responsibilities
- **Business Logic**: Pure domain operations without infrastructure concerns
- **Domain Rules**: Implementation of complex business rules and domain knowledge
- **Service Composition**: Using other domain services for specialized operations
- **Configuration Management**: Constructor-based behavior customization
- **Domain Workflows**: Complete business operations within bounded contexts

##### Characteristics
- **Stateful Objects**: Constructor-configured behavior and operational state
- **Single Responsibility**: Each service handles one bounded domain context
- **Constructor Configuration**: Behavior established through parameters and options
- **Business Purity**: No CLI, file I/O, or infrastructure dependencies

##### Constraints
- **Domain Dependencies Only**: Can import domain models and other domain services
- **No Application Layer**: Cannot import from CLI, application layer, or interface frameworks
- **No Side Effects**: No print statements, file operations, or external API calls
- **Interface Agnostic**: Must work identically across different calling interfaces

##### Service Categories

###### Data Extraction Services
- **Purpose**: Extract domain objects from external file formats
- **Examples**: `SchematicReader`, `PCBReader`, `InventoryReader`
- **Pattern**: File path input → Domain objects output

###### Processing Services
- **Purpose**: Transform domain objects through business operations
- **Examples**: `BOMGenerator`, `POSGenerator`, `InventoryMatcher`
- **Pattern**: Domain objects input → Processed domain objects output

###### Analysis Services
- **Purpose**: Analyze domain objects and provide business insights
- **Examples**: Component analysis, placement validation, procurement calculation
- **Pattern**: Domain objects input → Analysis results output

#### Application Layer

##### Purpose
Orchestrates domain services and manages interface workflows without containing business logic.

##### Responsibilities
- **Input Translation**: Convert interface arguments to domain configuration objects
- **Service Orchestration**: Coordinate multiple domain services for complex workflows
- **Output Formatting**: Adapt domain results for interface-specific presentation
- **Error Translation**: Convert domain exceptions to user-appropriate messages
- **Workflow Management**: Handle multi-service operations and business processes

##### Characteristics
- **Stateless Orchestration**: No business state, only workflow coordination
- **Interface Adaptation**: Bridge between interface concerns and domain operations
- **Service Composition**: Coordinate domain services without implementing business logic
- **Error Handling**: Translate domain exceptions to user-friendly messages

##### Constraints
- **No Business Logic**: Cannot contain domain rules or business calculations
- **Stateless Operations**: No instance variables or persistent state
- **Domain Service Orchestration**: Use domain services, don't reimplement their logic
- **Interface Translation**: Handle conversion between interface and domain concerns

##### Application Layer Patterns

###### Command Handler Pattern
```
1. Parse interface arguments
2. Translate to domain configuration objects
3. Instantiate and configure domain services
4. Execute service operations in logical sequence
5. Format results for interface presentation
6. Handle errors with appropriate user feedback
```

###### Adapter-Thin CLI Contract Pattern
```
Application module: src/jbom/application/<command>_workflow.py
Workflow class:    <Command>Workflow          (e.g. BOMWorkflow, POSWorkflow, FabricationWorkflow)
Request:           <Command>Request           (e.g. BOMRequest, POSRequest)
Result:            <Command>Result            (e.g. BOMResult, POSResult)
Mode enum:         <Command>Mode              (e.g. BOMMode — for multi-mode workflows)
Public method:     .run(request) -> result
Diagnostics:       immutable tuple on result contract (not callback side effects)
```

CLI adapter responsibilities are intentionally narrow:
1. Parse CLI flags/arguments.
2. Build request contract and call `.run()` on the workflow.
3. Render diagnostics and output payloads.
4. Map exceptions/outcomes to process exit semantics.

See also: **Naming Convention** in `design-patterns.md` and `src/WARP.md`.

###### Service Composition Pattern
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

#### Interface Layer

##### Purpose
Provides user and system interfaces built on the application layer foundation.

##### Responsibilities
- **User Interface**: CLI commands, GUI components, web interfaces
- **Framework Integration**: Interface-specific framework implementations
- **Presentation Logic**: Display formatting, user interaction handling
- **Interface Protocols**: API endpoints, plugin interfaces, configuration management

##### Characteristics
- **Framework-Specific**: Uses interface frameworks (argparse, GUI toolkits, web frameworks)
- **Presentation Focus**: Handles user interface and display concerns
- **Application Layer Dependent**: Builds on application layer services
- **Multiple Implementations**: Same functionality across different interface types

##### Constraints
- **No Business Logic**: All domain operations handled by lower layers
- **Framework Isolation**: Interface framework dependencies isolated to this layer
- **Application Layer Use**: Must use application layer, not domain services directly
- **Interface-Specific**: Implementation details specific to interface type

#### Dependency Management

##### Dependency Rules
1. **Inward Flow**: Dependencies flow toward domain core
2. **Layer Isolation**: No dependencies on higher layers
3. **Clear Boundaries**: Each layer has well-defined import constraints
4. **Shared Concepts**: Domain model layer accessible to all other layers

##### Allowed Dependencies
```
Interface Layer      → Application Layer, Domain Model Layer
Application Layer    → Domain Services Layer, Domain Model Layer
Domain Services Layer → Domain Model Layer, Other Domain Services
Domain Model Layer   → Standard Library Only
```

##### Forbidden Dependencies
- Domain Services → Application Layer or Interface Layer
- Domain Model → Any application-specific concerns
- Cross-layer circular dependencies
- Infrastructure concerns in domain layers

##### Boundary Enforcement
Currently enforced through:
- **Code Review**: Architectural discipline during development
- **Layer Structure**: Clear filesystem organization by layer
- **Import Conventions**: Established patterns for cross-layer communication

Future enforcement mechanisms:
- **Static Analysis**: Automated dependency checking
- **Architecture Tests**: Unit tests validating dependency constraints
- **CI/CD Integration**: Automated boundary validation in build pipeline

#### Benefits

##### Clear Separation of Concerns
- Each layer has distinct, well-defined responsibilities
- Business logic isolated from interface and infrastructure concerns
- Clear boundaries prevent coupling violations

##### Interface Flexibility
- Multiple interface types supported without domain changes
- Application layer provides consistent orchestration across interfaces
- Domain services reusable across different interface implementations

##### Evolutionary Design
- New capabilities added without modifying existing layers
- Layer boundaries support incremental enhancement
- Clear extension points through established patterns

##### Testing Strategy
- **Domain Services**: Unit tests with domain objects
- **Application Layer**: Integration tests with mocked domain services
- **Interface Layer**: End-to-end tests with real workflows
- **Cross-Layer**: Validation of architectural constraints

This layered architecture provides the foundation for maintainable, extensible software that clearly separates domain expertise from interface and infrastructure concerns.

### Integration patterns

This document defines how services compose and layers interact within jBOM's domain-centric architecture.

#### Service Composition Patterns

##### Linear Composition
Sequential service operations where output of one service becomes input to the next.

**Use Case**: Standard processing pipelines with clear data flow
**Pattern**: Service A → Data → Service B → Data → Service C
**Benefits**: Simple reasoning, clear data flow, easy testing

```
Schematic Processing Pipeline:
File Path → SchematicReader → Components → BOMGenerator → BOMData
```

##### Parallel Composition
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

##### Enhancement Composition
Services that augment existing data with additional information.

**Use Case**: Adding inventory data, procurement information, or analysis results
**Pattern**: Base Data + Enhancement Service → Enhanced Data
**Benefits**: Incremental enhancement, optional processing, modular capabilities

```
BOM Enhancement:
BOMData + InventoryMatcher → EnhancedBOMData (with availability info)
```

##### Conditional Composition
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

#### Layer Interaction Patterns

##### Interface → Application → Domain
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

##### Domain → Domain
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

##### Configuration → Behavior
Configuration objects driving service behavior variations.

**Flow**: Configuration Object → Service Constructor → Behavior Modification
**Characteristics**: Type-safe configuration, domain validation, immutable behavior contracts

```
Configuration-Driven Behavior:
options = PlacementOptions(smd_only=True, units="mm", layer_filter="TOP")
generator = POSGenerator(options)
# Generator behavior now configured for SMD-only, metric, top-layer processing
```

#### Error Flow Patterns

##### Domain Exception → Interface Error
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

##### Validation Error Cascade
Configuration validation errors preventing invalid service instantiation.

**Flow**: Invalid Configuration → Validation Error → Early Failure → User Feedback
**Characteristics**: Fail-fast behavior, clear validation messages, prevented invalid operations

```
Configuration Validation:
PlacementOptions(units="invalid") → ValidationError → User sees clear error message
```

#### Data Flow Patterns

##### Domain Object Passing
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

##### Immutable Data Transformation
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

##### Configuration Inheritance
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

#### Composition Coordination Patterns

##### Application Layer Orchestration
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

##### Service Factory Pattern
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

##### Event-Driven Integration
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

#### Testing Integration Patterns

##### Service Isolation Testing
Test services independently with mock dependencies and domain objects.

**Purpose**: Validate business logic without external dependencies
**Implementation**: Unit tests with domain object inputs and mock service dependencies
**Benefits**: Fast tests, clear failure isolation, business logic focus

##### Workflow Integration Testing
Test service composition with real services and controlled data.

**Purpose**: Validate service orchestration and data flow
**Implementation**: Integration tests that exercise complete workflows
**Benefits**: Workflow validation, real service interaction, end-to-end confidence

##### Contract Testing
Validate service interfaces remain stable across implementations.

**Purpose**: Ensure service contracts don't break during implementation changes
**Implementation**: Tests that validate service input/output contracts
**Benefits**: Interface stability, implementation flexibility, evolutionary design

These integration patterns ensure that jBOM's services compose cleanly while maintaining architectural boundaries and enabling flexible, maintainable workflows.

## Consequences

*From `domain-centric-design.md`:*
This domain-centric approach ensures that jBOM's architecture remains aligned with business understanding while supporting technical flexibility and evolutionary design.

*From `layer-responsibilities.md` — Benefits section:*

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

*Note: `design-patterns.md` and `integration-patterns.md` did not contain explicit Consequences sections; their closing summary paragraphs appear at the end of their respective Decision subsections above.*

## Provenance

Normalized into formal ADR format on 2026-05-25 under issue #300.
Source file(s):

- `docs/dev/architecture/domain-centric-design.md` — Context section (introduction paragraph) and Decision section (Domain-Driven Design Principles, Domain Model Design, Domain Evolution subsections; content preserved verbatim)
- `docs/dev/architecture/design-patterns.md` — Decision section (§ Design patterns subsection, content preserved verbatim); closing summary paragraph also appears in Consequences
- `docs/dev/architecture/layer-responsibilities.md` — Decision section (§ Layer responsibilities subsection, content preserved verbatim); Benefits section additionally reproduced in Consequences
- `docs/dev/architecture/integration-patterns.md` — Decision section (§ Integration patterns subsection, content preserved verbatim); closing summary paragraph also appears in Consequences
