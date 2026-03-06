"""Inventory command - manage component inventory."""

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import TextIO

import shutil

from jbom.cli.output import (
    OutputDestination,
    OutputKind,
    OutputRefusedError,
    add_force_argument,
    open_output_text_file,
    resolve_output_destination,
)
from jbom.common.types import Component, InventoryItem
from jbom.common.options import GeneratorOptions
from jbom.cli.formatting import print_inventory_table
from jbom.services.inventory_reader import InventoryReader
from jbom.common.component_filters import apply_component_filters
from jbom.services.project_file_resolver import ProjectFileResolver
from jbom.services.project_inventory import ProjectInventoryGenerator
from jbom.services.schematic_reader import SchematicReader
from jbom.services.sophisticated_inventory_matcher import (
    MatchingOptions,
    SophisticatedInventoryMatcher,
)

# Fields always present in no-aggregate output — included even when all values are empty
# so the designer can fill them in or use "~" for heuristic defaults.
_NO_AGGREGATE_ALWAYS_FIELDS: list[str] = [
    # Identity — required for jbom annotate component routing
    "Project",
    "ProjectName",
    "UUID",
    "SourceFile",
    "Reference",
    "Category",
    "IPN",
    # Electro-mechanical attributes
    "Value",
    "Description",
    "Inductance",
    "Resistance",
    "Capacitance",
    "Package",
    "Color",
    "Tolerance",
    "W",
    "A",
    "V",
    "Temperature Coefficient",
    "Voltage",
    "Wavelength",
    "mcd",
    "Symbol",
    "Footprint",
]

# Fields included only when at least one component carries a non-empty value.
_NO_AGGREGATE_CONDITIONAL_FIELDS: list[str] = [
    "SMD",
    "Type",
    "Form",
    "Pins",
    "Pitch",
    "Angle",
    "Manufacturer",
    "MFGPN",
    "LCSC",
    "Datasheet",
    "Keywords",
    "Height",
    "Manufacturer_Name",
    "Manufacturer_Part_Number",
    "Mouser Part Number",
    "Mouser Price/Stock",
    "Sim.Device",
    "Sim.Pins",
    "Supplier",
    "Name",
]


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
        help=(
            "Output destination: omit for default file output (part-inventory.csv), "
            "use 'console' for table, '-' for stdout, or a file path"
        ),
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
    parser.add_argument(
        "--no-aggregate",
        action="store_true",
        help="Emit one inventory row per component instance with category sub-header rows",
    )

    # Safety options
    add_force_argument(parser)

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

    # Apply standard BOM-equivalent filtering: exclude virtual symbols, DNP, and non-BOM components.
    # Virtual symbols (power flags, GND nets, etc.) are never stocked or purchased.
    # No CLI flags are exposed for inventory — these defaults are correct and permanent.
    components = apply_component_filters(
        components,
        {
            "exclude_dnp": True,
            "include_only_bom": True,
            "include_virtual_symbols": False,
        },
    )

    if not components:
        print(
            "Error: No real components found after filtering virtual symbols. "
            "Cannot create inventory from empty schematic.",
            file=sys.stderr,
        )
        return 1

    # Apply inventory filtering (component-level) if requested.
    if args.inventory_files or args.filter_matches:
        components = _filter_components_by_existing_inventory(
            components,
            inventory_files=args.inventory_files,
            filter_matches=args.filter_matches,
            verbose=args.verbose,
        )

    project_directory = (
        resolved_input.project_context.project_directory
        if resolved_input.project_context
        else schematic_file.parent
    )

    # Generate inventory
    generator = ProjectInventoryGenerator(components)

    project_name = (
        resolved_input.project_context.project_base_name
        if resolved_input.project_context
        else project_directory.name
    )

    if args.no_aggregate:
        rows, field_names = _generate_no_aggregate_inventory_rows(
            components,
            project_directory=project_directory,
            project_name=project_name,
        )
        return _output_inventory_rows(
            rows, field_names, args.output, args.force, args.verbose
        )

    inventory_items, field_names = generator.load()

    # Handle output using same pattern as BOM command
    return _output_inventory(
        inventory_items, field_names, args.output, args.force, args.verbose
    )


