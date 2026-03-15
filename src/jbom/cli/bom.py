"""BOM command - thin CLI wrapper over BOM workflows."""

import argparse
import csv
import sys
from pathlib import Path
from typing import Any, Optional

from jbom.cli.output import (
    OutputDestination,
    OutputKind,
    OutputRefusedError,
    add_force_argument,
    open_output_text_file,
    resolve_output_destination,
)
from jbom.services.schematic_reader import SchematicReader
from jbom.services.bom_generator import BOMGenerator, BOMData, BOMEntry
from jbom.services.fabricator_projection_service import (
    FabricatorProjectionService,
)
from jbom.services.inventory_overlay_service import InventoryOverlayService
from jbom.services.pcb_reader import DefaultKiCadReaderService
from jbom.services.component_merge_service import (
    ComponentMergeResult,
    ComponentMergeService,
    MergedReferenceRecord,
)
from jbom.services.project_component_collector import ProjectComponentCollector
from jbom.services.project_file_resolver import ProjectFileResolver
from jbom.common.options import GeneratorOptions
from jbom.config.fabricators import (
    FabricatorConfig,
    get_available_fabricators,
    get_fabricator_presets,
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
from jbom.common.package_matching import PackageType
from jbom.cli.formatting import Column, print_table, get_terminal_width


def _run_component_merge(
    *,
    components: list,
    schematic_files: list[Path],
    pcb_file: Optional[Path],
    verbose: bool,
) -> ComponentMergeResult | None:
    """Best-effort collector/merge execution for canonical namespace enrichment."""

    try:
        pcb_components = []
        if pcb_file is not None and pcb_file.exists():
            board = DefaultKiCadReaderService().read_pcb_file(pcb_file)
            pcb_components = list(board.footprints)

        collector = ProjectComponentCollector()
        project_graph = collector.collect(
            schematic_components=components,
            pcb_components=pcb_components,
            schematic_files=schematic_files,
            pcb_file=pcb_file,
        )
        merge_service = ComponentMergeService()
        merge_result = merge_service.merge(project_graph)

        if verbose:
            print(
                "Merge model active: "
                f"{project_graph.reference_count} references, "
                f"{len(merge_result.mismatches)} mismatch record(s)",
                file=sys.stderr,
            )
        return merge_result
    except Exception as exc:
        if verbose:
            print(
                f"Warning: merge model execution skipped due to error: {exc}",
                file=sys.stderr,
            )
        return None


def _resolve_uniform_merge_field_value(
    reference_records: list[MergedReferenceRecord],
    *,
    namespace_field: str,
    field_key: str,
) -> str:
    """Resolve a merge namespace field only when grouped references agree."""

    resolved_value = ""
    for record in reference_records:
        namespace_values = getattr(record, namespace_field)
        candidate_value = str(namespace_values.get(field_key, "")).strip()
        if not candidate_value:
            continue
        if not resolved_value:
            resolved_value = candidate_value
            continue
        if candidate_value != resolved_value:
            return ""
    return resolved_value


def _resolve_entry_merge_namespace_values(
    reference_records: list[MergedReferenceRecord],
) -> dict[str, str]:
    """Resolve stable merge namespace fields for one aggregated BOM entry."""

    resolved_fields: dict[str, str] = {}
    for namespace_field in ("source_fields", "canonical_fields", "annotated_fields"):
        field_keys = sorted(
            {
                field_key
                for record in reference_records
                for field_key in getattr(record, namespace_field).keys()
            }
        )
        for field_key in field_keys:
            resolved_value = _resolve_uniform_merge_field_value(
                reference_records,
                namespace_field=namespace_field,
                field_key=field_key,
            )
            if resolved_value:
                resolved_fields[field_key] = resolved_value
    return resolved_fields


def _enrich_bom_with_merge_namespaces(
    bom_data: BOMData,
    merge_result: ComponentMergeResult | None,
) -> BOMData:
    """Attach stable merge-model namespaces (`s:/p:/c:/a:`) onto BOM entries."""

    if merge_result is None or not merge_result.records:
        return bom_data

    updated_entries: list[BOMEntry] = []
    any_entry_updated = False
    for entry in bom_data.entries:
        entry_merge_records = [
            merge_result.records[reference]
            for reference in entry.references
            if reference in merge_result.records
        ]
        if not entry_merge_records:
            updated_entries.append(entry)
            continue

        merge_namespace_fields = _resolve_entry_merge_namespace_values(
            entry_merge_records
        )
        if not merge_namespace_fields:
            updated_entries.append(entry)
            continue

        attributes = dict(entry.attributes)
        entry_updated = False
        for field_key, field_value in merge_namespace_fields.items():
            if attributes.get(field_key) == field_value:
                continue
            attributes[field_key] = field_value
            entry_updated = True

        if not entry_updated:
            updated_entries.append(entry)
            continue

        any_entry_updated = True
        updated_entries.append(
            BOMEntry(
                references=entry.references,
                value=entry.value,
                footprint=entry.footprint,
                quantity=entry.quantity,
                lib_id=entry.lib_id,
                attributes=attributes,
            )
        )

    metadata = dict(bom_data.metadata)
    metadata.update(
        {
            "merge_model_enabled": True,
            "merge_model_reference_count": merge_result.reference_count,
            "merge_model_mismatch_count": len(merge_result.mismatches),
            "merge_precedence_profile": merge_result.metadata.get(
                "precedence_profile", ""
            ),
        }
    )
    return BOMData(
        project_name=bom_data.project_name,
        entries=updated_entries if any_entry_updated else bom_data.entries,
        metadata=metadata,
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
            schematic_files = list(hierarchical_files)
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
            schematic_files = [schematic_file]
            components = reader.load_components(schematic_file)

        merge_result = _run_component_merge(
            components=components,
            schematic_files=schematic_files,
            pcb_file=project_context.pcb_file if project_context else None,
            verbose=args.verbose,
        )

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
        bom_data = _enrich_bom_with_merge_namespaces(bom_data, merge_result)

        inventory_file: Path | None = None
        if args.inventory_files:
            if args.verbose:
                print(
                    f"Enhancing BOM with {len(args.inventory_files)} inventory file(s)",
                    file=sys.stderr,
                )
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

        overlay_service = InventoryOverlayService()
        overlay_result = overlay_service.overlay_bom_data(
            bom_data,
            inventory_file=inventory_file,
            fabricator_id=fabricator,
            project_name=project_name,
        )
        bom_data = overlay_result.bom_data

        bom_data = _enrich_bom_smd_from_project_pcb(
            bom_data,
            project_context.pcb_file if project_context else None,
            verbose=args.verbose,
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


def _load_pcb_smd_lookup(
    pcb_file: Optional[Path], *, verbose: bool = False
) -> dict[str, bool]:
    """Return reference -> is_smd lookup from a KiCad PCB file."""

    if pcb_file is None or not pcb_file.exists():
        return {}

    try:
        board = DefaultKiCadReaderService().read_pcb_file(pcb_file)
    except Exception as exc:
        if verbose:
            print(
                f"Warning: Could not read PCB mount metadata from {pcb_file}: {exc}",
                file=sys.stderr,
            )
        return {}

    smd_by_reference: dict[str, bool] = {}
    for footprint in board.footprints:
        reference = (footprint.reference or "").strip()
        if not reference:
            continue

        mount_type = str(footprint.attributes.get("mount_type", "")).strip().lower()
        if mount_type == "smd":
            smd_by_reference[reference] = True
        elif mount_type in {"through_hole", "through-hole", "tht"}:
            smd_by_reference[reference] = False

    return smd_by_reference


def _entry_smd_from_reference_lookup(
    entry: BOMEntry, smd_by_reference: dict[str, bool]
) -> Optional[bool]:
    """Resolve an entry-level SMD boolean from per-reference PCB mount metadata."""

    known_values = [
        smd_by_reference[ref] for ref in entry.references if ref in smd_by_reference
    ]
    if not known_values:
        return None

    # Aggregated BOM groups should be homogeneous by footprint.
    return all(known_values)


def _enrich_bom_smd_from_project_pcb(
    bom_data: BOMData,
    pcb_file: Optional[Path],
    *,
    verbose: bool = False,
) -> BOMData:
    """Populate missing BOM `smd` attributes from PCB mount metadata."""

    smd_by_reference = _load_pcb_smd_lookup(pcb_file, verbose=verbose)
    if not smd_by_reference:
        return bom_data

    updated = False
    enriched_entries: list[BOMEntry] = []

    for entry in bom_data.entries:
        current_smd = str(entry.attributes.get("smd", "")).strip()
        if current_smd:
            enriched_entries.append(entry)
            continue

        resolved = _entry_smd_from_reference_lookup(entry, smd_by_reference)
        if resolved is None:
            enriched_entries.append(entry)
            continue

        attrs = dict(entry.attributes)
        attrs["smd"] = resolved
        enriched_entries.append(
            BOMEntry(
                references=entry.references,
                value=entry.value,
                footprint=entry.footprint,
                quantity=entry.quantity,
                lib_id=entry.lib_id,
                attributes=attrs,
            )
        )
        updated = True

    if not updated:
        return bom_data

    metadata = dict(bom_data.metadata)
    metadata["pcb_mount_metadata_used"] = True
    return BOMData(
        project_name=bom_data.project_name,
        entries=enriched_entries,
        metadata=metadata,
    )


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
    projection_service = FabricatorProjectionService()
    projection = projection_service.build_projection(
        fabricator_id=fabricator,
        output_type="bom",
        selected_fields=selected_fields,
    )
    headers = list(projection.headers)
    fabricator_config = projection.fabricator_config

    dest = resolve_output_destination(
        output,
        default_destination=OutputDestination(
            OutputKind.FILE, path=default_output_path
        ),
    )

    if dest.kind == OutputKind.CONSOLE:
        _print_console_table(
            bom_data,
            selected_fields,
            headers,
            fabricator_id=fabricator,
            fabricator_config=fabricator_config,
        )
        return 0

    if dest.kind == OutputKind.STDOUT:
        _print_csv(
            bom_data,
            selected_fields,
            headers,
            fabricator_id=fabricator,
            fabricator_config=fabricator_config,
        )
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
            _write_csv_handle(
                bom_data,
                f,
                selected_fields,
                headers,
                fabricator_id=fabricator,
                fabricator_config=fabricator_config,
            )
    except OutputRefusedError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"BOM written to {output_path}")
    return 0


def _print_console_table(
    bom_data: BOMData,
    selected_fields: list[str],
    headers: list[str],
    *,
    fabricator_id: str,
    fabricator_config: Optional[FabricatorConfig],
) -> None:
    """Print BOM as formatted console table with dynamic fields."""
    print(f"\n{bom_data.project_name} - Bill of Materials")
    print("=" * 60)

    if not bom_data.entries:
        print("No components found.")
        return

    rows = [
        {
            h: _get_field_value(
                entry,
                f,
                fabricator_id=fabricator_id,
                fabricator_config=fabricator_config,
            )
            for f, h in zip(selected_fields, headers)
        }
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
    bom_data: BOMData,
    selected_fields: list[str],
    headers: list[str],
    *,
    fabricator_id: str,
    fabricator_config: Optional[FabricatorConfig],
) -> None:
    """Print BOM as CSV to stdout with dynamic fields."""
    _write_csv_handle(
        bom_data,
        sys.stdout,
        selected_fields,
        headers,
        fabricator_id=fabricator_id,
        fabricator_config=fabricator_config,
    )


def _write_csv_handle(
    bom_data: BOMData,
    f,
    selected_fields: list[str],
    headers: list[str],
    *,
    fabricator_id: str,
    fabricator_config: Optional[FabricatorConfig],
) -> None:
    """Write BOM as CSV to a file-like object."""

    # QUOTE_ALL ensures values like "0603" are written as "\"0603\"" so
    # spreadsheet apps treat them as text and preserve leading zeros.
    writer = csv.writer(f, quoting=csv.QUOTE_ALL)
    writer.writerow(headers)
    for entry in bom_data.entries:
        row = [
            _get_field_value(
                entry,
                field,
                fabricator_id=fabricator_id,
                fabricator_config=fabricator_config,
            )
            for field in selected_fields
        ]
        writer.writerow(row)


def _resolve_fabricator_part_number(
    entry,
    *,
    fabricator_id: str,
    fabricator_config: Optional[FabricatorConfig],
) -> str:
    """Resolve fabricator part number using shared projection service behavior."""

    return FabricatorProjectionService.resolve_fabricator_part_number(
        entry.attributes,
        fabricator_id=fabricator_id,
        fabricator_config=fabricator_config,
    )


def _is_smd_token(value: str) -> bool:
    """Return True when a token contains known SMD package patterns."""

    token = (value or "").strip().lower()
    if not token:
        return False

    for pattern in sorted(PackageType.SMD_PACKAGES, key=len, reverse=True):
        if pattern in token:
            return True
    return False


def _resolve_smd_indicator(entry: BOMEntry) -> str:
    """Resolve BOM SMD value as `Yes`/`No` from explicit and inferred signals."""

    raw = entry.attributes.get("smd", "")
    if isinstance(raw, bool):
        return "Yes" if raw else "No"

    raw_text = str(raw).strip().lower()
    if raw_text in {"yes", "y", "true", "1", "smd"}:
        return "Yes"
    if raw_text in {"no", "n", "false", "0", "tht", "through_hole", "through-hole"}:
        return "No"

    package = str(entry.attributes.get("package", "")).strip()
    if _is_smd_token(package):
        return "Yes"

    derived_package = derive_package_from_footprint(entry.footprint)
    if _is_smd_token(derived_package):
        return "Yes"

    if _is_smd_token(entry.footprint):
        return "Yes"

    return "No"


def _coerce_output_value(raw_value: Any) -> str:
    """Convert raw values to output-ready strings while preserving empties."""

    if isinstance(raw_value, str):
        return raw_value if raw_value.strip() else ""

    if raw_value is None:
        return ""

    if isinstance(raw_value, bool):
        return "Yes" if raw_value else "No"

    return str(raw_value)


def _get_attribute_value(entry: BOMEntry, key: str) -> str:
    """Return a normalized attribute value from a BOM entry."""

    return _coerce_output_value(entry.attributes.get(key, ""))


def _resolve_inventory_field_value(entry: BOMEntry, inventory_field: str) -> str:
    """Resolve an inventory-prefixed field with schema-aware fallbacks."""
    raw_value = entry.attributes.get(f"i:{inventory_field}", "")
    if isinstance(raw_value, str):
        if raw_value.strip():
            return raw_value
    elif raw_value:
        return str(raw_value)
    legacy_value = entry.attributes.get(inventory_field, "")
    if isinstance(legacy_value, str):
        if legacy_value.strip():
            return legacy_value
    elif legacy_value:
        return str(legacy_value)

    return ""


def _resolve_standard_field_value(
    entry: BOMEntry,
    field: str,
    *,
    fabricator_id: str,
    fabricator_config: Optional[FabricatorConfig],
) -> str:
    """Resolve a standard (non-prefixed) BOM field."""

    field_mapping = {
        "reference": lambda e: e.references_string,
        "quantity": lambda e: str(e.quantity),
        "value": lambda e: e.value,
        "description": lambda e: _get_attribute_value(e, "description"),
        "footprint": lambda e: e.footprint,
        "manufacturer": lambda e: _get_attribute_value(e, "manufacturer"),
        "mfgpn": lambda e: _get_attribute_value(e, "manufacturer_part"),
        "fabricator_part_number": lambda e: _resolve_fabricator_part_number(
            e,
            fabricator_id=fabricator_id,
            fabricator_config=fabricator_config,
        ),
        "smd": lambda e: _resolve_smd_indicator(e),
        "lcsc": lambda e: _get_attribute_value(e, "lcsc")
        or _get_attribute_value(e, "LCSC"),
        "package": lambda e: _get_attribute_value(e, "package")
        or derive_package_from_footprint(e.footprint),
    }

    if field in field_mapping:
        return field_mapping[field](entry)

    return _get_attribute_value(entry, field)


def _resolve_namespaced_field_value(
    entry: BOMEntry,
    namespace: str,
    namespaced_field: str,
    *,
    fabricator_id: str,
    fabricator_config: Optional[FabricatorConfig],
) -> str:
    """Resolve a namespace-qualified field with deterministic fallbacks."""

    explicit = _get_attribute_value(entry, f"{namespace}:{namespaced_field}")
    if explicit:
        return explicit

    if namespace == "i":
        return _resolve_inventory_field_value(entry, namespaced_field)

    if namespace in {"s", "c"}:
        return _resolve_standard_field_value(
            entry,
            namespaced_field,
            fabricator_id=fabricator_id,
            fabricator_config=fabricator_config,
        )

    return ""


def _resolve_annotation_field_value(
    entry: BOMEntry,
    annotation_field: str,
    *,
    fabricator_id: str,
    fabricator_config: Optional[FabricatorConfig],
) -> str:
    """Render `a:*` fields as deterministic source annotation lines."""

    explicit = _get_attribute_value(entry, f"a:{annotation_field}")
    if explicit:
        return explicit

    lines: list[tuple[str, str]] = []

    for namespace in ("s", "p"):
        value = _resolve_namespaced_field_value(
            entry,
            namespace,
            annotation_field,
            fabricator_id=fabricator_id,
            fabricator_config=fabricator_config,
        )
        if value:
            lines.append((namespace, value))

    inventory_value = _resolve_namespaced_field_value(
        entry,
        "i",
        annotation_field,
        fabricator_id=fabricator_id,
        fabricator_config=fabricator_config,
    )
    if inventory_value:
        lines.append(("i", inventory_value))

    canonical_value = _resolve_namespaced_field_value(
        entry,
        "c",
        annotation_field,
        fabricator_id=fabricator_id,
        fabricator_config=fabricator_config,
    )
    if canonical_value:
        if not lines or any(value != canonical_value for _, value in lines):
            lines.append(("c", canonical_value))

    if not lines:
        return ""

    return "\n".join(f"{namespace}:{value}" for namespace, value in lines)


def _get_field_value(
    entry,
    field: str,
    *,
    fabricator_id: str = "generic",
    fabricator_config: Optional[FabricatorConfig] = None,
) -> str:
    """Extract field value from BOM entry.

    Args:
        entry: BOM entry object
        field: Field name to extract

    Returns:
        String value for the field
    """
    # Handle namespaced fields
    if field.startswith("i:"):
        return _resolve_namespaced_field_value(
            entry,
            "i",
            field[2:],
            fabricator_id=fabricator_id,
            fabricator_config=fabricator_config,
        )

    if field.startswith("s:"):
        return _resolve_namespaced_field_value(
            entry,
            "s",
            field[2:],
            fabricator_id=fabricator_id,
            fabricator_config=fabricator_config,
        )

    if field.startswith("p:"):
        return _resolve_namespaced_field_value(
            entry,
            "p",
            field[2:],
            fabricator_id=fabricator_id,
            fabricator_config=fabricator_config,
        )

    if field.startswith("c:"):
        return _resolve_namespaced_field_value(
            entry,
            "c",
            field[2:],
            fabricator_id=fabricator_id,
            fabricator_config=fabricator_config,
        )

    if field.startswith("a:"):
        return _resolve_annotation_field_value(
            entry,
            field[2:],
            fabricator_id=fabricator_id,
            fabricator_config=fabricator_config,
        )

    # Handle standard BOM fields
    return _resolve_standard_field_value(
        entry,
        field,
        fabricator_id=fabricator_id,
        fabricator_config=fabricator_config,
    )
