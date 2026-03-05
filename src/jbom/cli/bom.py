"""BOM command - thin CLI wrapper over BOM workflows."""

import argparse
import csv
import sys
from pathlib import Path
from typing import Optional

from jbom.cli.output import (
    OutputDestination,
    OutputKind,
    OutputRefusedError,
    add_force_argument,
    open_output_text_file,
    resolve_output_destination,
)
from jbom.services.schematic_reader import SchematicReader
from jbom.services.bom_generator import BOMGenerator, BOMData
from jbom.services.inventory_matcher import InventoryMatcher
from jbom.services.project_file_resolver import ProjectFileResolver
from jbom.common.options import GeneratorOptions
from jbom.config.fabricators import (
    get_available_fabricators,
    get_fabricator_presets,
    apply_fabricator_column_mapping,
)
from jbom.common.field_parser import (
    parse_fields_argument,
    check_fabricator_field_completeness,
)
from jbom.common.fields import get_available_presets
from jbom.common.component_filters import (
    add_component_filter_arguments,
    create_filter_config,
)
from jbom.common.component_utils import derive_package_from_footprint
from jbom.cli.formatting import Column, print_table, get_terminal_width


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
        help='Output destination: omit for default file output, use "console" for table, "-" for CSV to stdout, or a file path',
    )
    add_force_argument(parser)

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

    # Component filtering options
    add_component_filter_arguments(parser)

    # Field selection (key feature for fabricator customization)
    parser.add_argument(
        "-f",
        "--fields",
        help=(
            "Select specific fields for BOM output. Comma-separated list or +preset "
            "(+minimal, +standard, +jlc, etc.). Any field name is accepted; unknown "
            "fields produce blank cells. Use --list-fields to see known fields and presets."
        ),
    )

    parser.add_argument(
        "--list-fields",
        action="store_true",
        help="List available fields and presets, then exit",
    )

    # Options
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    parser.set_defaults(handler=handle_bom)


