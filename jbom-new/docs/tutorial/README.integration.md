# Integration Tutorial: CLI Adapters and Testing

This tutorial demonstrates how to integrate domain services with jBOM's CLI interface and testing infrastructure, following the adapter pattern and TDD workflow.

## Application Layer Integration Overview

The Application Layer acts as an **orchestrator** between interface concerns and domain services:

- **Input Translation**: Interface arguments → Domain configuration objects
- **Service Orchestration**: Coordinate multiple domain services
- **Output Presentation**: Domain results → Interface-appropriate formats
- **Error Translation**: Domain exceptions → User-friendly messages

## Step 1: Create Application Layer Command

Implement the POS command orchestrator in `cli/pos.py`:

```python
def register_command(subparsers) -> None:
    """Register pos command with argument parser."""
    parser = subparsers.add_parser(
        "pos", help="Generate component placement files from KiCad PCB"
    )

    # Domain-relevant arguments
    parser.add_argument("pcb", help="Path to .kicad_pcb file")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("--smd-only", action="store_true", help="Include only SMD components")
    parser.add_argument("--layer", choices=["TOP", "BOTTOM"], help="Layer filter")
    parser.add_argument("--units", choices=["mm", "inch"], default="mm")

    parser.set_defaults(handler=handle_pos)

def handle_pos(args: argparse.Namespace) -> int:
    """Command handler: orchestrate domain services for POS generation."""
    try:
        # 1. Input validation and translation
        pcb_file = Path(args.pcb)
        if not pcb_file.exists():
            print(f"Error: PCB file not found: {pcb_file}", file=sys.stderr)
            return 1

        # 2. CLI args → Domain configuration
        options = translate_to_placement_options(args)

        # 3. Domain service orchestration
        reader = DefaultKiCadReaderService()
        generator = POSGenerator(options)

        board = reader.read_pcb_file(pcb_file)
        pos_data = generator.generate_pos_data(board)

        # 4. Output presentation
        return present_pos_results(pos_data, args.output, args.units)

    except Exception as error:
        return handle_pos_command_error(error, args)
```

**Key Insights**:
- Handler is a pure function with no instance state
- Clear separation between input translation, orchestration, and output
- Domain services do the work; Application Layer orchestrates workflows

## Step 2: Input Translation Pattern

Convert CLI arguments to rich domain objects:

```python
def translate_to_placement_options(args: argparse.Namespace) -> PlacementOptions:
    """Translate CLI arguments to domain configuration."""
    return PlacementOptions(
        units=args.units,
        origin="board",  # Could be configurable
        smd_only=args.smd_only,
        layer_filter=args.layer
    )

def validate_pos_inputs(args: argparse.Namespace) -> None:
    """Validate CLI inputs before domain service calls."""
    pcb_path = Path(args.pcb)

    if not pcb_path.exists():
        raise FileNotFoundError(f"PCB file not found: {pcb_path}")

    if not pcb_path.suffix.lower() == ".kicad_pcb":
        raise ValueError(f"Expected .kicad_pcb file, got: {pcb_path.suffix}")

    if args.output and Path(args.output).is_dir():
        raise ValueError("Output path cannot be a directory")
```

**Key Insight**: Translation functions create well-formed domain objects and validate at the interface boundary.

## Step 3: Output Presentation Pattern

Adapt domain results for CLI presentation:

