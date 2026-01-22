# jBOM Developer Guide

A comprehensive guide to jBOM's architecture, design patterns, and implementation details for contributors and maintainers.

## Architecture Overview

jBOM implements a **Service-Command Architecture** with clear layer separation:

```
src/jbom/
├── services/     # Domain services - business logic with state
├── cli/          # Application layer - interface adapters
├── common/       # Domain models - shared concepts and utilities
└── config/       # Configuration objects
```

## Core Design Principles

### Service vs Common Axiom

**The differentiator is the `__init__` method**:

- **Services** (`src/services/`): Have state and behavior
  - Contains `__init__` method with instance variables
  - Encapsulate business processes and domain logic
  - Examples: `ComponentInventoryMatcher`, `BOMGenerator`

- **Common** (`src/common/`): Stateless utilities and data structures
  - Pure functions, data classes, constants
  - No `__init__` methods (except for data classes)
  - Examples: `ComponentData`, file utilities, formatters

### Dependency Direction

Application Layer → Services Layer → Domain Model Layer (never outward)

```python
# CLI imports services
from jbom.services.bom_generator import BOMGenerator

# Services import common models
from jbom.common.component_data import ComponentData

# Services NEVER import CLI modules
```

## Inventory System Architecture

### Component Matching Service

The `ComponentInventoryMatcher` service provides sophisticated component identification:

#### Matching Algorithm
```python
class ComponentInventoryMatcher:
    def __init__(self, inventory_file: Optional[Path] = None):
        """Initialize matcher, optionally loading from single file."""

    def set_inventory(self, inventory_items: List[InventoryItem]) -> None:
        """Set pre-aggregated inventory items (for multi-source scenarios)."""

    def find_matches(self, component_data: Dict) -> List[ComponentMatch]:
        """Find inventory matches with scoring."""
```

**Scoring System**:
1. **Exact IPN Match** (100 points) - Internal Part Numbers match exactly
2. **Type+Value+Package Match** (85 points) - All three core attributes match
3. **Type+Value Match** (60 points) - Component type and value match
4. **Property-Based Match** (varies) - Custom property matching with configurable weights

#### Multi-Source Inventory Architecture

Multi-source inventory aggregation with proper deduplication validation:

```python
# CLI layer aggregates inventories with validation
merged_inventory, warnings = aggregate_with_deduplication_validation([
    primary_inventory,    # Items tagged with source="primary"
    backup_inventory,     # Items tagged with source="backup"
    supplier_catalog      # Items tagged with source="catalog"
])

# Emit warnings for problematic duplicates
for warning in warnings:
    print(f"Warning: IPN {warning.ipn} has conflicting data: {warning.conflicts}")

# Matcher works with clean, deduplicated inventory
matcher = ComponentInventoryMatcher()
matcher.set_inventory(merged_inventory)
```

**Pragmatic Data Model** (spreadsheet-compatible with normalized intent):
```csv
IPN,Type,Value,Package,Manufacturer,MPN,Priority
IPN-10k-E17-0603-Resistor,resistor,10k,0603,Yageo,RC0603FR-0710KL,1
IPN-10k-E17-0603-Resistor,resistor,10k,0603,Vishay,CRCW060310K0FKEA,2
```

**Conceptual Mapping to Normalized Design**:
- **Repeated IPN rows** = supplier alternatives for same component
- **Component fields** (Type, Value, Package) = canonical specification
- **Supplier fields** (Manufacturer, MPN) = sourcing options
- **Priority field** = ranking within IPN group

**Validation Requirements**:
1. **Consistent component specs** - same IPN must have identical Type/Value/Package
2. **Priority ranking** - different priorities indicate legitimate alternatives
3. **Conflict detection** - warn when component specs differ for same IPN
4. **Future extensibility** - design allows migration to fully normalized tables

**Current Implementation vs. Intent**:
1. **Missing Validation**: No checks for consistent component specs across same-IPN rows
2. **Naive Deduplication**: "First wins" instead of priority-based supplier ranking
3. **Unused Priority Field**: Priority exists but not used for supplier selection

**Alignment with Pragmatic Model**:
- **Accept repeated IPNs** as supplier alternatives (not duplicates to eliminate)
- **Validate component specs** are consistent within IPN groups
- **Use Priority field** for supplier ranking instead of file order
- **Preserve spreadsheet usability** while maintaining normalized intent

**Future Integration Readiness**:
This pragmatic approach provides a compatible foundation for future integrations with KiCad database systems and enterprise ERP/PLM solutions while maintaining CSV simplicity for current users.

**Architecture Benefits**:
- Simple data flow: aggregate → match → filter
- Service remains stateless for matching logic
- Precedence handled at data layer, not matching logic
- Extensible for different ranking/optimization policies