def handle_bom(args: argparse.Namespace) -> int:
    """Handle BOM command with project-centric input resolution."""
    try:
        # Determine effective fabricator early (needed for --list-fields)
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

        # Handle --list-fields - best-effort: try to load runtime data for richer output
        if args.list_fields:
            list_components: list = []
            list_inv_columns: list[str] = []

            # Try to load project components if a specific input was given
            if args.input and args.input != ".":
                try:
                    list_resolver = ProjectFileResolver(
                        prefer_pcb=False, target_file_type="schematic"
                    )
                    list_resolved = list_resolver.resolve_input(args.input)
                    list_reader = SchematicReader()
                    for sch_f in list_resolved.get_hierarchical_files():
                        list_components.extend(list_reader.load_components(sch_f))
                except Exception:
                    pass  # Fall back to statically-known fields

            # Try to load inventory columns if --inventory was given
            if args.inventory_files:
                from jbom.services.inventory_reader import InventoryReader as _InvReader

                for inv_str in args.inventory_files:
                    inv_p = Path(inv_str)
                    if inv_p.exists():
                        try:
                            _, cols = _InvReader(inv_p).load()
                            list_inv_columns.extend(cols)
                        except Exception:
                            pass

            _list_available_fields(
                fabricator,
                components=list_components or None,
                inventory_column_names=list_inv_columns or None,
            )
            return 0

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

        if not resolved_input.project_context:
            raise ValueError("No project context available")

        project_context = resolved_input.project_context
        project_name = project_context.project_base_name
        default_output_path = (
            project_context.project_directory / f"{project_name}.bom.csv"
        )

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

        # Parse field selection
        fabricator_presets = get_fabricator_presets(fabricator)
        available_fields = _get_available_bom_fields(components)

        try:
            selected_fields = parse_fields_argument(
                args.fields, available_fields, fabricator, fabricator_presets
            )
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        if args.verbose:
            print(f"Selected fields: {', '.join(selected_fields)}", file=sys.stderr)

        # Check for missing fabricator-specific fields and warn if appropriate
        if args.fields:  # Only warn if user explicitly provided fields
            warning = check_fabricator_field_completeness(
                selected_fields, fabricator, fabricator_presets
            )
            if warning:
                print(warning, file=sys.stderr)

        # Generate basic BOM with common filtering logic
        filters = create_filter_config(args)
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
            bom_data = matcher.enhance_bom_with_inventory(
                bom_data,
                inventory_file,
                fabricator_id=fabricator,
                project_name=project_name,
            )

        # Handle output
        return _output_bom(
            bom_data,
            args.output,
            selected_fields,
            fabricator,
            default_output_path=default_output_path,
            force=args.force,
        )

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _list_available_fields(
    fabricator: str,
    components: list | None = None,
    inventory_column_names: list[str] | None = None,
) -> None:
    """List known BOM fields and presets for the given fabricator.

    Fields are dynamically derived from the union of component-schema fields and any
    loaded inventory columns. Any field name is accepted at runtime; unknown fields
    produce blank cells.

    Args:
        fabricator: Current fabricator ID (for fabricator-specific presets)
        components: Optional loaded components for runtime field discovery
        inventory_column_names: Optional list of inventory CSV column headers
    """
    from jbom.common.fields import field_to_header, normalize_field_name

    # Build known fields dynamically from project + inventory union
    known_fields = _get_available_bom_fields(components or [])

    # Merge in inventory-discovered columns (with i: prefix for unambiguous access)
    if inventory_column_names:
        for col in inventory_column_names:
            normalized_col = normalize_field_name(col)
            i_key = f"i:{normalized_col}"
            if i_key not in known_fields:
                known_fields[i_key] = f"Inventory: {col}"

    print(
        "\nKnown fields (any field name is accepted \u2014 unknown fields produce blank cells):"
    )
    print("=" * 60)
    for field_name in sorted(known_fields.keys()):
        desc = known_fields[field_name]
        header = field_to_header(field_name)
        print(f"  {field_name:<30}  ({header}):  {desc}")

    if not components and not inventory_column_names:
        print(
            "\n  Tip: Run with a project path or --inventory to see runtime-discovered fields."
        )
        print("  Example: jbom bom --list-fields [input] [--inventory file.csv]")

    print("\nAvailable presets:")
    print("=" * 40)

    # Get global presets
    global_presets = get_available_presets()
    for name, desc in global_presets.items():
        print(f"  +{name}: {desc}")

    # Get fabricator-specific presets
    fabricator_presets = get_fabricator_presets(fabricator)
    if fabricator_presets:
        print(f"\nFabricator-specific presets ({fabricator}):")
        print("=" * 40)
        for name, preset_def in fabricator_presets.items():
            desc = preset_def.get("description", "Fabricator-specific preset")
            print(f"  +{name}: {desc}")


def _get_available_bom_fields(components) -> dict[str, str]:
    """Get available fields based on component data and inventory enhancement."""
    # Standard BOM fields available from components
    fields = {
        "reference": "Component reference (R1, C2, etc.)",
        "quantity": "Number of components",
        "value": "Component value",
        "description": "Component description",
        "footprint": "Component footprint",
        "manufacturer": "Component manufacturer",
        "mfgpn": "Manufacturer part number",
        "fabricator_part_number": "Fabricator-specific part number",
        "smd": "Surface mount indicator",
        "lcsc": "LCSC part number",
        # Add inventory fields with I: prefix
        "i:voltage": "Inventory: Component voltage",
        "i:tolerance": "Inventory: Component tolerance",
        "i:package": "Inventory: Component package",
    }

    # Add any additional fields found in component properties
    if components:
        for comp in components:
            # Components have .properties, not .attributes
            if hasattr(comp, "properties"):
                for attr_key in comp.properties.keys():
                    normalized_key = attr_key.lower().replace(" ", "_")
                    if normalized_key not in fields:
                        fields[normalized_key] = f"Component property: {attr_key}"

    return fields


