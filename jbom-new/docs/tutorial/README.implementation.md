# Implementation Tutorial: Building a POS Service

This tutorial demonstrates jBOM's development approach by implementing a Position (POS) service from scratch, following TDD principles and architectural patterns.

## Development Process Overview

jBOM development follows this sequence:
1. **Gherkin Features** - Define user behavior
2. **Domain Models** - Add shared concepts
3. **Service Implementation** - Build business logic
4. **CLI Integration** - Create user interface
5. **Testing & Validation** - Ensure robustness

## Step 1: Define Gherkin Features

Start with user behavior specification in `features/pos/pos_generation.feature`:

```gherkin
Feature: Generate Position Files
  As a PCB designer
  I want to generate component placement files from KiCad PCB data
  So that I can provide pick-and-place data to manufacturers

  Scenario: Generate POS file with default settings
    Given I have a KiCad PCB file "example.kicad_pcb"
    When I run jbom pos "example.kicad_pcb"
    Then the position data should include all components
    And each component should have placement coordinates
    And the output should be in CSV format

  Scenario: Filter to SMD components only
    Given I have a KiCad PCB file with SMD and through-hole components
    When I run jbom pos "mixed.kicad_pcb" --smd-only
    Then only SMD components should be included
    And through-hole components should be excluded
```

**Key Insight**: Gherkin focuses on *what* the system should do, not *how* it does it. This drives domain service design.

## Step 2: Create Step Implementations

Step functions orchestrate services to fulfill Gherkin scenarios in `features/steps/pos_steps.py`:

```python
@when('I run jbom pos "{pcb_file}"')
def step_run_pos_command(context, pcb_file):
    """Orchestrate POS generation workflow."""
    pcb_path = context.test_data_dir / pcb_file

    # Service composition - each with single responsibility
    reader = DefaultKiCadReaderService()
    generator = POSGenerator(PlacementOptions())

    # Domain workflow
    board = reader.read_pcb_file(pcb_path)
    pos_data = generator.generate_pos_data(board)

    context.pos_data = pos_data

@then('the position data should include all components')
def step_verify_all_components(context):
    """Verify business rule: all placed components included."""
    assert len(context.pos_data) > 0
    # Domain validation logic here
```

**Key Insight**: Steps orchestrate services but don't implement business logic. Domain rules are validated, not implemented.

## Step 3: Define Domain Models

Add domain concepts to `common/pcb_types.py`:

```python
@dataclass
class BoardModel:
    """Domain Entity: PCB board with component placement data."""
    path: Path
    title: str = ""
    kicad_version: str = ""
    footprints: List[PcbComponent] = field(default_factory=list)

@dataclass
class PcbComponent:
    """Domain Entity: Component placement information."""
    reference: str              # Component identity (R1, C5, U3)
    footprint_name: str        # KiCad PCB library footprint reference
    package_token: str         # Physical package type (0805, SOIC-8, etc.)
    center_x_mm: float         # X placement coordinate
    center_y_mm: float         # Y placement coordinate
    rotation_deg: float        # Rotation angle
    side: str                  # "TOP" or "BOTTOM"
    attributes: dict = field(default_factory=dict)

    @property
    def is_smd(self) -> bool:
        """Domain rule: Is component surface-mount?"""
        return self.attributes.get("mount_type") == "smd"
```

**Key Insight**: Domain models encode business rules and use ubiquitous language from the electronics domain.

## Step 4: Implement Configuration Objects

Create type-safe configuration in `common/options.py`:

```python
@dataclass(frozen=True)
class PlacementOptions:
    """Configuration for POS generation domain service."""
    units: str = "mm"                    # "mm" or "inch"
    origin: str = "board"               # "board" or "aux"
    smd_only: bool = False              # Filter to SMD components
    layer_filter: Optional[str] = None   # "TOP", "BOTTOM", or None

    def __post_init__(self):
        """Domain validation of configuration."""
        if self.units not in ("mm", "inch"):
            raise ValueError("Units must be 'mm' or 'inch'")
        if self.layer_filter and self.layer_filter not in ("TOP", "BOTTOM"):
            raise ValueError("Layer filter must be 'TOP' or 'BOTTOM'")
```

**Key Insight**: Configuration objects capture domain intentions and validate business constraints.

## Step 5: Build the Domain Service

Implement the core business logic in `services/pos_generator.py`:

```python
class POSGenerator:
    """Domain Service: Generate component placement data for manufacturing.

    Encapsulates POS generation business rules and coordinate transformations.
    """

    def __init__(self, options: PlacementOptions = None):
        """Configure POS generation behavior."""
        self.options = options or PlacementOptions()
        self._coordinate_transformer = self._create_transformer()

    def generate_pos_data(self, board: BoardModel) -> List[Dict[str, Any]]:
        """Core business operation: Generate placement data from board model."""
        components = self._filter_components(board.footprints)
        pos_entries = []

        for component in components:
            # Apply domain business rules
            transformed_coords = self._coordinate_transformer.transform(
                component.center_x_mm, component.center_y_mm
            )

            pos_entries.append({
                "reference": component.reference,
                "x_mm": transformed_coords.x,
                "y_mm": transformed_coords.y,
                "rotation": self._normalize_rotation(component.rotation_deg),
                "side": component.side,
                "footprint": component.footprint_name,
                "package": component.package_token
            })

        return pos_entries

    def _filter_components(self, components: List[PcbComponent]) -> List[PcbComponent]:
        """Apply filtering business rules."""
        filtered = components

        # SMD-only filter
        if self.options.smd_only:
            filtered = [c for c in filtered if c.is_smd]

        # Layer filter
        if self.options.layer_filter:
            filtered = [c for c in filtered if c.side == self.options.layer_filter]

        return filtered

    def _create_transformer(self) -> CoordinateTransformer:
        """Factory: Create coordinate transformation strategy."""
        if self.options.origin == "aux":
            return AuxOriginTransformer()
        return BoardOriginTransformer()
```

**Key Insights**:
- Service is stateful (configured via constructor)
- Encapsulates complex business operations
- Uses strategy pattern for configurable behavior
- Pure business logic with no CLI dependencies

## Step 6: Implement Supporting Services

Create the PCB reader service in `services/pcb_reader.py`:

```python
class DefaultKiCadReaderService(KiCadReaderService):
    """Domain Service: Read KiCad PCB files into domain objects."""

    def __init__(self, mode: str = "auto"):
        """Configure reading behavior."""
        self.mode = mode

    def read_pcb_file(self, pcb_path: Path) -> BoardModel:
        """Core business operation: Parse PCB file into domain model."""
        if not self.validate_pcb_file(pcb_path):
            raise KiCadParseError(f"Invalid PCB file: {pcb_path}")

        # Use infrastructure utilities to parse file format
        sexp = load_kicad_file(pcb_path)
        board = BoardModel(path=pcb_path)

        # Business logic: extract domain concepts from file data
        for footprint_node in walk_nodes(sexp, "footprint"):
            component = self._parse_footprint_node(footprint_node)
            if component:
                board.footprints.append(component)

        return board
```

**Key Insight**: Reader service focuses on business operation of extracting domain concepts from file formats.

## Step 7: Service Composition Pattern

Services can use other services but avoid deep orchestration:

```python
class EnhancedPOSGenerator(POSGenerator):
    """Domain Service: POS generation with inventory enhancement."""

    def __init__(self, options: PlacementOptions, inventory_matcher: InventoryMatcher):
        super().__init__(options)
        self.inventory_matcher = inventory_matcher  # Service composition

    def generate_enhanced_pos_data(self, board: BoardModel, inventory: List[InventoryItem]) -> List[Dict]:
        """Business operation: POS data enhanced with availability."""
        base_pos_data = super().generate_pos_data(board)

        # Use another service for specific domain operation
        availability_data = self.inventory_matcher.check_availability(
            [entry["reference"] for entry in base_pos_data],
            inventory
        )

        # Business logic to enhance POS data
        return self._merge_availability_data(base_pos_data, availability_data)
```

**Key Insight**: Services use other services for their domain expertise, but don't orchestrate full workflows.

## Step 8: Error Handling Pattern

Define domain-specific exceptions:

```python
class PCBProcessingError(Exception):
    """Base exception for PCB processing domain."""
    def __init__(self, message: str, pcb_path: Optional[Path] = None):
        self.pcb_path = pcb_path
        super().__init__(message)

class ComponentPlacementError(PCBProcessingError):
    """Raised when component placement cannot be determined."""
    def __init__(self, reference: str, reason: str, pcb_path: Optional[Path] = None):
        self.reference = reference
        self.reason = reason
        message = f"Placement error for {reference}: {reason}"
        super().__init__(message, pcb_path)
```

**Key Insight**: Domain exceptions provide context for CLI error translation while keeping business concerns separate.

## Step 9: Unit Testing Services

Test business logic in isolation:

```python
class TestPOSGenerator:
    def test_smd_filtering_business_rule(self):
        """Test domain rule: SMD-only filter includes only surface-mount components."""
        options = PlacementOptions(smd_only=True)
        generator = POSGenerator(options)

        # Domain test data
        smd_component = PcbComponent(
            reference="C1", attributes={"mount_type": "smd"},
            center_x_mm=10.0, center_y_mm=20.0
        )
        through_hole_component = PcbComponent(
            reference="R1", attributes={"mount_type": "through_hole"},
            center_x_mm=30.0, center_y_mm=40.0
        )

        board = BoardModel(footprints=[smd_component, through_hole_component])
        pos_data = generator.generate_pos_data(board)

        # Verify business rule application
        assert len(pos_data) == 1
        assert pos_data[0]["reference"] == "C1"
```

**Key Insight**: Unit tests focus on business rules and domain behavior, using domain objects as test data.

## Architecture Benefits Demonstrated

**Testability**: Services tested in isolation with pure business logic
**Flexibility**: Same services can power CLI, GUI, or API interfaces
**Maintainability**: Clear separation between business rules and interface concerns
**Extensibility**: New strategies and filters added without modifying existing code

The POS service demonstrates how jBOM's architectural patterns enable robust, maintainable domain services that can evolve independently of user interface concerns.