def _generate_no_aggregate_inventory_rows(
    components: list[Component],
    project_directory: Path,
    project_name: str = "",
) -> tuple[list[dict[str, str]], list[str]]:
    """Generate no-aggregate inventory rows grouped by category with sub-headers.

    Schema always includes identity and electro-mechanical attribute columns
    (``_NO_AGGREGATE_ALWAYS_FIELDS``).  Supply-chain and simulation columns are
    included only when at least one component carries a non-empty value for that
    field (``_NO_AGGREGATE_CONDITIONAL_FIELDS``).

    Identity semantics:
    - ``SourceFile`` (absolute path) + ``UUID`` is the canonical annotation routing key.
    - ``ProjectName`` and ``Project`` are cosmetic context only, never used for routing.
    - ``Reference`` is the human-readable designator (e.g. "R1", "C3").
    """

    generator = ProjectInventoryGenerator(components)
    inventory_items, base_field_names = generator.load_no_aggregate()

    project_value = str(project_directory.resolve())
    project_name_value = project_name or project_directory.name

    uuid_to_source: dict[str, str] = {}
    uuid_to_ref: dict[str, str] = {}
    for comp in components:
        if comp.uuid:
            uuid_to_source[comp.uuid] = (
                str(comp.source_file) if comp.source_file else ""
            )
            uuid_to_ref[comp.uuid] = comp.reference

    # Build raw rows using all candidate fields so conditional-field detection
    # can inspect actual values before the final field list is determined.
    candidate_fields: list[str] = list(
        dict.fromkeys(
            _NO_AGGREGATE_ALWAYS_FIELDS
            + _NO_AGGREGATE_CONDITIONAL_FIELDS
            + list(base_field_names)
        )
    )

    raw_rows: list[dict[str, str]] = []
    for item in inventory_items:
        row = _inventory_item_to_row(item, candidate_fields)
        row["Project"] = project_value
        row["ProjectName"] = project_name_value
        row["UUID"] = item.uuid
        row["SourceFile"] = uuid_to_source.get(item.uuid, "")
        row["Reference"] = uuid_to_ref.get(item.uuid, "")
        row["Category"] = item.category
        row["IPN"] = item.ipn
        raw_rows.append(row)

    # Determine final field order: always fields + conditional fields that have data.
    field_names = _build_no_aggregate_field_order(base_field_names, raw_rows)

    sorted_rows = sorted(
        raw_rows, key=lambda r: (r.get("Category", ""), r.get("UUID", ""))
    )

    grouped_rows: list[dict[str, str]] = []
    current_category = ""
    for row in sorted_rows:
        category = row.get("Category", "")
        if category != current_category:
            grouped_rows.append(_build_no_aggregate_subheader_row(field_names))
            current_category = category
        grouped_rows.append({fn: row.get(fn, "") for fn in field_names})

    return grouped_rows, field_names


def _build_no_aggregate_field_order(
    base_field_names: list[str],
    data_rows: list[dict[str, str]],
) -> list[str]:
    """Return deterministic field ordering for no-aggregate inventory output.

    Always-include fields appear first (even when every value is empty).
    Conditional fields follow only when at least one data row carries a
    non-empty value.  Any remaining fields from *base_field_names* that have
    data but are not in either list are appended at the end.
    """

    ordered: list[str] = list(_NO_AGGREGATE_ALWAYS_FIELDS)
    already: set[str] = set(ordered)

    def _has_data(field: str) -> bool:
        return any(row.get(field, "") for row in data_rows)

    for field in _NO_AGGREGATE_CONDITIONAL_FIELDS:
        if field not in already and _has_data(field):
            ordered.append(field)
            already.add(field)

    # Append any extra fields from the KiCad base data not already covered.
    for field in base_field_names:
        if field not in already and _has_data(field):
            ordered.append(field)
            already.add(field)

    return ordered


