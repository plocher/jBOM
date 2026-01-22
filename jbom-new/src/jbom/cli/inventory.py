"""Inventory command - manage component inventory."""

import argparse
import csv
import sys
from pathlib import Path

from jbom.services.project_inventory import ProjectInventoryGenerator
from jbom.services.schematic_reader import SchematicReader
from jbom.services.project_file_resolver import ProjectFileResolver
from jbom.common.options import GeneratorOptions
from jbom.cli.formatting import print_inventory_table


def register_command(subparsers) -> None:
    """Register inventory command with argument parser."""
    parser = subparsers.add_parser(
        "inventory", help="Generate component inventory from project"
    )

    # Project input as main positional argument
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
        help="Output destination: file path, 'console', or '-' for stdout (default: part-inventory.csv)",
        default=None,
    )

    # Verbose mode
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    parser.set_defaults(handler=handle_inventory)


def handle_inventory(args: argparse.Namespace) -> int:
    """Handle inventory command - generate inventory from project."""
    try:
        return _handle_generate_inventory(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _handle_generate_inventory(args: argparse.Namespace) -> int:
    """Generate inventory from project components with project-centric input resolution.

    Output destination handling (following BOM command pattern):
    - None (default): write to 'part-inventory.csv'
    - "console": pretty print table to stdout
    - "-": write CSV format to stdout
    - otherwise: treat as a file path
    """

    # Create options
    options = GeneratorOptions(verbose=args.verbose) if args.verbose else None

    # Use ProjectFileResolver for intelligent input resolution
    resolver = ProjectFileResolver(
        prefer_pcb=False, target_file_type="schematic", options=options
    )

    try:
        resolved_input = resolver.resolve_input(args.input)

        # Handle cross-command intelligence - if user provided wrong file type, try to resolve it
        if not resolved_input.is_schematic:
            if args.verbose:
                print(
                    f"Note: Inventory generation requires a schematic file. "
                    f"Found {resolved_input.resolved_path.suffix} file, trying to find matching schematic.",
                    file=sys.stderr,
                )

            resolved_input = resolver.resolve_for_wrong_file_type(
                resolved_input, "schematic"
            )
            if args.verbose:
                print(
                    f"Using schematic: {resolved_input.resolved_path.name}",
                    file=sys.stderr,
                )

        schematic_file = resolved_input.resolved_path
        reader = SchematicReader(options)

        # Load components from schematic (including hierarchical sheets if available)
        if resolved_input.project_context:
            # Get all hierarchical schematic files for complete inventory
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

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Generate inventory
    generator = ProjectInventoryGenerator(components)
    inventory_items, field_names = generator.load()

    # Handle output using same pattern as BOM command
    return _output_inventory(inventory_items, field_names, args.output)
    return 0


def _output_inventory(inventory_items, field_names, output) -> int:
    """Output inventory data in the requested format.

    Special cases (following BOM pattern):
    - output == "console" => formatted table to stdout
    - output in {None, "-"} => CSV to stdout
    - otherwise => treat as file path
    """
    if output == "console":
        _print_console_table(inventory_items, field_names)
    elif output == "-":
        _print_csv(inventory_items, field_names)
    elif output is None:
        # Default to part-inventory.csv file
        output_path = Path("part-inventory.csv")
        _write_csv(inventory_items, field_names, output_path)
        print(
            f"Generated inventory with {len(inventory_items)} items written to {output_path}"
        )
    else:
        output_path = Path(output)
        _write_csv(inventory_items, field_names, output_path)
        print(
            f"Generated inventory with {len(inventory_items)} items written to {output_path}"
        )

    return 0


def _print_console_table(inventory_items, field_names) -> None:
    """Print inventory as formatted console table."""
    # Convert inventory items to dict format for print_inventory_table
    item_dicts = []
    for item in inventory_items:
        row = {
            "IPN": item.ipn,
            "Category": item.category,
            "Value": item.value,
            "Description": item.description,
            "Package": item.package,
            "Manufacturer": item.manufacturer,
            "MFGPN": item.mfgpn,
            "LCSC": item.lcsc,
            "Datasheet": item.datasheet,
            "UUID": item.uuid,
        }
        # Add any extra fields from component properties
        for field in field_names:
            if (
                field not in row
                and hasattr(item, "raw_data")
                and field in item.raw_data
            ):
                row[field] = item.raw_data[field]
        item_dicts.append(row)

    # Use the common formatting utility
    print_inventory_table(item_dicts, field_names)
    print(f"\nGenerated inventory with {len(inventory_items)} items")


def _print_csv(inventory_items, field_names) -> None:
    """Print inventory as CSV to stdout."""
    import csv

    writer = csv.DictWriter(sys.stdout, fieldnames=field_names)
    writer.writeheader()

    for item in inventory_items:
        row = {
            "IPN": item.ipn,
            "Category": item.category,
            "Value": item.value,
            "Description": item.description,
            "Package": item.package,
            "Manufacturer": item.manufacturer,
            "MFGPN": item.mfgpn,
            "LCSC": item.lcsc,
            "Datasheet": item.datasheet,
            "UUID": item.uuid,
        }
        # Add any extra fields from component properties
        for field in field_names:
            if (
                field not in row
                and hasattr(item, "raw_data")
                and field in item.raw_data
            ):
                row[field] = item.raw_data[field]
        writer.writerow(row)


def _write_csv(inventory_items, field_names, output_path: Path) -> None:
    """Write inventory as CSV to file."""
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=field_names)
        writer.writeheader()

        for item in inventory_items:
            row = {
                "IPN": item.ipn,
                "Category": item.category,
                "Value": item.value,
                "Description": item.description,
                "Package": item.package,
                "Manufacturer": item.manufacturer,
                "MFGPN": item.mfgpn,
                "LCSC": item.lcsc,
                "Datasheet": item.datasheet,
                "UUID": item.uuid,
            }
            # Add any extra fields from component properties
            for field in field_names:
                if (
                    field not in row
                    and hasattr(item, "raw_data")
                    and field in item.raw_data
                ):
                    row[field] = item.raw_data[field]
            writer.writerow(row)