```python
def present_pos_results(pos_data: List[Dict], output: str, units: str) -> int:
    """Present POS results in CLI-appropriate format."""
    if output == "console":
        present_console_table(pos_data, units)
    elif output == "stdout" or output is None:
        present_csv_to_stdout(pos_data, units)
    else:
        write_csv_to_file(pos_data, Path(output), units)
        print(f"Position file written to {output}")

    return 0

def present_console_table(pos_data: List[Dict], units: str) -> None:
    """Rich console presentation for interactive use."""
    print(f"\nComponent Placement Data ({len(pos_data)} components)")
    print("=" * 80)

    if not pos_data:
        print("No components found.")
        return

    unit_label = "mm" if units == "mm" else "in"

    # Formatted table with proper alignment
    print(f"{'Ref':<10} {'X(' + unit_label + ')':<12} {'Y(' + unit_label + ')':<12} {'Rot':<6} {'Side':<6} {'Package':<15}")
    print("-" * 80)

    for entry in pos_data:
        x_coord = f"{entry['x_mm']:.3f}" if units == "mm" else f"{entry['x_mm']/25.4:.4f}"
        y_coord = f"{entry['y_mm']:.3f}" if units == "mm" else f"{entry['y_mm']/25.4:.4f}"

        print(f"{entry['reference']:<10} {x_coord:<12} {y_coord:<12} "
              f"{entry['rotation']:<6.1f} {entry['side']:<6} {entry['package']:<15}")

def present_csv_to_stdout(pos_data: List[Dict], units: str) -> None:
    """Raw CSV output suitable for piping."""
    writer = csv.writer(sys.stdout)

    # Headers with unit specification
    unit_label = "mm" if units == "mm" else "in"
    headers = ["Reference", f"X({unit_label})", f"Y({unit_label})", "Rotation", "Side", "Footprint", "Package"]
    writer.writerow(headers)

    # Data with unit conversion
    for entry in pos_data:
        x_coord = entry["x_mm"] if units == "mm" else entry["x_mm"] / 25.4
        y_coord = entry["y_mm"] if units == "mm" else entry["y_mm"] / 25.4

        writer.writerow([
            entry["reference"], f"{x_coord:.4f}", f"{y_coord:.4f}",
            f"{entry['rotation']:.1f}", entry["side"],
            entry["footprint"], entry["package"]
        ])
```

**Key Insights**:
- Different presentations for different use cases (interactive vs scripting)
- Domain data is translated, not modified
- Output formatters handle interface-specific concerns

## Step 4: Error Translation Pattern

Convert domain exceptions to user-friendly CLI messages:

```python
def handle_pos_command_error(error: Exception, args: argparse.Namespace) -> int:
    """Translate domain exceptions to user-friendly CLI messages."""
    if isinstance(error, KiCadParseError):
        print(f"Error reading PCB file '{args.pcb}': {error}", file=sys.stderr)
        if error.pcb_path and args.verbose:
            print(f"  File path: {error.pcb_path}", file=sys.stderr)
        return 2

    elif isinstance(error, ComponentPlacementError):
        print(f"Placement error: {error}", file=sys.stderr)
        if args.verbose:
            print(f"  Component: {error.reference}", file=sys.stderr)
            print(f"  Reason: {error.reason}", file=sys.stderr)
        return 3

    elif isinstance(error, FileNotFoundError):
        print(f"File not found: {error}", file=sys.stderr)
        return 1

    elif isinstance(error, ValueError):
        print(f"Invalid input: {error}", file=sys.stderr)
        return 1

    else:
        print(f"Unexpected error: {error}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 99
```

**Key Insight**: Error translation preserves domain exception information while providing appropriate user context.

## Step 5: CLI Registration Pattern

Register the command in `main.py`:

```python
def create_cli() -> argparse.ArgumentParser:
    """Create and configure the main CLI parser."""
    parser = argparse.ArgumentParser(
        prog="jbom",
        description="KiCad BOM and component data management tools"
    )

    # Global options
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    # Subcommand registration - explicit and maintainable
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Register all commands directly
    from jbom.cli.bom import register_command as register_bom
    from jbom.cli.inventory import register_command as register_inventory
    from jbom.cli.pos import register_command as register_pos

    register_bom(subparsers)
    register_inventory(subparsers)
    register_pos(subparsers)  # Our new command

    return parser

def main() -> int:
    """Main entry point with error handling."""
    parser = create_cli()
    args = parser.parse_args()

    if not hasattr(args, 'handler'):
        parser.print_help()
        return 1

    # Delegate to command handler
    return args.handler(args)
```

**Key Insight**: Explicit registration avoids magic discovery mechanisms and keeps the composition root simple.

## Step 6: Integration Testing

Test CLI integration with domain services:

```python
class TestPOSCommandIntegration:
    """Integration tests for POS command adapter."""

    def test_pos_command_orchestrates_services_correctly(self, tmp_path):
        """Test that POS command properly orchestrates domain services."""
        # Arrange: Create test PCB file
        test_pcb = tmp_path / "test.kicad_pcb"
        create_test_pcb_file(test_pcb)  # Test utility

        output_file = tmp_path / "output.csv"

        # Act: Execute command via CLI
        args = create_test_args(pcb=str(test_pcb), output=str(output_file))
        result = handle_pos(args)

        # Assert: Verify successful orchestration
        assert result == 0
        assert output_file.exists()

        # Verify domain results were properly translated
        with open(output_file, 'r') as f:
            content = f.read()
            assert "Reference,X(mm),Y(mm)" in content  # Headers
            assert "R1,10.0000,20.0000" in content     # Sample component

    def test_error_translation_for_invalid_pcb_file(self, tmp_path, capsys):
        """Test domain exception translation to CLI errors."""
        invalid_pcb = tmp_path / "invalid.kicad_pcb"
        invalid_pcb.write_text("not a valid pcb file")

        args = create_test_args(pcb=str(invalid_pcb))
        result = handle_pos(args)

        # Assert error handling
        assert result != 0
        captured = capsys.readouterr()
        assert "Error reading PCB file" in captured.err

    def test_input_translation_to_domain_options(self):
        """Test CLI argument translation to domain configuration."""
        args = create_test_args(
            pcb="test.kicad_pcb",
            smd_only=True,
            layer="TOP",
            units="inch"
        )

        options = translate_to_placement_options(args)

        assert options.smd_only == True
        assert options.layer_filter == "TOP"
        assert options.units == "inch"
```

**Key Insight**: Integration tests verify that adapters correctly translate between CLI and domain concerns without testing business logic.

## Step 7: Functional Test Integration

Connect Gherkin scenarios to CLI commands:

```python
@when('I run jbom pos "{pcb_file}" with options "{options}"')
def step_run_pos_command_with_options(context, pcb_file, options):
    """Execute POS command via CLI with specified options."""
    pcb_path = context.test_data_dir / pcb_file

    # Parse options into CLI args
    cmd_args = ["pos", str(pcb_path)] + options.split()

    # Use actual CLI infrastructure
    parser = create_cli()
    parsed_args = parser.parse_args(cmd_args)

    # Execute through command handler
    with io.StringIO() as output_buffer:
        old_stdout = sys.stdout
        sys.stdout = output_buffer

        result_code = parsed_args.handler(parsed_args)
        output_content = output_buffer.getvalue()

        sys.stdout = old_stdout

    # Store results for verification steps
    context.command_result = result_code
    context.command_output = output_content

@then('the CSV output should contain component "{reference}"')
def step_verify_component_in_csv(context, reference):
    """Verify specific component appears in CSV output."""
    assert reference in context.command_output

    # Parse CSV to verify format
    lines = context.command_output.strip().split('\n')
    headers = lines[0].split(',')

    # Verify proper CSV structure
    assert "Reference" in headers
    assert "X(mm)" in headers or "X(in)" in headers

    # Find component row
    for line in lines[1:]:
        if line.startswith(reference + ','):
            components = line.split(',')
            # Verify data format
            assert len(components) == len(headers)
            break
    else:
        assert False, f"Component {reference} not found in output"
```

**Key Insight**: Functional tests exercise the complete CLI-to-domain integration path using real command handlers.

## Step 8: Testing Strategy Summary

jBOM uses layered testing to ensure robustness:

**Unit Tests** (`tests/services/`):
- Test domain services in isolation
- Focus on business logic and domain rules
- Use domain objects as test data

**Integration Tests** (`tests/cli/`):
- Test CLI-to-service orchestration
- Verify input translation and error handling
- Mock external dependencies, use real services

**Functional Tests** (`features/`):
- Test complete user workflows end-to-end
- Exercise actual CLI commands with real files
- Validate user-facing behavior

## Step 9: Semantic Version Management

CLI changes impact versioning. Follow semantic versioning:

**PATCH** (1.0.1): Bug fixes in existing commands
- Fix error handling in POS command
- Improve CSV output formatting

**MINOR** (1.1.0): New functionality, backward compatible
- Add new POS command to existing CLI
- Add new options to existing commands

**MAJOR** (2.0.0): Breaking changes to CLI interface
- Change command structure or argument names
- Remove or significantly modify existing functionality

Use conventional commit messages:
```bash
git commit -m "feat(cli): add POS command for component placement files

- Add jbom pos command for PCB component placement
- Support SMD filtering and layer selection
- Output in CSV format with coordinate transformation
- Integrate with existing PCB reader service

Co-Authored-By: Warp <agent@warp.dev>"
```

## Integration Benefits

**Separation of Concerns**: CLI handles interface, services handle business logic
**Testability**: Each layer tested independently with appropriate strategies
**Maintainability**: Changes to CLI don't affect domain services and vice versa
**Extensibility**: New interfaces (GUI, API) can reuse same domain services

The POS command demonstrates how jBOM's adapter pattern enables clean integration between user interfaces and domain services while maintaining testability and architectural constraints.