def _build_no_aggregate_subheader_row(field_names: list[str]) -> dict[str, str]:
    """Build minimal deterministic sub-header marker row for no-aggregate output.

    Identity columns (Project … Reference) are marked with their field name as
    a sentinel.  IPN is marked optional.  All other columns are left empty so
    the designer can fill in component-specific values.
    """

    row = {field_name: "" for field_name in field_names}
    row["Project"] = "Project"
    row["ProjectName"] = "ProjectName"
    row["UUID"] = "UUID"
    row["SourceFile"] = "SourceFile"
    row["Reference"] = "Reference"
    row["Category"] = "Category"
    row["IPN"] = "(Optional)\nIPN"
    row["Value"] = "Value"
    row["Package"] = "Package"
    return row


def _filter_components_by_existing_inventory(
    components: list[Component],
    *,
    inventory_files: list[Path] | None,
    filter_matches: bool,
    verbose: bool,
) -> list[Component]:
    """Filter project components based on whether they match an existing inventory.

    This is used by `jbom inventory` to show only "new" components not already
    represented in an inventory file.

    Args:
        components: Components loaded from schematic(s).
        inventory_files: Inventory CSV file paths.
        filter_matches: If True, exclude components that match (show only new).
        verbose: Emit diagnostic match info to stderr.

    Returns:
        Filtered component list.
    """
    inventory_files = inventory_files or []
    if not inventory_files:
        if filter_matches:
            print(
                "Error: --filter-matches requires --inventory file(s)",
                file=sys.stderr,
            )
            raise SystemExit(1)
        return components

    # Load and merge inventory files (first occurrence of each IPN wins).
    merged_inventory: list[InventoryItem] = []
    seen_ipns: set[str] = set()

    if verbose:
        print(
            f"Loading {len(inventory_files)} inventory file(s):",
            file=sys.stderr,
        )

    missing_file_detected = False
    total_files_loaded = 0

    for i, inventory_file in enumerate(inventory_files):
        if not inventory_file.exists():
            missing_file_detected = True
            print(
                f"Error: Inventory file not found: {inventory_file}",
                file=sys.stderr,
            )
            continue

        try:
            reader = InventoryReader(inventory_file)
            file_inventory, _ = reader.load()

            added_count = 0
            for item in file_inventory:
                if item.ipn not in seen_ipns:
                    merged_inventory.append(item)
                    seen_ipns.add(item.ipn)
                    added_count += 1

            total_files_loaded += 1
            if verbose:
                file_desc = f"file {i + 1}"
                print(
                    f"  {file_desc}: {inventory_file} ({added_count}/{len(file_inventory)} items added)",
                    file=sys.stderr,
                )

        except Exception as e:
            print(f"Error loading {inventory_file}: {e}", file=sys.stderr)

    if missing_file_detected:
        raise SystemExit(1)

    if not merged_inventory:
        print("Error: No inventory items loaded from any file", file=sys.stderr)
        raise SystemExit(1)

    if verbose:
        print(
            f"Merged inventory: {len(merged_inventory)} total items from {total_files_loaded} file(s)",
            file=sys.stderr,
        )

    matcher = SophisticatedInventoryMatcher(MatchingOptions(include_debug_info=verbose))

    filtered_components: list[Component] = []
    matched_count = 0

    for comp in components:
        matches = matcher.find_matches(comp, merged_inventory)

        if matches:
            matched_count += 1
            if verbose:
                print(
                    f"Matched {comp.reference}: {matches[0].debug_info}",
                    file=sys.stderr,
                )

            if not filter_matches:
                filtered_components.append(comp)
        else:
            if verbose:
                print(
                    f"No match for {comp.reference} ({comp.lib_id} {comp.value} {comp.footprint})",
                    file=sys.stderr,
                )
            filtered_components.append(comp)

    if verbose:
        total = len(components)
        filtered = len(filtered_components)
        action = "kept" if filter_matches else "included"
        print(
            f"\nInventory filtering: {matched_count}/{total} matched, {filtered} {action}",
            file=sys.stderr,
        )

    return filtered_components