def _output_bom(
    bom_data: BOMData,
    output: Optional[str],
    selected_fields: list[str],
    fabricator: str,
    *,
    default_output_path: Path,
    force: bool,
) -> int:
    """Output BOM data in the requested format with field customization."""

    headers = apply_fabricator_column_mapping(fabricator, "bom", selected_fields)

    dest = resolve_output_destination(
        output,
        default_destination=OutputDestination(
            OutputKind.FILE, path=default_output_path
        ),
    )

    if dest.kind == OutputKind.CONSOLE:
        _print_console_table(bom_data, selected_fields, headers)
        return 0

    if dest.kind == OutputKind.STDOUT:
        _print_csv(bom_data, selected_fields, headers)
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
            _write_csv_handle(bom_data, f, selected_fields, headers)
    except OutputRefusedError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"BOM written to {output_path}")
    return 0


def _print_console_table(
    bom_data: BOMData, selected_fields: list[str], headers: list[str]
) -> None:
    """Print BOM as formatted console table with dynamic fields."""
    print(f"\n{bom_data.project_name} - Bill of Materials")
    print("=" * 60)

    if not bom_data.entries:
        print("No components found.")
        return

    rows = [
        {h: _get_field_value(entry, f) for f, h in zip(selected_fields, headers)}
        for entry in bom_data.entries
    ]
    columns = [
        Column(header=h, key=h, preferred_width=max(15, len(h)), wrap=True)
        for h in headers
    ]
    print_table(rows, columns, terminal_width=get_terminal_width())

    print(
        f"\nTotal: {bom_data.total_components} components, {bom_data.total_line_items} unique items"
    )

    # Show inventory enhancement info if available
    if "matched_entries" in bom_data.metadata:
        matched = bom_data.metadata["matched_entries"]
        print(
            f"Inventory enhanced: {matched}/{bom_data.total_line_items} items matched"
        )


def _print_csv(
    bom_data: BOMData, selected_fields: list[str], headers: list[str]
) -> None:
    """Print BOM as CSV to stdout with dynamic fields."""

    _write_csv_handle(bom_data, sys.stdout, selected_fields, headers)


def _write_csv_handle(
    bom_data: BOMData,
    f,
    selected_fields: list[str],
    headers: list[str],
) -> None:
    """Write BOM as CSV to a file-like object."""

    writer = csv.writer(f)
    writer.writerow(headers)
    for entry in bom_data.entries:
        row = [_get_field_value(entry, field) for field in selected_fields]
        writer.writerow(row)


def _get_field_value(entry, field: str) -> str:
    """Extract field value from BOM entry.

    Args:
        entry: BOM entry object
        field: Field name to extract

    Returns:
        String value for the field
    """
    # Handle inventory fields with I: prefix
    if field.startswith("i:"):
        inventory_field = field[2:]  # Remove "i:" prefix
        return entry.attributes.get(inventory_field, "")

    # Handle standard BOM fields
    field_mapping = {
        "reference": lambda e: e.references_string,
        "quantity": lambda e: str(e.quantity),
        "value": lambda e: e.value,
        "description": lambda e: e.attributes.get("description", ""),
        "footprint": lambda e: e.footprint,
        "manufacturer": lambda e: e.attributes.get("manufacturer", ""),
        "mfgpn": lambda e: e.attributes.get("manufacturer_part", ""),
        "fabricator_part_number": lambda e: e.attributes.get(
            "fabricator_part_number", ""
        ),
        "smd": lambda e: "Yes" if e.attributes.get("smd", False) else "No",
        "lcsc": lambda e: e.attributes.get("lcsc", "") or e.attributes.get("LCSC", ""),
        "package": lambda e: e.attributes.get("package", "")
        or derive_package_from_footprint(e.footprint),
    }

    if field in field_mapping:
        return field_mapping[field](entry)

    # Fall back to attribute lookup for unknown fields
    return entry.attributes.get(field, "")
