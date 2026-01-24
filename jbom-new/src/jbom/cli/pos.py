"""POS (Position) command - generate component placement files."""

import argparse
import csv
import sys
from pathlib import Path

from jbom.services.pcb_reader import DefaultKiCadReaderService
from jbom.services.pos_generator import POSGenerator
from jbom.services.project_file_resolver import ProjectFileResolver
from jbom.common.options import PlacementOptions, GeneratorOptions
from jbom.common.cli_fabricator import (
    add_fabricator_arguments,
    resolve_fabricator_from_args,
)
from jbom.common.field_parser import (
    parse_fields_argument,
    validate_fields_against_available,
)
from jbom.common.fields import field_to_header
from jbom.config.fabricators import (
    get_fabricator_default_fields,
    apply_fabricator_column_mapping,
)


def register_command(subparsers) -> None:
    """Register pos command with argument parser."""
    parser = subparsers.add_parser(
        "pos", help="Generate component placement files from KiCad PCB"
    )

    # Positional argument - now supports project-centric inputs
    parser.add_argument(
        "input",
        nargs="?",
        default=".",
        help="Path to .kicad_pcb file, project directory, or base name (default: current directory)",
    )

    # Output options
    parser.add_argument(
        "-o",
        "--output",
        help='Output file path, "stdout" for stdout, or "console" for formatted table',
    )

    # Filtering options
    parser.add_argument(
        "--smd-only",
        action="store_true",
        help="Include only SMD components",
    )

    parser.add_argument(
        "--layer",
        choices=["TOP", "BOTTOM"],
        help="Include only components on specified layer",
    )

    # Unit options removed: POS always uses mm and echoes raw tokens from PCB

    # Origin options
    parser.add_argument(
        "--origin",
        choices=["board", "aux"],
        default="board",
        help="Origin reference (default: board)",
    )

    # Field selection options
    parser.add_argument(
        "-f",
        "--fields",
        help="Comma-separated field list or preset (+minimal, +standard, +jlc, etc.)",
    )

    parser.add_argument(
        "--list-fields",
        action="store_true",
        help="List available fields and presets, then exit",
    )

    # Fabricator selection (for field presets / predictable output)
    add_fabricator_arguments(parser)

    # Options
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    parser.set_defaults(handler=handle_pos)