def _output_inventory(
    inventory_items, field_names, output, force: bool = False, verbose: bool = False
) -> int:
    """Output inventory data in the requested format.

    Defaults:
    - output omitted => write to part-inventory.csv in the current working directory
    - output == "console" => formatted table to stdout
    - output == "-" => CSV to stdout
    - otherwise => treat as file path with safety checks
    """
    default_path = Path("part-inventory.csv")

    dest = resolve_output_destination(
        output,
        default_destination=OutputDestination(OutputKind.FILE, path=default_path),
    )

    if dest.kind == OutputKind.CONSOLE:
        _print_console_table(inventory_items, field_names)
        return 0

    if dest.kind == OutputKind.STDOUT:
        _print_csv(inventory_items, field_names, out=sys.stdout)
        return 0

    if not dest.path:
        raise ValueError("Internal error: file output selected but no path provided")

    output_path = dest.path
    refused = (
        f"Error: Output file '{output_path}' already exists. Use --force to overwrite."
    )

    def _backup(p: Path) -> Path | None:
        backup_path = _create_backup(p, verbose)
        if backup_path and verbose:
            print(f"Created backup: {backup_path}", file=sys.stderr)
        return backup_path

    try:
        with open_output_text_file(
            output_path,
            force=force,
            refused_message=refused,
            make_backup=_backup,
        ) as f:
            _write_csv(inventory_items, field_names, out=f)
    except OutputRefusedError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(
        f"Generated inventory with {len(inventory_items)} items written to {output_path}"
    )
    return 0


def _output_inventory_rows(
    rows: list[dict[str, str]],
    field_names: list[str],
    output,
    force: bool = False,
    verbose: bool = False,
) -> int:
    """Output pre-built inventory row dictionaries in the requested format."""
    default_path = Path("part-inventory.csv")

    dest = resolve_output_destination(
        output,
        default_destination=OutputDestination(OutputKind.FILE, path=default_path),
    )

    if dest.kind == OutputKind.CONSOLE:
        print_inventory_table(rows, field_names)
        print(f"\nGenerated inventory with {_count_data_rows(rows)} items")
        return 0

    if dest.kind == OutputKind.STDOUT:
        _write_csv_rows(rows, field_names, out=sys.stdout)
        return 0

    if not dest.path:
        raise ValueError("Internal error: file output selected but no path provided")

    output_path = dest.path
    refused = (
        f"Error: Output file '{output_path}' already exists. Use --force to overwrite."
    )

    def _backup(path: Path) -> Path | None:
        backup_path = _create_backup(path, verbose)
        if backup_path and verbose:
            print(f"Created backup: {backup_path}", file=sys.stderr)
        return backup_path

    try:
        with open_output_text_file(
            output_path,
            force=force,
            refused_message=refused,
            make_backup=_backup,
        ) as handle:
            _write_csv_rows(rows, field_names, out=handle)
    except OutputRefusedError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(
        f"Generated inventory with {_count_data_rows(rows)} items written to {output_path}"
    )
    return 0


def _count_data_rows(rows: list[dict[str, str]]) -> int:
    """Count inventory data rows excluding no-aggregate sentinel sub-headers."""

    return sum(1 for row in rows if row.get("Project", "") != "Project")


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


def _print_csv(inventory_items, field_names, *, out: TextIO) -> None:
    """Print inventory as CSV to a file-like object."""
    rows = [_inventory_item_to_row(item, field_names) for item in inventory_items]
    _write_csv_rows(rows, field_names, out=out)


def _write_csv(inventory_items, field_names, *, out: TextIO) -> None:
    """Write inventory as CSV to a file-like object."""
    rows = [_inventory_item_to_row(item, field_names) for item in inventory_items]
    _write_csv_rows(rows, field_names, out=out)


def _inventory_item_to_row(
    item: InventoryItem, field_names: list[str]
) -> dict[str, str]:
    """Convert an InventoryItem to a CSV row dictionary."""

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

    for field_name in field_names:
        if (
            field_name not in row
            and hasattr(item, "raw_data")
            and field_name in item.raw_data
        ):
            row[field_name] = item.raw_data[field_name]

    for field_name in field_names:
        row.setdefault(field_name, "")

    return row


def _write_csv_rows(
    rows: list[dict[str, str]], field_names: list[str], *, out: TextIO
) -> None:
    """Write row dictionaries as CSV using the provided field order."""

    writer = csv.DictWriter(out, fieldnames=field_names)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
