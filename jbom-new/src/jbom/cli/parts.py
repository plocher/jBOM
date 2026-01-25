"""Parts command - thin CLI wrapper over Parts List workflows."""

import argparse
import csv
import sys
from pathlib import Path
from typing import Optional

from jbom.services.schematic_reader import SchematicReader
from jbom.services.parts_list_generator import PartsListGenerator, PartsListData
from jbom.services.project_file_resolver import ProjectFileResolver
from jbom.common.options import GeneratorOptions
from jbom.config.fabricators import get_available_fabricators


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
        help='Output file path, "stdout" for stdout, or "console" for formatted table',
    )

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

    # Filtering options
    parser.add_argument(
        "--include-dnp",
        action="store_true",
        help='Include "do not populate" components',
    )

    parser.add_argument(
        "--include-excluded",
        action="store_true",
        help="Include components excluded from BOM",
    )

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

        # Determine project name from context or file
        if resolved_input.project_context:
            project_name = resolved_input.project_context.project_base_name
        else:
            project_name = schematic_file.stem

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

        # Generate basic parts list
        filters = {
            "exclude_dnp": not args.include_dnp,
            "include_only_bom": not args.include_excluded,
        }
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
        return _output_parts(parts_data, args.output, project_name)

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
    parts_data: PartsListData, output: Optional[str], project_name: str
) -> int:
    """Output Parts List data in the requested format.

    Special cases:
    - output in {None, "stdout", "-"} => CSV to stdout
    - output == "console" => formatted table to stdout
    - otherwise => treat as file path
    """
    if output == "console":
        _print_console_table(parts_data)
    elif output in (None, "stdout", "-"):
        _print_csv(parts_data)
    else:
        output_path = Path(output)
        _write_csv(parts_data, output_path)
        print(f"Parts list written to {output_path}")

    return 0


def _print_console_table(parts_data: PartsListData) -> None:
    """Print Parts List as formatted console table."""
    print(f"\n{parts_data.project_name} - Parts List")
    print("=" * 60)

    if not parts_data.entries:
        print("No components found.")
        return

    # Simple table formatting
    print(f"{'Reference':<12} {'Value':<12} {'Footprint':<20}")
    print("-" * 60)

    for entry in parts_data.entries:
        ref = entry.reference[:11] if len(entry.reference) > 11 else entry.reference
        value = entry.value[:11] + "..." if len(entry.value) > 11 else entry.value
        footprint = (
            entry.footprint[:19] + "..."
            if len(entry.footprint) > 19
            else entry.footprint
        )

        print(f"{ref:<12} {value:<12} {footprint:<20}")

    print(f"\nTotal: {parts_data.total_components} components")

    # Show inventory enhancement info if available
    if "matched_entries" in parts_data.metadata:
        matched = parts_data.metadata["matched_entries"]
        print(
            f"Inventory enhanced: {matched}/{parts_data.total_components} items matched"
        )


def _print_csv(parts_data: PartsListData) -> None:
    """Print Parts List as CSV to stdout."""
    writer = csv.writer(sys.stdout)

    # Headers
    headers = ["Reference", "Value", "Footprint"]

    # Add inventory headers if present
    if parts_data.entries and parts_data.entries[0].attributes.get("inventory_matched"):
        headers.extend(["Manufacturer", "Manufacturer Part", "Description", "Voltage"])

    writer.writerow(headers)

    # Data rows
    for entry in parts_data.entries:
        row = [entry.reference, entry.value, entry.footprint]

        # Add inventory data if present
        if entry.attributes.get("inventory_matched"):
            row.extend(
                [
                    entry.attributes.get("manufacturer", ""),
                    entry.attributes.get("manufacturer_part", ""),
                    entry.attributes.get("description", ""),
                    entry.attributes.get("voltage", ""),
                ]
            )

        writer.writerow(row)


def _write_csv(parts_data: PartsListData, output_path: Path) -> None:
    """Write Parts List as CSV to file."""
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        # Use the same logic as stdout
        old_stdout = sys.stdout
        sys.stdout = csvfile
        _print_csv(parts_data)
        sys.stdout = old_stdout
