"""BOM command - thin CLI wrapper over BOM workflows."""

import argparse
import csv
import sys
from pathlib import Path
from typing import Optional

from jbom.services.schematic_reader import SchematicReader
from jbom.services.bom_generator import BOMGenerator, BOMData
from jbom.services.inventory_matcher import InventoryMatcher
from jbom.common.options import GeneratorOptions


def register_command(subparsers) -> None:
    """Register BOM command with argument parser."""
    parser = subparsers.add_parser(
        "bom", help="Generate bill of materials from KiCad schematic"
    )

    # Positional argument
    parser.add_argument("schematic", help="Path to .kicad_sch file")

    # Output options
    parser.add_argument(
        "-o",
        "--output",
        help='Output file path, "stdout" for stdout, or "console" for formatted table',
    )

    # Enhancement options
    parser.add_argument(
        "--inventory", help="Enhance BOM with inventory data from CSV file"
    )

    # Fabricator selection (for field presets / predictable output)
    parser.add_argument(
        "--fabricator",
        choices=["generic", "jlc", "pcbway", "seeed"],
        help="Specify PCB fabricator for field presets (default: generic)",
    )
    parser.add_argument("--jlc", action="store_true", help="Use JLC preset")
    parser.add_argument("--pcbway", action="store_true", help="Use PCBWay preset")
    parser.add_argument("--seeed", action="store_true", help="Use Seeed preset")
    parser.add_argument("--generic", action="store_true", help="Use Generic preset")

    # Aggregation options
    parser.add_argument(
        "--aggregation",
        choices=["value_footprint", "value_only", "lib_id_value"],
        default="value_footprint",
        help="Component aggregation strategy",
    )

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
    """Handle BOM command - pure CLI logic."""
    try:
        schematic_file = Path(args.schematic)

        if not schematic_file.exists():
            print(f"Error: Schematic file not found: {schematic_file}", file=sys.stderr)
            return 1

        # Create options
        options = GeneratorOptions(verbose=args.verbose) if args.verbose else None
        project_name = schematic_file.stem

        # Use services directly - no workflow abstraction needed
        reader = SchematicReader(options)
        generator = BOMGenerator(args.aggregation)

        # Load components from schematic
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
        if args.inventory:
            inventory_file = Path(args.inventory)
            if not inventory_file.exists():
                print(
                    f"Error: Inventory file not found: {inventory_file}",
                    file=sys.stderr,
                )
                return 1

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
    """Output BOM data in the requested format."""
    if output == "console":
        # Formatted table output
        _print_console_table(bom_data)
    elif output == "stdout" or output is None:
        # CSV to stdout
        _print_csv(bom_data)
    else:
        # CSV to file
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
