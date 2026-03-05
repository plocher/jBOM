"""Parts command - thin CLI wrapper over Parts List workflows."""

import argparse
import csv
import sys
from pathlib import Path
from typing import Optional, TextIO

from jbom.cli.output import (
    OutputDestination,
    OutputKind,
    OutputRefusedError,
    add_force_argument,
    open_output_text_file,
    resolve_output_destination,
)
from jbom.services.schematic_reader import SchematicReader
from jbom.services.parts_list_generator import PartsListGenerator, PartsListData
from jbom.services.project_file_resolver import ProjectFileResolver
from jbom.common.options import GeneratorOptions
from jbom.common.component_filters import (
    add_component_filter_arguments,
    create_filter_config,
)
from jbom.config.fabricators import get_available_fabricators
from jbom.cli.formatting import Column, print_table, get_terminal_width


def register_command(subparsers) -> None:
    """Register Parts command with argument parser."""
    parser = subparsers.add_parser(
        "parts", help="Generate parts list from KiCad schematic"
    )

    # Positional argument - now supports project-centric inputs
    parser.add_argument(
        "input",
        nargs="?",
        default=".",
        help="Path to .kicad_sch file, project directory, or base name (default: current directory)",
    )

    # Output options
    parser.add_argument(
        "-o",
        "--output",
        help='Output destination: omit for default file output, use "console" for table, "-" for CSV to stdout, or a file path',
    )
    add_force_argument(parser)

    # Enhancement options
    parser.add_argument(
        "--inventory", help="Enhance parts list with inventory data from CSV file"
    )

    # Fabricator selection (for field presets / predictable output)
    parser.add_argument(
        "--fabricator",
        choices=get_available_fabricators(),
        help="Specify PCB fabricator for field presets (default: generic)",
    )
    parser.add_argument("--jlc", action="store_true", help="Use JLC preset")
    parser.add_argument("--pcbway", action="store_true", help="Use PCBWay preset")
    parser.add_argument("--seeed", action="store_true", help="Use Seeed preset")
    parser.add_argument("--generic", action="store_true", help="Use Generic preset")

    # Component filtering options
    add_component_filter_arguments(parser)

    # Options
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    parser.set_defaults(handler=handle_parts)


def handle_parts(args: argparse.Namespace) -> int:
    """Handle Parts command with project-centric input resolution."""
    try:
        # Create options
        options = GeneratorOptions(verbose=args.verbose) if args.verbose else None

        # Use ProjectFileResolver for intelligent input resolution
        resolver = ProjectFileResolver(
            prefer_pcb=False, target_file_type="schematic", options=options
        )
        resolved_input = resolver.resolve_input(args.input)

        # Handle cross-command intelligence - if user provided wrong file type, try to resolve it
        if not resolved_input.is_schematic:
            # Provide guidance about cross-resolution unless quiet
            import os as _os

            if not _os.environ.get("JBOM_QUIET"):
                print(
                    f"Note: Parts list generation requires a schematic file. "
                    f"Found {resolved_input.resolved_path.suffix} file, trying to find matching schematic.",
                    file=sys.stderr,
                )

            try:
                resolved_input = resolver.resolve_for_wrong_file_type(
                    resolved_input, "schematic"
                )
                # Emit phrasing expected by Gherkin tests unless quiet
                import os as _os

                if not _os.environ.get("JBOM_QUIET"):
                    print(
                        f"found matching schematic {resolved_input.resolved_path.name}",
                        file=sys.stderr,
                    )
                    print(
                        f"Using schematic: {resolved_input.resolved_path.name}",
                        file=sys.stderr,
                    )
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1

        schematic_file = resolved_input.resolved_path

        if not resolved_input.project_context:
            raise ValueError("No project context available")

        project_context = resolved_input.project_context
        project_name = project_context.project_base_name
        default_output_path = (
            project_context.project_directory / f"{project_name}.parts.csv"
        )

        # Use services directly - no workflow abstraction needed
        reader = SchematicReader(options)
        generator = PartsListGenerator()

        # Load components from schematic (including hierarchical sheets if available)
        if resolved_input.project_context:
            # Get all hierarchical schematic files for complete parts list
            hierarchical_files = resolved_input.get_hierarchical_files()
            if args.verbose and len(hierarchical_files) > 1:
                print(
                    f"Processing hierarchical design with {len(hierarchical_files)} schematic files",
                    file=sys.stderr,
                )

            # Load components from all hierarchical files
            components = []
            for sch_file in hierarchical_files:
                if args.verbose:
                    print(f"Loading components from {sch_file.name}", file=sys.stderr)
                file_components = reader.load_components(sch_file)
                components.extend(file_components)
        else:
            # Load components from single schematic
            components = reader.load_components(schematic_file)

        # Determine effective fabricator (default generic)
        fabricator = args.fabricator
        if not fabricator:
            if args.jlc:
                fabricator = "jlc"
            elif args.pcbway:
                fabricator = "pcbway"
            elif args.seeed:
                fabricator = "seeed"
            elif args.generic:
                fabricator = "generic"
        if not fabricator:
            fabricator = "generic"

        # Generate basic parts list with common filtering logic
        filters = create_filter_config(args)
        parts_data = generator.generate_parts_list_data(
            components, project_name, filters
        )

        # Enhance with inventory if requested
        if args.inventory:
            inventory_file = Path(args.inventory)
            if not inventory_file.exists():
                print(
                    f"Error: Inventory file not found: {inventory_file}",
                    file=sys.stderr,
                )
                return 1

            # TODO: Implement inventory enhancement for parts list
            parts_data = _enhance_parts_with_inventory(parts_data, inventory_file)

        # Handle output
        return _output_parts(
            parts_data,
            args.output,
            project_name,
            default_output_path=default_output_path,
            force=args.force,
        )

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _enhance_parts_with_inventory(
    parts_data: PartsListData, inventory_file: Path
) -> PartsListData:
    """Enhance parts list with inventory data (placeholder implementation)."""
    # TODO: Implement inventory enhancement for parts list
    # For now, just return the parts data unchanged
    # This will be implemented when inventory matching is extended to parts lists
    return parts_data