### Data Integrity Validation

Multi-source inventory requires validation to prevent indeterminate behavior:

#### Duplicate IPN Detection
```python
class InventoryValidator:
    def validate_merged_inventory(self, items: List[InventoryItem]) -> List[ValidationWarning]:
        """Detect duplicate IPNs with conflicting data."""
        warnings = []
        ipn_groups = group_by_ipn(items)

        for ipn, group in ipn_groups.items():
            if len(group) > 1:
                conflicts = self._find_field_conflicts(group)
                if conflicts:
                    warnings.append(DuplicateIPNWarning(
                        ipn=ipn,
                        sources=[item.source_file for item in group],
                        conflicts=conflicts
                    ))
        return warnings
```

#### Validation Rules
- **Priority field differences**: Expected and allowed for ranking
- **Source metadata differences**: Expected (source, source_file)
- **Core field differences**: Warning required (manufacturer, value, package, etc.)
- **UUID differences**: Warning (could indicate different physical components)

### File Safety Architecture

Production-ready file handling with safety features:

#### Backup System
```python
class FileBackupService:
    def create_backup(self, filepath: Path) -> Path:
        """Create timestamped backup: filename.backup.YYYYMMDD_HHMMSS.ext"""
```

#### Overwrite Protection
- Files are never overwritten without explicit `--force` flag
- Clear error messages guide users through safety options
- Automatic backups when overwriting with `--force`

## Service Implementation Patterns

### Strategy Pattern for Configurable Behavior

Services use constructor injection for behavior configuration:

```python
class BOMGenerator:
    def __init__(self, aggregation_strategy: str = "value_footprint"):
        self.strategy = aggregation_strategy

class ComponentInventoryMatcher:
    def __init__(self, inventory_file: Optional[Path] = None):
        self.inventory = []
        if inventory_file:
            self._load_inventory(inventory_file)
```

### Factory Pattern for Complex Object Creation

Services create domain objects through internal factories:

```python
class InventoryGenerator:
    def _build_inventory_item(self, component: ComponentData) -> InventoryData:
        """Factory method for inventory item creation."""
        return InventoryData(
            ipn=self._generate_ipn(component),
            component_type=component.component_type,
            # ... other fields
        )
```

### Command/Query Separation

Clear distinction between operations and data retrieval:

```python
# Commands (modify state/produce output)
def generate_inventory_data(self, components: List[ComponentData]) -> List[InventoryData]
def create_enhanced_bom(self, components: List[ComponentData]) -> BOMData

# Queries (read-only operations)
def validate_inventory_format(self, filepath: Path) -> ValidationResult
def count_matched_components(self, components: List[ComponentData]) -> int
```

## CLI Integration Patterns

### Application Layer as Orchestrators

CLI commands coordinate services without containing business logic:

```python
def handle_inventory_command(args):
    # 1. Translate CLI args to domain configuration
    options = InventoryOptions.from_args(args)

    # 2. Create and configure services
    reader = SchematicReader(options.reader_config)
    generator = InventoryGenerator(options.generation_config)

    # 3. Orchestrate workflow
    components = reader.load_components(args.schematic_path)
    inventory_data = generator.generate_inventory_data(components)

    # 4. Handle output presentation
    if args.output_file:
        save_inventory_csv(inventory_data, args.output_file)
    else:
        display_inventory_table(inventory_data)
```

### Input Translation Pattern

CLI arguments are translated to domain configuration objects:

```python
class InventoryOptions:
    @classmethod
    def from_args(cls, args) -> 'InventoryOptions':
        """Translate CLI args to domain configuration."""
        return cls(
            filter_matches=args.filter_matches,
            inventory_sources=[Path(inv) for inv in args.inventory],
            force_overwrite=args.force,
            verbose=args.verbose
        )
```

### Error Translation Pattern

Domain exceptions are caught and translated to user-friendly messages:

```python
try:
    inventory_data = generator.generate_inventory_data(components)
except InventoryGenerationError as e:
    sys.exit(f"Inventory generation failed: {e.user_message}")
except FileNotFoundError as e:
    sys.exit(f"File not found: {e.filename}")
```

## Testing Architecture

### Layered Testing Strategy

1. **Gherkin Features** - User behavior and workflow validation
2. **Unit Tests** - Service logic and domain model validation
3. **Integration Tests** - Service collaboration validation

### Gherkin Test Organization

```
features/
├── inventory/           # Inventory-specific workflows
│   ├── core.feature    # Basic inventory generation
│   ├── matching.feature # Component matching scenarios
│   ├── multi_source.feature # Multi-inventory workflows
│   └── file_safety.feature  # File handling edge cases
├── bom/                # BOM-specific workflows
│   └── inventory_enhancement.feature # BOM+inventory integration
└── shared/             # Cross-command scenarios
    └── ux_consistency.feature # Consistent behavior patterns
```