def handle_pos(args: argparse.Namespace) -> int:
    """Handle POS command with project-centric input resolution."""
    try:
        # Create options
        gen_options = GeneratorOptions(verbose=args.verbose) if args.verbose else None

        # Resolve fabricator from arguments
        fabricator = resolve_fabricator_from_args(args)

        # Handle --list-fields before processing
        if args.list_fields:
            _list_available_pos_fields(fabricator)
            return 0

        # Use ProjectFileResolver for intelligent input resolution
        resolver = ProjectFileResolver(
            prefer_pcb=True, target_file_type="pcb", options=gen_options
        )
        resolved_input = resolver.resolve_input(args.input)

        # Handle cross-command intelligence - if user provided wrong file type, try to resolve it
        if not resolved_input.is_pcb:
            # Provide guidance about cross-resolution unless quiet
            import os as _os

            if not _os.environ.get("JBOM_QUIET"):
                print(
                    f"Note: POS generation requires a PCB file. "
                    f"Found {resolved_input.resolved_path.suffix} file, trying to find matching PCB.",
                    file=sys.stderr,
                )

            resolved_input = resolver.resolve_for_wrong_file_type(resolved_input, "pcb")
            # Emit phrasing expected by Gherkin tests unless quiet
            import os as _os

            if not _os.environ.get("JBOM_QUIET"):
                print(
                    f"found matching PCB {resolved_input.resolved_path.name}",
                    file=sys.stderr,
                )
                print(
                    f"Using PCB: {resolved_input.resolved_path.name}", file=sys.stderr
                )

        pcb_file = resolved_input.resolved_path

        # If project has hierarchical schematics, emit a helpful diagnostic (tests expect this)
        if resolved_input.project_context:
            try:
                hier_files = (
                    resolved_input.project_context.get_hierarchical_schematic_files()
                )
                if hier_files and len(hier_files) > 1:
                    print("Processing hierarchical design", file=sys.stderr)
            except Exception:
                pass

        # Create placement options - units removed, always mm with raw token echo
        options = PlacementOptions(
            origin=args.origin,
            smd_only=args.smd_only,
            layer_filter=args.layer,
        )

        # Use services to generate POS data
        reader = DefaultKiCadReaderService()
        generator = POSGenerator(options)

        # Read PCB data
        board = reader.read_pcb_file(pcb_file)

        # Generate position data
        pos_data = generator.generate_pos_data(board)

        # Parse field selection with fabricator awareness
        available_pos_fields = _get_available_pos_fields()
        # NOTE: Don't pass BOM fabricator_presets to POS - they contain incompatible fields
        # POS uses get_fabricator_default_fields() instead

        # Explicitly reject empty --fields (e.g., --fields '' or only commas)
        if args.fields is not None:
            raw = [t.strip() for t in args.fields.split(",")]
            tokens = []
            for tok in raw:
                if not tok:
                    continue
                if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in ("'", '"'):
                    tok = tok[1:-1].strip()
                if tok:
                    tokens.append(tok)
            if not tokens:
                print("Error: --fields parameter cannot be empty", file=sys.stderr)
                return 1

        # Track whether fields were user-specified or came from fabricator defaults
        # If user specified a non-generic fabricator, treat field additions as fabricator preset modifications
        user_specified_fields = args.fields is not None and fabricator == "generic"

        try:
            selected_fields = parse_fields_argument(
                args.fields,
                available_pos_fields,
                fabricator,
                None,  # No BOM presets for POS
                context="pos",
            )
            # Validate fields
            validate_fields_against_available(selected_fields, available_pos_fields)

            # Check for fabricator completeness warnings if fabricator specified but custom fields used
            if args.fields and fabricator != "generic":
                from jbom.common.field_parser import check_fabricator_field_completeness

                # Don't use BOM presets for POS completeness check
                warning = check_fabricator_field_completeness(
                    selected_fields, fabricator, None
                )
                if warning:
                    print(f"Warning: {warning}", file=sys.stderr)

        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        # Handle output
        return _output_pos(
            pos_data, args.output, fabricator, selected_fields, user_specified_fields
        )

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _get_available_pos_fields() -> dict:
    """Get available POS fields with descriptions.

    Returns:
        Dict mapping field names to descriptions
    """
    return {
        "reference": "Component reference designator (R1, C1, etc.)",
        "x": "X coordinate",
        "y": "Y coordinate",
        "rotation": "Rotation angle in degrees",
        "side": "PCB side (TOP/BOTTOM)",
        "footprint": "KiCad footprint name",
        "package": "Component package/case size",
        "value": "Component value",
        "fabricator_part_number": "Fabricator-specific part number",
    }


def _list_available_pos_fields(fabricator: str) -> None:
    """List available POS fields and fabricator presets.

    Args:
        fabricator: Current fabricator ID
    """
    available_fields = _get_available_pos_fields()
    # NOTE: Don't show BOM presets for POS - they contain incompatible fields

    print(f"\nAvailable POS Fields for {fabricator} fabricator:")
    print("=" * 50)

    for field, description in available_fields.items():
        print(f"  {field:<15} - {description}")

    print("\nFabricator Presets:")
    print("  No POS-specific presets available (POS uses fabricator column mapping)")

    # Show default fields if no --fields specified
    default_fields = get_fabricator_default_fields(fabricator, "pos")
    if default_fields:
        print("\nDefault fields (when no --fields specified):")
        print(f"  {', '.join(default_fields)}")


def _output_pos(
    pos_data: list,
    output: str,
    fabricator: str = "generic",
    selected_fields: list = None,
    user_specified_fields: bool = False,
) -> int:
    """Output position data in the requested format.

    Human-first defaults (BREAKING CHANGE for UX consistency):
    - output is None => formatted table to stdout (human exploration)
    - output == "console" => formatted table to stdout (explicit)
    - output == "-" => CSV to stdout (machine readable)
    - "stdout" removed (legacy compatibility)
    - otherwise => treat as file path

    Args:
        pos_data: List of position data dictionaries
        output: Output destination
        fabricator: Fabricator ID for column mapping
        selected_fields: List of selected field names to include
        user_specified_fields: Whether fields were explicitly specified by user
    """
    # Use default fields if none selected
    if not selected_fields:
        # Try to get fabricator default fields, fall back to standard set
        selected_fields = get_fabricator_default_fields(fabricator, "pos")
        if not selected_fields:
            selected_fields = [
                "reference",
                "x",
                "y",
                "rotation",
                "side",
                "footprint",
                "package",
            ]
        # Mark that these came from fabricator defaults, not user specification
        user_specified_fields = False

    # Apply fabricator column mapping only for fabricator presets, not user-specified fields
    if user_specified_fields:
        # User specified exact field names - use them as headers with proper display names
        headers = [field_to_header(field) for field in selected_fields]
    else:
        # Fabricator preset - use fabricator-specific column names
        headers = apply_fabricator_column_mapping(fabricator, "pos", selected_fields)

    if output is None or output == "console":
        _print_console_table(pos_data, selected_fields, headers)
    elif output == "-":
        _print_csv(pos_data, selected_fields, headers)
    else:
        output_path = Path(output)
        _write_csv(pos_data, output_path, selected_fields, headers)
        print(f"Position file written to {output_path}")

    return 0


