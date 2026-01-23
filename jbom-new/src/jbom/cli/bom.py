"""BOM command - thin CLI wrapper over BOM workflows."""

import argparse
import csv
import sys
from pathlib import Path
from typing import Optional

from jbom.services.schematic_reader import SchematicReader
from jbom.services.bom_generator import BOMGenerator, BOMData
from jbom.services.inventory_matcher import InventoryMatcher
from jbom.services.project_file_resolver import ProjectFileResolver
from jbom.common.options import GeneratorOptions
from jbom.config.fabricators import get_available_fabricators


def register_command(subparsers) -> None:
    """Register BOM command with argument parser."""
    parser = subparsers.add_parser(
        "bom",
        help="Generate bill of materials from KiCad schematic (aggregated for procurement)",
        description="Generate Bill of Materials (BOM) from KiCad schematic. "
        "Always aggregated by value+package for procurement.",
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
        "--inventory",
        help="Enhance BOM with inventory data from CSV file (can be specified multiple times)",
        action="append",
        dest="inventory_files",
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

    # BOM always aggregates by value+package (footprint) for procurement

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

    parser.set_defaults(handler=handle_bom)


def handle_bom(args: argparse.Namespace) -> int:
    """Handle BOM command with project-centric input resolution."""
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
                    f"Note: BOM generation requires a schematic file. "
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
        generator = BOMGenerator(
            "value_footprint"
        )  # BOM always aggregates by value+package

        # Load components from schematic (including hierarchical sheets if available)
        if resolved_input.project_context:
            # Get all hierarchical schematic files for complete BOM
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

        # Generate basic BOM
        filters = {
            "exclude_dnp": not args.include_dnp,
            "include_only_bom": not args.include_excluded,
        }
        bom_data = generator.generate_bom_data(components, project_name, filters)

        # Enhance with inventory if requested
        if args.inventory_files:
            if args.verbose:
                print(
                    f"Enhancing BOM with {len(args.inventory_files)} inventory file(s)",
                    file=sys.stderr,
                )

            # For now, use the first inventory file (single-file enhancement)
            # TODO: Implement multi-file enhancement in InventoryMatcher service
            inventory_file = Path(args.inventory_files[0])

            if not inventory_file.exists():
                print(
                    f"Error: Inventory file not found: {inventory_file}",
                    file=sys.stderr,
                )
                return 1

            if len(args.inventory_files) > 1 and args.verbose:
                print(
                    f"Note: Using primary inventory file {inventory_file}, multi-file enhancement coming soon",
                    file=sys.stderr,
                )

            matcher = InventoryMatcher()
            # Note: current matcher API uses a strategy string; fabricator can
            # be incorporated internally later. For now we keep behavior stable.
            bom_data = matcher.enhance_bom_with_inventory(
                bom_data, inventory_file, "ipn_fuzzy"
            )

        # Handle output
        return _output_bom(bom_data, args.output)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _output_bom(bom_data: BOMData, output: Optional[str]) -> int:
    """Output BOM data in the requested format.

    Human-first defaults (BREAKING CHANGE for UX consistency):
    - output is None => formatted table to stdout (human exploration)
    - output == "console" => formatted table to stdout (explicit)
    - output == "-" => CSV to stdout (machine readable)
    - "stdout" removed (legacy compatibility)
    - otherwise => treat as file path
    """
    if output is None or output == "console":
        _print_console_table(bom_data)
    elif output == "-":
        _print_csv(bom_data)
    else:
        output_path = Path(output)
        _write_csv(bom_data, output_path)
        print(f"BOM written to {output_path}")

    return 0


def _print_console_table(bom_data: BOMData) -> None:
    """Print BOM as formatted console table."""
    print(f"\n{bom_data.project_name} - Bill of Materials")
    print("=" * 60)

    if not bom_data.entries:
        print("No components found.")
        return

    # Simple table formatting
    print(f"{'References':<15} {'Value':<12} {'Footprint':<20} {'Qty':<4}")
    print("-" * 60)

    for entry in bom_data.entries:
        refs = (
            entry.references_string[:14] + "..."
            if len(entry.references_string) > 14
            else entry.references_string
        )
        value = entry.value[:11] + "..." if len(entry.value) > 11 else entry.value
        footprint = (
            entry.footprint[:19] + "..."
            if len(entry.footprint) > 19
            else entry.footprint
        )

        print(f"{refs:<15} {value:<12} {footprint:<20} {entry.quantity:<4}")

    print(
        f"\nTotal: {bom_data.total_components} components, {bom_data.total_line_items} unique items"
    )

    # Show inventory enhancement info if available
    if "matched_entries" in bom_data.metadata:
        matched = bom_data.metadata["matched_entries"]
        print(
            f"Inventory enhanced: {matched}/{bom_data.total_line_items} items matched"
        )


def _print_csv(bom_data: BOMData) -> None:
    """Print BOM as CSV to stdout."""
    writer = csv.writer(sys.stdout)

    # Headers
    headers = ["References", "Value", "Footprint", "Quantity"]

    # Add inventory headers if present
    if bom_data.entries and bom_data.entries[0].attributes.get("inventory_matched"):
        headers.extend(["Manufacturer", "Manufacturer Part", "Description", "Voltage"])

    writer.writerow(headers)

    # Data rows
    for entry in bom_data.entries:
        row = [entry.references_string, entry.value, entry.footprint, entry.quantity]

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


def _write_csv(bom_data: BOMData, output_path: Path) -> None:
    """Write BOM as CSV to file."""
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        # Use the same logic as stdout
        old_stdout = sys.stdout
        sys.stdout = csvfile
        _print_csv(bom_data)
        sys.stdout = old_stdout
