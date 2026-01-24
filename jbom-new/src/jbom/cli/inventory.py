"""Inventory command - manage component inventory."""

import argparse
import csv
import sys
from pathlib import Path
from datetime import datetime
import shutil

from jbom.services.project_inventory import ProjectInventoryGenerator
from jbom.services.schematic_reader import SchematicReader
from jbom.services.project_file_resolver import ProjectFileResolver
from jbom.services.component_inventory_matcher import ComponentInventoryMatcher
from jbom.common.options import GeneratorOptions
from jbom.cli.formatting import print_inventory_table


def register_command(subparsers) -> None:
    """Register inventory command with argument parser."""
    parser = subparsers.add_parser(
        "inventory",
        help="Generate component inventory from project",
        description="Generate component inventory from project",
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

    # Inventory merge options
    parser.add_argument(
        "--inventory",
        help="Path to existing inventory CSV file for merge operations (can be specified multiple times)",
        type=Path,
        action="append",
        dest="inventory_files",
    )

    parser.add_argument(
        "--filter-matches",
        action="store_true",
        help="Filter out components that match existing inventory items",
    )

    # Safety options
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing output files without confirmation",
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

    # Check for empty components list
    if not components:
        print(
            "Error: No components found in project. Cannot create inventory from empty schematic.",
            file=sys.stderr,
        )
        return 1

    # Generate inventory
    generator = ProjectInventoryGenerator(components)
    inventory_items, field_names = generator.load()

    # Apply inventory filtering if requested
    if args.inventory_files or args.filter_matches:
        inventory_items = _apply_inventory_filtering(
            inventory_items, args.inventory_files, args.filter_matches, args.verbose
        )

    # Handle output using same pattern as BOM command
    return _output_inventory(
        inventory_items, field_names, args.output, args.force, args.verbose
    )


def _apply_inventory_filtering(
    inventory_items, inventory_files, filter_matches, verbose
):
    """Apply inventory filtering based on existing inventory matches.

    Args:
        inventory_items: List of inventory items from the project
        inventory_files: List of paths to existing inventory CSV files (first has precedence)
        filter_matches: If True, filter OUT matched components (show only new ones)
        verbose: Enable verbose output

    Returns:
        Filtered list of inventory items
    """
    if not inventory_files:
        if filter_matches:
            print(
                "Warning: --filter-matches requires --inventory file(s)",
                file=sys.stderr,
            )
        return inventory_items

    # Initialize matcher with merged inventory from multiple sources
    try:
        matcher = ComponentInventoryMatcher()
        merged_inventory = []
        seen_ipns = set()  # Track IPNs for precedence
        total_files_loaded = 0

        if verbose:
            print(
                f"Loading {len(inventory_files)} inventory file(s) with precedence order:",
                file=sys.stderr,
            )

        # Load files in order - first file has highest precedence
        for i, inventory_file in enumerate(inventory_files):
            try:
                from jbom.services.inventory_reader import InventoryReader

                reader = InventoryReader(inventory_file)
                file_inventory, _ = reader.load()

                added_count = 0
                for item in file_inventory:
                    if item.ipn not in seen_ipns:  # First occurrence wins (precedence)
                        merged_inventory.append(item)
                        seen_ipns.add(item.ipn)
                        added_count += 1

                total_files_loaded += 1
                if verbose:
                    precedence = "primary" if i == 0 else f"precedence {i+1}"
                    print(
                        f"  {precedence}: {inventory_file} ({added_count}/{len(file_inventory)} items added)",
                        file=sys.stderr,
                    )

            except FileNotFoundError:
                print(
                    f"Error: Inventory file not found: {inventory_file}",
                    file=sys.stderr,
                )
            except Exception as e:
                print(f"Error loading {inventory_file}: {e}", file=sys.stderr)

        if not merged_inventory:
            print("Error: No inventory items loaded from any file", file=sys.stderr)
            return inventory_items

        # Set the merged inventory in the matcher
        matcher.set_inventory(merged_inventory)

        if verbose:
            print(
                f"Merged inventory: {len(merged_inventory)} total items from {total_files_loaded} file(s)",
                file=sys.stderr,
            )

    except Exception as e:
        print(f"Error loading inventories: {e}", file=sys.stderr)
        return inventory_items

    # Apply filtering logic
    filtered_items = []
    matched_count = 0

    for item in inventory_items:
        # Convert inventory item to component data format for matching
        component_data = {
            "value": item.value or "",
            "footprint": "",  # inventory items don't have footprint info
            "lib_id": f"{item.category}:{item.value}"
            if item.category and item.value
            else "",
            "properties": {},
        }

        # Find matches using sophisticated logic
        matches = matcher.find_matches(component_data, debug=verbose)

        if matches:
            matched_count += 1
            if verbose:
                best_match = matches[0]
                print(f"Matched {item.ipn}: {best_match.debug_info}", file=sys.stderr)

            # If filter_matches=True, exclude matched items (show only new ones)
            if not filter_matches:
                filtered_items.append(item)
        else:
            # No match found
            if verbose:
                print(f"No match for {item.ipn} ({item.value})", file=sys.stderr)

            # If filter_matches=True, include unmatched items (new ones)
            # If filter_matches=False, include all items
            filtered_items.append(item)

    if verbose:
        total = len(inventory_items)
        filtered = len(filtered_items)
        action = "filtered out" if filter_matches else "included"
        print(
            f"\nInventory filtering: {matched_count}/{total} matched, {filtered} {action}",
            file=sys.stderr,
        )

    return filtered_items


def _output_inventory(
    inventory_items, field_names, output, force=False, verbose=False
) -> int:
    """Output inventory data in the requested format.

    Human-first defaults (BREAKING CHANGE for UX consistency):
    - output is None => formatted table to stdout (human exploration)
    - output == "console" => formatted table to stdout (explicit)
    - output == "-" => CSV to stdout (machine readable)
    - otherwise => treat as file path with safety checks
    """
    if output is None or output == "console":
        _print_console_table(inventory_items, field_names)
    elif output == "-":
        _print_csv(inventory_items, field_names)
    else:
        output_path = Path(output)

        # File existence and backup handling
        if output_path.exists():
            if not force:
                print(
                    f"Error: Output file '{output_path}' already exists. Use --force to overwrite.",
                    file=sys.stderr,
                )
                return 1

            # Create timestamped backup
            backup_path = _create_backup(output_path, verbose)
            if backup_path and verbose:
                print(f"Created backup: {backup_path}", file=sys.stderr)

        _write_csv(inventory_items, field_names, output_path)
        print(
            f"Generated inventory with {len(inventory_items)} items written to {output_path}"
        )

    return 0


def _create_backup(file_path: Path, verbose: bool = False) -> Path:
    """Create a timestamped backup of an existing file.

    Args:
        file_path: Path to file to backup
        verbose: Enable verbose output

    Returns:
        Path to created backup file, or None if backup failed
    """
    if not file_path.exists():
        return None

    # Generate timestamped backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = file_path.with_name(
        f"{file_path.stem}.backup.{timestamp}{file_path.suffix}"
    )

    try:
        shutil.copy2(file_path, backup_path)
        return backup_path
    except Exception as e:
        if verbose:
            print(f"Warning: Failed to create backup: {e}", file=sys.stderr)
        return None


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
