# Domain-Centric Design

jBOM's architecture prioritizes domain logic clarity through Domain-Driven Design principles, establishing clear bounded contexts and ubiquitous language throughout the electronics design domain.

## Domain-Driven Design Principles

### Ubiquitous Language
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

### Bounded Contexts

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

#### Schematic Domain
**Core Concepts**: Component extraction, hierarchy resolution, design rule application
**Business Rules**:
- DNP (Do Not Populate) components excluded by default
- Multi-unit components consolidated by reference designator
- Hierarchical designs flattened with proper reference prefixing
- Component properties merged from schematic and library sources

**Domain Service**: `SchematicReader`

#### PCB Domain
**Core Concepts**: Physical component placement, coordinate systems, manufacturing layers
**Business Rules**:
- Component placement coordinates in millimeters
- Layer designation (TOP/BOTTOM) determines assembly sequence
- Rotation angles normalized to manufacturing standards (0-360°)
- SMD components identified by footprint characteristics

**Domain Service**: `PCBReader`

#### Manufacturing Domain
**Core Concepts**: BOM aggregation, component procurement, placement file generation
**Business Rules**:
- Components aggregated by value/footprint combinations
- Quantity calculations include all instances of aggregated components
- Inventory matching enhances components with procurement data
- Manufacturing files formatted for pick-and-place equipment

**Domain Services**: `BOMGenerator`, `POSGenerator`, `InventoryMatcher`

### Service Boundaries

Domain services maintain clear boundaries to prevent coupling and ensure single responsibility:

#### Boundary Enforcement
1. **Domain Isolation**: Services only import from domain model layer and other domain services
2. **Business Logic Purity**: No infrastructure concerns (CLI, file I/O, external APIs)
3. **Interface Agnostic**: Services work identically regardless of calling interface
4. **Configuration Independence**: Service behavior established through constructor parameters

#### Cross-Boundary Communication
Services communicate through well-defined domain objects:

```
SchematicReader → Component[] → BOMGenerator → BOMData
                                     ↓
PCBReader → BoardModel → POSGenerator → PlacementData[]
                              ↓
InventoryMatcher → EnhancedBOMData
```

## Domain Model Design

### Entity vs Value Object Distinction

**Domain Entities**: Objects with identity representing core business concepts
- `Component`: Electronic component with reference designator identity
- `InventoryItem`: Inventory record with internal part number identity
- `BoardModel`: PCB design with file path identity

**Value Objects**: Immutable objects representing domain concepts through attributes
- `BOMEntry`: Aggregated component information without individual identity
- `PlacementData`: Component placement coordinates and orientation
- `ComponentValue`: Parsed electrical specification (numeric value + unit)

### Domain Rules Encoding

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

### Configuration Objects

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

## Domain Evolution

### Adding New Bounded Contexts
1. **Domain Analysis**: Identify coherent business functionality requiring separate service
2. **Boundary Definition**: Establish clear input/output contracts with existing contexts
3. **Service Creation**: Implement domain service following established patterns
4. **Integration Testing**: Validate service composition with existing workflows

### Extending Existing Contexts
1. **Backward Compatibility**: Maintain existing service contracts during enhancement
2. **Domain Integrity**: Ensure new functionality aligns with established domain language
3. **Boundary Respect**: Avoid feature creep that violates single responsibility
4. **Configuration Extension**: Add new behavior through constructor parameters

### Cross-Cutting Concerns
Handle concerns that span multiple bounded contexts:

- **Configuration Management**: Shared options objects in domain model layer
- **File Format Parsing**: Utility functions bridging file formats to domain objects
- **Error Handling**: Domain-specific exceptions with business context
- **Validation**: Business rule validation in domain objects and configuration

This domain-centric approach ensures that jBOM's architecture remains aligned with business understanding while supporting technical flexibility and evolutionary design.