def _output_parts(
    parts_data: PartsListData,
    output: Optional[str],
    project_name: str,
    *,
    default_output_path: Path,
    force: bool,
) -> int:
    """Output Parts List data in the requested format."""
    dest = resolve_output_destination(
        output,
        default_destination=OutputDestination(
            OutputKind.FILE, path=default_output_path
        ),
    )

    if dest.kind == OutputKind.CONSOLE:
        _print_console_table(parts_data)
        return 0

    if dest.kind == OutputKind.STDOUT:
        _print_csv(parts_data, out=sys.stdout)
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
            _print_csv(parts_data, out=f)
    except OutputRefusedError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Parts list written to {output_path}")
    return 0


# Single source of truth for parts fields: used by both CSV and console output.
# Each tuple is (PartsListEntry attribute, display header, preferred console width).
_PARTS_FIELDS: list[tuple[str, str, int]] = [
    ("refs_csv", "Refs", 20),
    ("value", "Value", 12),
    ("footprint", "Footprint", 20),
    ("package", "Package", 14),
    ("part_type", "Type", 10),
    ("tolerance", "Tolerance", 10),
    ("voltage", "Voltage", 8),
    ("dielectric", "Dielectric", 10),
]


def _print_console_table(parts_data: PartsListData) -> None:
    """Print Parts List as formatted console table."""
    print(f"\n{parts_data.project_name} - Parts List")
    print("=" * 60)

    if not parts_data.entries:
        print("No components found.")
        return

    rows = [
        {
            header: str(getattr(entry, attr, "") or "")
            for attr, header, _ in _PARTS_FIELDS
        }
        for entry in parts_data.entries
    ]
    columns = [
        Column(header=header, key=header, preferred_width=width, wrap=True)
        for _, header, width in _PARTS_FIELDS
    ]
    print_table(rows, columns, terminal_width=get_terminal_width())

    print(
        f"\nTotal: {parts_data.total_components} components in {parts_data.total_groups} groups"
    )

    # Show inventory enhancement info if available
    if "matched_entries" in parts_data.metadata:
        matched = parts_data.metadata["matched_entries"]
        print(
            f"Inventory enhanced: {matched}/{parts_data.total_components} items matched"
        )


def _print_csv(parts_data: PartsListData, *, out: TextIO) -> None:
    """Print Parts List as CSV to a file-like object."""
    writer = csv.writer(out)
    writer.writerow([header for _, header, _ in _PARTS_FIELDS])
    for entry in parts_data.entries:
        writer.writerow(
            [str(getattr(entry, attr, "") or "") for attr, _, _ in _PARTS_FIELDS]
        )
