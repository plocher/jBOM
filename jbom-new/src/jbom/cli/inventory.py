"""Inventory command - manage component inventory."""

import argparse
import sys
from pathlib import Path

from jbom.services.inventory_reader import InventoryReader
from jbom.services.project_inventory import ProjectInventoryGenerator
from jbom.services.schematic_reader import SchematicReader
from jbom.services.project_file_resolver import ProjectFileResolver
from jbom.common.options import GeneratorOptions


def register_command(subparsers) -> None:
    """Register inventory command with argument parser."""
    parser = subparsers.add_parser(
        "inventory", help="Generate and manage component inventory"
    )

    # Subcommands for inventory
    inv_subparsers = parser.add_subparsers(
        title="inventory commands",
        dest="inventory_command",
        help="inventory operations",
    )

    # Generate inventory from project
    gen_parser = inv_subparsers.add_parser(
        "generate", help="Generate inventory from project components"
    )
    gen_parser.add_argument(
        "input",
        nargs="?",
        default=".",
        help="Path to .kicad_sch file, project directory, or base name (default: current directory)",
    )
    gen_parser.add_argument(
        "-o", "--output", help="Output inventory CSV file", required=True
    )
    gen_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose output"
    )

    # List inventory
    list_parser = inv_subparsers.add_parser("list", help="List inventory items")
    list_parser.add_argument("inventory_file", help="Path to inventory CSV file")
    list_parser.add_argument("--category", help="Filter by category", default=None)

    parser.set_defaults(handler=handle_inventory)


def handle_inventory(args: argparse.Namespace) -> int:
    """Handle inventory command."""
    try:
        if not args.inventory_command:
            print("Error: No inventory command specified", file=sys.stderr)
            return 1

        if args.inventory_command == "generate":
            return _handle_generate_inventory(args)
        elif args.inventory_command == "list":
            return _handle_list_inventory(args)
        else:
            print(
                f"Error: Unknown inventory command: {args.inventory_command}",
                file=sys.stderr,
            )
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _handle_generate_inventory(args: argparse.Namespace) -> int:
    """Generate inventory from project components with project-centric input resolution."""
    output_file = Path(args.output)

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

    # Write to CSV
    import csv

    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
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

    print(
        f"Generated inventory with {len(inventory_items)} items written to {output_file}"
    )
    return 0


def _handle_list_inventory(args: argparse.Namespace) -> int:
    """List inventory items."""
    inventory_file = Path(args.inventory_file)

    if not inventory_file.exists():
        print(f"Error: Inventory file not found: {inventory_file}", file=sys.stderr)
        return 1

    # Load inventory
    reader = InventoryReader(inventory_file)
    inventory_items, _ = reader.load()

    # Filter by category if specified
    if args.category:
        inventory_items = [
            item
            for item in inventory_items
            if item.category.lower() == args.category.lower()
        ]

    # Display items
    print(f"\nInventory: {len(inventory_items)} items")
    print("=" * 80)

    if not inventory_items:
        print("No items found.")
        return 0

    print(f"{'IPN':<20} {'Category':<15} {'Value':<15} {'Description':<30}")
    print("-" * 80)

    for item in inventory_items:
        ipn = item.ipn[:19] + "..." if len(item.ipn) > 19 else item.ipn
        category = (
            item.category[:14] + "..." if len(item.category) > 14 else item.category
        )
        value = item.value[:14] + "..." if len(item.value) > 14 else item.value
        desc = (
            item.description[:29] + "..."
            if len(item.description) > 29
            else item.description
        )

        print(f"{ipn:<20} {category:<15} {value:<15} {desc:<30}")

    return 0