### DRY Background Pattern

Use comprehensive Background setups for scenarios sharing test data:

```gherkin
Feature: Inventory Management
  Background:
    Given I have a test schematic "complex_board.kicad_sch" with components:
      | Reference | Value | Footprint | Type |
      | R1        | 10k   | 0603      | resistor |
      | C1        | 100nF | 0603      | capacitor |
    And I have inventory file "existing.csv" with:
      | IPN | Type | Value | Package |
      | R-10K-0603 | resistor | 10k | 0603 |

  Scenario: Generate inventory for unmatched components
    When I run "jbom inventory complex_board.kicad_sch --inventory existing.csv --filter-matches"
    Then the output should contain only capacitor C1
```

### Unit Test Patterns

Test services in isolation using domain objects:

```python
class TestComponentInventoryMatcher(unittest.TestCase):
    def setUp(self):
        self.inventory = [
            InventoryItem(ipn="R-10K-0603", category="RESISTOR",
                         value="10k", package="0603"),
        ]
        self.matcher = ComponentInventoryMatcher()
        self.matcher.set_inventory(self.inventory)

    def test_exact_ipn_match_returns_perfect_score(self):
        component_data = {
            "reference": "R1",
            "value": "10k",
            "footprint": "R_0603_1608Metric",
            "lib_id": "Device:R",
            "properties": {}
        }

        matches = self.matcher.find_matches(component_data)

        self.assertEqual(len(matches), 1)
        self.assertTrue(matches[0].score >= 50)  # Should match well
```

## Configuration Management

### Domain Configuration Objects

Type-safe configuration with validation:

```python
@dataclass
class MatchingConfig:
    """Configuration for component matching behavior."""
    exact_ipn_weight: int = 100
    type_value_package_weight: int = 85
    type_value_weight: int = 60
    min_score_threshold: int = 50

    def __post_init__(self):
        if self.min_score_threshold < 0:
            raise ValueError("Score threshold must be non-negative")
```

### Application Configuration

CLI-specific configuration separate from domain logic:

```python
@dataclass
class OutputOptions:
    """CLI output formatting configuration."""
    format: str = "console"  # "console" | "csv"
    verbose: bool = False
    force_overwrite: bool = False
```

## Extension Patterns

### Adding New Services

1. **Create service class** with `__init__` method (has state/behavior)
2. **Follow pure business logic** - no CLI dependencies
3. **Add comprehensive unit tests** in `tests/services/`
4. **Document in service README**

Example service skeleton:
```python
class NewDomainService:
    def __init__(self, configuration: NewServiceConfig):
        """Configure service behavior."""
        self.config = configuration
        self._state = self._initialize_state()

    def process_domain_operation(self, input_data: DomainModel) -> DomainModel:
        """Core business operation."""
        # Domain logic here
        pass

    def _initialize_state(self) -> Any:
        """Internal factory method."""
        pass
```

### Adding CLI Commands

1. **Create command handler** in `src/jbom/cli/`
2. **Register in main.py**
3. **Add Gherkin tests** in `features/<command>/`
4. **Update user documentation**

### Multi-Interface Support

Services are interface-agnostic and can support:

- **CLI** (current implementation)
- **GUI applications** (future)
- **Web APIs** (future)
- **KiCad plugins** (future)

The service layer remains unchanged; only adapter layers need implementation.

## Performance Considerations

### Inventory Matching Optimization

- **Early exit** on exact IPN matches (score = 100)
- **Lazy evaluation** of expensive matching criteria
- **Caching** of parsed inventory data across multiple operations

### Memory Management

- **Streaming CSV processing** for large inventory files
- **Generator patterns** for component processing pipelines
- **Lazy loading** of schematic/PCB data

## Error Handling Patterns

### Domain-Level Exceptions

Create specific exceptions for domain errors:

```python
class ComponentMatchingError(Exception):
    """Raised when component matching fails."""
    def __init__(self, component_ref: str, reason: str):
        self.component_ref = component_ref
        self.user_message = f"Failed to match {component_ref}: {reason}"
        super().__init__(self.user_message)
```

### Graceful Degradation

Services should provide meaningful partial results when possible:

```python
def generate_enhanced_bom(self, components: List[ComponentData]) -> BOMData:
    """Generate BOM with best-effort inventory enhancement."""
    results = []
    for component in components:
        try:
            enhanced = self._enhance_component(component)
            results.append(enhanced)
        except ComponentEnhancementError:
            # Include component without enhancement
            results.append(component)
    return BOMData(results)
```

This architecture enables maintainable, testable, and extensible inventory management capabilities while preserving jBOM's architectural principles.