def _print_console_table(pos_data: list, selected_fields: list, headers: list) -> None:
    """Print position data as formatted console table."""
    print(f"\nComponent Placement Data ({len(pos_data)} components)")
    print("=" * 80)

    if not pos_data:
        print("No components found.")
        return

    # Use provided headers and selected fields
    # For console display, use abbreviated headers if too long
    display_headers = []
    for header in headers:
        if len(header) > 12:
            # Abbreviate long headers for console display
            abbrev = header[:10] + ".."
        else:
            abbrev = header
        display_headers.append(abbrev)

    # Print dynamic header based on selected fields
    header_line = ""
    for i, header in enumerate(display_headers):
        width = 12 if i > 0 else 10  # First column (reference) slightly narrower
        header_line += f"{header:<{width}} "

    print(header_line)
    print("-" * len(header_line))

    for entry in pos_data:
        row_values = []
        for field in selected_fields:
            value = _get_pos_field_value(entry, field)
            # Truncate values that are too long for display
            width = 12 if len(row_values) > 0 else 10  # First column narrower
            if len(value) > width:
                value = value[: width - 3] + "..."
            row_values.append(value)

        # Format row with dynamic widths
        formatted_values = []
        for i, value in enumerate(row_values):
            width = 12 if i > 0 else 10
            formatted_values.append(f"{value:<{width}}")

        print(" ".join(formatted_values))

    print(f"\nTotal: {len(pos_data)} components")


def _print_csv(pos_data: list, selected_fields: list, headers: list) -> None:
    """Print position data as CSV to stdout."""
    writer = csv.writer(sys.stdout)

    # Use headers exactly as provided by fabricator column mapping
    writer.writerow(headers)

    # Data rows - output only selected fields in specified order
    for entry in pos_data:
        row = []
        for field in selected_fields:
            value = _get_pos_field_value(entry, field)
            row.append(value)
        writer.writerow(row)


def _get_pos_field_value(entry: dict, field: str) -> str:
    """Extract field value from POS entry.

    Args:
        entry: POS entry dictionary
        field: Field name to extract

    Returns:
        String value for the field
    """
    # Handle coordinate/rotation fields
    if field == "x":
        if entry.get("x_raw"):
            return str(entry["x_raw"])  # echo exactly as authored in PCB (mm)
        return f"{entry['x_mm']:.4f}"
    elif field == "y":
        if entry.get("y_raw"):
            return str(entry["y_raw"])  # echo exactly as authored in PCB (mm)
        return f"{entry['y_mm']:.4f}"
    elif field == "rotation":
        if entry.get("rotation_raw") is not None:
            return str(entry["rotation_raw"])  # echo raw if available
        return f"{entry['rotation']:.1f}"

    # Handle standard POS fields
    field_mapping = {
        "reference": "reference",
        "side": "side",
        "footprint": "footprint",
        "package": "package",
        "value": "value",  # This would need to come from schematic data
        "fabricator_part_number": "fabricator_part_number",  # From component properties
    }

    if field in field_mapping:
        pos_key = field_mapping[field]
        return str(entry.get(pos_key, ""))

    # Fallback for unknown fields
    return str(entry.get(field, ""))


def _write_csv(
    pos_data: list,
    output_path: Path,
    selected_fields: list = None,
    headers: list = None,
) -> None:
    """Write position data as CSV to file."""
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        # Use the same logic as stdout
        old_stdout = sys.stdout
        sys.stdout = csvfile
        _print_csv(pos_data, selected_fields, headers)
        sys.stdout = old_stdout
