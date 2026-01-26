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

    # Component filtering options
    add_component_filter_arguments(parser)

    # Field selection (key feature for fabricator customization)
    parser.add_argument(
        "-f",
        "--fields",
        help="Comma-separated field list or preset (+minimal, +standard, +jlc, etc.)",
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

        # Handle --list-fields before processing
        if args.list_fields:
            _list_available_fields(fabricator)
            return 0

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
            bom_data = matcher.enhance_bom_with_inventory(bom_data, inventory_file)

        # Handle output
        return _output_bom(bom_data, args.output, selected_fields, fabricator)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _list_available_fields(fabricator: str) -> None:
    """List all available fields and presets for the given fabricator."""
    print("\nAvailable fields:")
    print("=" * 40)

    # Get standard BOM fields
    standard_fields = [
        "reference",
        "quantity",
        "value",
        "description",
        "footprint",
        "manufacturer",
        "mfgpn",
        "fabricator_part_number",
        "smd",
        "lcsc",
    ]

    for field in sorted(standard_fields):
        print(f"  {field}")

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
) -> int:
    """Output BOM data in the requested format with field customization.

    Args:
        bom_data: BOM data to output
        output: Output destination (None/"console" for table, "-" for CSV, path for file)
        selected_fields: List of fields to include in output
        fabricator: Fabricator ID for column mapping

    Returns:
        Exit code (0 for success)
    """
    # Apply fabricator-specific column mapping to get headers
    headers = apply_fabricator_column_mapping(fabricator, "bom", selected_fields)

    if output is None or output == "console":
        _print_console_table(bom_data, selected_fields, headers)
    elif output == "-":
        _print_csv(bom_data, selected_fields, headers)
    else:
        output_path = Path(output)
        _write_csv(bom_data, output_path, selected_fields, headers)
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

    # Dynamic table formatting based on selected fields
    col_widths = [max(15, len(header)) for header in headers]
    header_line = "  ".join(
        f"{headers[i]:<{col_widths[i]}}" for i in range(len(headers))
    )
    print(header_line)
    print("-" * len(header_line))

    for entry in bom_data.entries:
        values = []
        for field in selected_fields:
            value = _get_field_value(entry, field)
            # Truncate long values to fit column width
            col_width = col_widths[len(values)]
            if len(value) > col_width:
                value = value[: col_width - 3] + "..."
            values.append(value)

        row = "  ".join(f"{values[i]:<{col_widths[i]}}" for i in range(len(values)))
        print(row)

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
    writer = csv.writer(sys.stdout)

    # Write dynamic headers
    writer.writerow(headers)

    # Write data rows
    for entry in bom_data.entries:
        row = []
        for field in selected_fields:
            value = _get_field_value(entry, field)
            row.append(value)

        writer.writerow(row)


def _write_csv(
    bom_data: BOMData, output_path: Path, selected_fields: list[str], headers: list[str]
) -> None:
    """Write BOM as CSV to file with dynamic fields."""
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        # Use the same logic as stdout
        old_stdout = sys.stdout
        sys.stdout = csvfile
        _print_csv(bom_data, selected_fields, headers)
        sys.stdout = old_stdout


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
        "package": lambda e: e.attributes.get("package", ""),
    }

    if field in field_mapping:
        return field_mapping[field](entry)

    # Fall back to attribute lookup for unknown fields
    return entry.attributes.get(field, "")
    # Fall back to attribute lookup for unknown fields
    return entry.attributes.get(field, "")
