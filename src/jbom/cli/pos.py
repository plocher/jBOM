"""POS (Position) command - generate component placement files."""

import argparse
import csv
import sys
from pathlib import Path
from typing import Any, Optional, TextIO

from jbom.cli.output import (
    OutputDestination,
    OutputKind,
    OutputRefusedError,
    add_force_argument,
    open_output_text_file,
    resolve_output_destination,
)
from jbom.services.pcb_reader import DefaultKiCadReaderService
from jbom.services.pos_generator import POSGenerator
from jbom.services.project_file_resolver import ProjectFileResolver
from jbom.common.options import PlacementOptions, GeneratorOptions
from jbom.common.cli_fabricator import (
    add_fabricator_arguments,
    resolve_fabricator_from_args,
)
from jbom.common.field_parser import parse_fields_argument
from jbom.common.fields import field_to_header
from jbom.common.component_filters import (
    add_component_filter_arguments,
    create_filter_config,
)
from jbom.config.fabricators import (
    FabricatorConfig,
    get_fabricator_default_fields,
)
from jbom.cli.formatting import Column, print_table, get_terminal_width
from jbom.services.fabricator_projection_service import FabricatorProjectionService

_NUMERIC_POS_FIELDS: frozenset[str] = frozenset({"x", "y", "rotation"})


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
        help='Output destination: omit for default file output, use "console" for table, "-" for CSV to stdout, or a file path',
    )
    add_force_argument(parser)

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

    # Units flag retained for backward compatible CLI help and UX tests.
    # POS currently always uses mm internally.
    parser.add_argument(
        "--units",
        choices=["mm"],
        default="mm",
        help="Units for POS output (mm only)",
    )

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
        help=(
            "Select specific fields for POS output. Comma-separated list or +preset. "
            "Any field name is accepted; unknown fields produce blank cells. "
            "Use --list-fields to see known fields."
        ),
    )

    parser.add_argument(
        "--list-fields",
        action="store_true",
        help="List available fields and presets, then exit",
    )

    # Component filtering (POS-specific: only DNP filtering applies)
    add_component_filter_arguments(parser, command_type="pos")

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

        if not resolved_input.project_context:
            raise ValueError("No project context available")

        project_context = resolved_input.project_context
        project_name = project_context.project_base_name
        default_output_path = (
            project_context.project_directory / f"{project_name}.pos.csv"
        )

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

        # Create component filter configuration (for future DNP filtering support)
        component_filters = create_filter_config(args, command_type="pos")
        if args.verbose and not component_filters.get("exclude_dnp", True):
            print(
                "Note: --include-dnp specified but DNP filtering not yet implemented for POS",
                file=sys.stderr,
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
            # Permissive: unknown fields are accepted and produce blank cells.
            # No strict validation — jBOM is a flexible tool, not a gatekeeper.

        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        # Handle output
        return _output_pos(
            pos_data,
            args.output,
            fabricator,
            selected_fields,
            user_specified_fields,
            default_output_path=default_output_path,
            force=args.force,
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
    """List known POS fields and fabricator defaults.

    Fields are dynamically derived from the POS schema. Any field name is accepted;
    unknown fields produce blank cells.

    Args:
        fabricator: Current fabricator ID
    """
    from jbom.common.fields import field_to_header

    known_fields = _get_available_pos_fields()

    print(
        "\nKnown POS fields (any field name is accepted — unknown fields produce blank cells):"
    )
    print("=" * 60)
    for field_name in sorted(known_fields.keys()):
        desc = known_fields[field_name]
        header = field_to_header(field_name)
        print(f"  {field_name:<30}  ({header}):  {desc}")

    # Show default fields for the active fabricator
    default_fields = get_fabricator_default_fields(fabricator, "pos")
    if default_fields:
        print(
            f"\nDefault fields for {fabricator} fabricator (when --fields not specified):"
        )
        print(f"  {', '.join(default_fields)}")


def _resolve_pos_output_projection(
    *,
    selected_fields: list[str] | None,
    fabricator: str,
    user_specified_fields: bool,
    projection_service: FabricatorProjectionService | None = None,
) -> tuple[list[str], list[str], Optional[FabricatorConfig]]:
    """Resolve effective POS fields, headers, and fabricator config."""

    effective_fields = list(selected_fields) if selected_fields else []
    if not effective_fields:
        effective_fields = get_fabricator_default_fields(fabricator, "pos") or [
            "reference",
            "x",
            "y",
            "rotation",
            "side",
            "footprint",
            "package",
        ]

    service = projection_service or FabricatorProjectionService()
    projection = service.build_projection(
        fabricator_id=fabricator,
        output_type="pos",
        selected_fields=effective_fields,
    )

    headers = (
        [field_to_header(field) for field in effective_fields]
        if user_specified_fields
        else list(projection.headers)
    )
    return effective_fields, headers, projection.fabricator_config


def _output_pos(
    pos_data: list,
    output: str | None,
    fabricator: str = "generic",
    selected_fields: list | None = None,
    user_specified_fields: bool = False,
    *,
    default_output_path: Path,
    force: bool,
) -> int:
    """Output position data in the requested format."""
    selected_fields, headers, fabricator_config = _resolve_pos_output_projection(
        selected_fields=selected_fields,
        fabricator=fabricator,
        user_specified_fields=user_specified_fields,
    )

    dest = resolve_output_destination(
        output,
        default_destination=OutputDestination(
            OutputKind.FILE, path=default_output_path
        ),
    )

    if dest.kind == OutputKind.CONSOLE:
        _print_console_table(
            pos_data,
            selected_fields,
            headers,
            fabricator_id=fabricator,
            fabricator_config=fabricator_config,
        )
        return 0

    if dest.kind == OutputKind.STDOUT:
        _print_csv(
            pos_data,
            selected_fields,
            headers,
            out=sys.stdout,
            fabricator_id=fabricator,
            fabricator_config=fabricator_config,
        )
        return 0

    if not dest.path:
        raise ValueError("Internal error: file output selected but no path provided")

    output_path = dest.path
    refused = f"Error: Output file '{output_path}' already exists. Use -F/--force to overwrite."

    try:
        with open_output_text_file(
            output_path,
            force=force,
            refused_message=refused,
        ) as f:
            _print_csv(
                pos_data,
                selected_fields,
                headers,
                out=f,
                fabricator_id=fabricator,
                fabricator_config=fabricator_config,
            )
    except OutputRefusedError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Position file written to {output_path}")
    return 0


def _print_console_table(
    pos_data: list,
    selected_fields: list,
    headers: list,
    *,
    fabricator_id: str,
    fabricator_config: Optional[FabricatorConfig],
) -> None:
    """Print position data as formatted console table."""
    print(f"\nComponent Placement Data ({len(pos_data)} components)")
    print("=" * 80)

    if not pos_data:
        print("No components found.")
        return

    rows = [
        {
            h: _get_pos_field_value(
                entry,
                f,
                fabricator_id=fabricator_id,
                fabricator_config=fabricator_config,
            )
            for f, h in zip(selected_fields, headers)
        }
        for entry in pos_data
    ]
    columns = [
        Column(
            header=h,
            key=h,
            preferred_width=max(10, len(h)),
            wrap=False,
            align="right" if f in _NUMERIC_POS_FIELDS else "left",
        )
        for f, h in zip(selected_fields, headers)
    ]
    print_table(rows, columns, terminal_width=get_terminal_width())

    print(f"\nTotal: {len(pos_data)} components")


def _print_csv(
    pos_data: list,
    selected_fields: list,
    headers: list,
    *,
    out: TextIO,
    fabricator_id: str,
    fabricator_config: Optional[FabricatorConfig],
) -> None:
    """Print position data as CSV to a file-like object."""

    # QUOTE_ALL ensures values like "0603" are written as "\"0603\"" so
    # spreadsheet apps treat them as text and preserve leading zeros.
    writer = csv.writer(out, quoting=csv.QUOTE_ALL)

    # Use headers exactly as provided by fabricator column mapping
    writer.writerow(headers)

    # Data rows - output only selected fields in specified order
    for entry in pos_data:
        row = []
        for field in selected_fields:
            value = _get_pos_field_value(
                entry,
                field,
                fabricator_id=fabricator_id,
                fabricator_config=fabricator_config,
            )
            row.append(value)
        writer.writerow(row)


def _resolve_fabricator_part_number(
    entry: dict[str, Any],
    *,
    fabricator_id: str,
    fabricator_config: Optional[FabricatorConfig],
) -> str:
    """Resolve fabricator part number using shared projection service behavior."""

    return FabricatorProjectionService.resolve_fabricator_part_number(
        entry,
        fabricator_id=fabricator_id,
        fabricator_config=fabricator_config,
    )


def _get_pos_field_value(
    entry: dict[str, Any],
    field: str,
    *,
    fabricator_id: str = "generic",
    fabricator_config: Optional[FabricatorConfig] = None,
) -> str:
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

    if field == "fabricator_part_number":
        return _resolve_fabricator_part_number(
            entry,
            fabricator_id=fabricator_id,
            fabricator_config=fabricator_config,
        )

    # Handle standard POS fields
    field_mapping = {
        "reference": "reference",
        "side": "side",
        "footprint": "footprint",
        "package": "package",
        "value": "value",  # This would need to come from schematic data
    }

    if field in field_mapping:
        pos_key = field_mapping[field]
        return str(entry.get(pos_key, ""))

    # Fallback for unknown fields
    return str(entry.get(field, ""))
