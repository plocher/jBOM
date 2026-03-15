"""Parts command - thin CLI wrapper over Parts List workflows."""

import argparse
import csv
import sys
from pathlib import Path
from typing import Any, Optional, TextIO

from jbom.cli.output import (
    OutputDestination,
    OutputKind,
    OutputRefusedError,
    add_force_argument,
    open_output_text_file,
    resolve_output_destination,
)
from jbom.services.schematic_reader import SchematicReader
from jbom.services.parts_list_generator import (
    PartsListData,
    PartsListEntry,
    PartsListGenerator,
)
from jbom.services.component_merge_service import (
    ComponentMergeResult,
    ComponentMergeService,
    MergedReferenceRecord,
)
from jbom.services.pcb_reader import DefaultKiCadReaderService
from jbom.services.project_component_collector import ProjectComponentCollector
from jbom.services.project_file_resolver import ProjectFileResolver
from jbom.common.options import GeneratorOptions
from jbom.common.field_parser import parse_fields_argument
from jbom.common.fields import field_to_header
from jbom.common.component_filters import (
    add_component_filter_arguments,
    create_filter_config,
)
from jbom.config.fabricators import get_available_fabricators
from jbom.cli.formatting import Column, print_table, get_terminal_width


def _run_parts_component_merge(
    *,
    schematic_components: list[Any],
    schematic_files: list[Path],
    pcb_file: Path | None,
    verbose: bool,
) -> ComponentMergeResult | None:
    """Best-effort collector/merge execution for parts namespace enrichment."""

    try:
        pcb_components: list[Any] = []
        if pcb_file is not None and pcb_file.exists():
            board = DefaultKiCadReaderService().read_pcb_file(pcb_file)
            pcb_components = list(board.footprints)

        collector = ProjectComponentCollector()
        project_graph = collector.collect(
            schematic_components=schematic_components,
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
    """Resolve one merge namespace field when grouped references agree."""

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


def _resolve_parts_entry_merge_namespace_fields(
    reference_records: list[MergedReferenceRecord],
) -> dict[str, str]:
    """Resolve stable merge namespace values for one aggregated parts entry."""

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


def _enrich_parts_with_merge_namespaces(
    parts_data: PartsListData,
    merge_result: ComponentMergeResult | None,
) -> PartsListData:
    """Attach merge namespace attributes (`s:/p:/c:/a:`) to parts entries."""

    if merge_result is None or not merge_result.records:
        return parts_data

    updated_entries: list[PartsListEntry] = []
    any_entry_updated = False
    for entry in parts_data.entries:
        entry_records = [
            merge_result.records[reference]
            for reference in entry.refs
            if reference in merge_result.records
        ]
        if not entry_records:
            updated_entries.append(entry)
            continue

        merge_namespace_fields = _resolve_parts_entry_merge_namespace_fields(
            entry_records
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
            PartsListEntry(
                refs=entry.refs,
                value=entry.value,
                footprint=entry.footprint,
                package=entry.package,
                part_type=entry.part_type,
                tolerance=entry.tolerance,
                voltage=entry.voltage,
                dielectric=entry.dielectric,
                lib_id=entry.lib_id,
                attributes=attributes,
            )
        )

    metadata = dict(parts_data.metadata)
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
    return PartsListData(
        project_name=parts_data.project_name,
        entries=updated_entries if any_entry_updated else parts_data.entries,
        metadata=metadata,
    )


def _get_available_parts_fields() -> dict[str, str]:
    """Return known parts output fields for discovery and presets."""

    return {
        "refs": "Aggregated reference designators",
        "value": "Component value",
        "footprint": "Component footprint",
        "package": "Package token",
        "part_type": "Component type",
        "tolerance": "Tolerance value",
        "voltage": "Voltage rating",
        "dielectric": "Dielectric type",
        "s:value": "Schematic source value",
        "p:footprint": "PCB source footprint",
        "c:value": "Canonical merged value",
        "a:value": "Merge annotation value",
    }


def _list_available_parts_fields() -> None:
    """List known parts fields and presets, then exit."""

    known_fields = _get_available_parts_fields()
    print(
        "\nKnown parts fields (any field name is accepted — unknown fields produce blank cells):"
    )
    print("=" * 60)
    for field_name in sorted(known_fields.keys()):
        print(
            f"  {field_name:<30}  ({field_to_header(field_name)}):  {known_fields[field_name]}"
        )


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
        help='Output destination: omit for default file output, use "console" for table, "-" for CSV to stdout, or a file path',
    )
    add_force_argument(parser)

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

    # Component filtering options
    add_component_filter_arguments(parser)
    # Field selection
    parser.add_argument(
        "-f",
        "--fields",
        help=(
            "Select specific fields for parts output. Comma-separated list or +preset. "
            "Any field name is accepted; unknown fields produce blank cells. "
            "Use --list-fields to see known fields."
        ),
    )
    parser.add_argument(
        "--list-fields",
        action="store_true",
        help="List available fields and presets, then exit",
    )

    # Options
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    parser.set_defaults(handler=handle_parts)


def handle_parts(args: argparse.Namespace) -> int:
    """Handle Parts command with project-centric input resolution."""
    try:
        # Create options
        options = GeneratorOptions(verbose=args.verbose) if args.verbose else None

        if args.list_fields:
            _list_available_parts_fields()
            return 0

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

        if not resolved_input.project_context:
            raise ValueError("No project context available")

        project_context = resolved_input.project_context
        project_name = project_context.project_base_name
        default_output_path = (
            project_context.project_directory / f"{project_name}.parts.csv"
        )

        # Use services directly - no workflow abstraction needed
        reader = SchematicReader(options)
        generator = PartsListGenerator()

        # Load components from schematic (including hierarchical sheets if available)
        if resolved_input.project_context:
            # Get all hierarchical schematic files for complete parts list
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

        # Generate basic parts list with common filtering logic
        filters = create_filter_config(args)
        parts_data = generator.generate_parts_list_data(
            components, project_name, filters
        )
        merge_result = _run_parts_component_merge(
            schematic_components=components,
            schematic_files=schematic_files,
            pcb_file=project_context.pcb_file,
            verbose=args.verbose,
        )
        parts_data = _enrich_parts_with_merge_namespaces(parts_data, merge_result)

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

        available_parts_fields = _get_available_parts_fields()
        try:
            selected_fields = parse_fields_argument(
                args.fields,
                available_parts_fields,
                fabricator_id=fabricator,
                context="parts",
            )
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        # Handle output
        return _output_parts(
            parts_data,
            args.output,
            project_name,
            selected_fields=selected_fields,
            default_output_path=default_output_path,
            force=args.force,
        )

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
    parts_data: PartsListData,
    output: Optional[str],
    project_name: str,
    selected_fields: list[str] | None = None,
    *,
    default_output_path: Path,
    force: bool,
) -> int:
    """Output Parts List data in the requested format."""
    selected_fields, headers, widths = _resolve_parts_output_projection(selected_fields)
    dest = resolve_output_destination(
        output,
        default_destination=OutputDestination(
            OutputKind.FILE, path=default_output_path
        ),
    )

    if dest.kind == OutputKind.CONSOLE:
        _print_console_table(parts_data, selected_fields, headers, widths)
        return 0

    if dest.kind == OutputKind.STDOUT:
        _print_csv(parts_data, selected_fields, headers, out=sys.stdout)
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
            _print_csv(parts_data, selected_fields, headers, out=f)
    except OutputRefusedError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Parts list written to {output_path}")
    return 0


_DEFAULT_PARTS_COLUMNS: list[tuple[str, str, int]] = [
    ("refs", "Refs", 20),
    ("value", "Value", 12),
    ("footprint", "Footprint", 20),
    ("package", "Package", 14),
    ("part_type", "Type", 10),
    ("tolerance", "Tolerance", 10),
    ("voltage", "Voltage", 8),
    ("dielectric", "Dielectric", 10),
]


def _resolve_parts_output_projection(
    selected_fields: list[str] | None,
) -> tuple[list[str], list[str], list[int]]:
    """Resolve effective fields, headers, and widths for parts output."""

    default_fields = [field_name for field_name, _, _ in _DEFAULT_PARTS_COLUMNS]
    effective_fields = selected_fields or default_fields
    if effective_fields == default_fields:
        headers = [header for _, header, _ in _DEFAULT_PARTS_COLUMNS]
        widths = [width for _, _, width in _DEFAULT_PARTS_COLUMNS]
    else:
        headers = [field_to_header(field_name) for field_name in effective_fields]
        widths = [max(10, len(header)) for header in headers]
    return effective_fields, headers, widths


def _get_parts_field_value(entry: PartsListEntry, field: str) -> str:
    """Resolve one parts output field from entry attributes and namespaces."""

    if field in {"refs", "reference", "refs_csv"}:
        return entry.refs_csv

    direct_mapping = {
        "value": "value",
        "footprint": "footprint",
        "package": "package",
        "part_type": "part_type",
        "type": "part_type",
        "tolerance": "tolerance",
        "voltage": "voltage",
        "dielectric": "dielectric",
        "lib_id": "lib_id",
    }
    mapped_attr = direct_mapping.get(field)
    if mapped_attr:
        return str(getattr(entry, mapped_attr, "") or "")

    if field.startswith(("s:", "p:", "i:", "c:", "a:")):
        return str(entry.attributes.get(field, "") or "")

    return str(entry.attributes.get(field, "") or "")


def _print_console_table(
    parts_data: PartsListData,
    selected_fields: list[str],
    headers: list[str],
    widths: list[int],
) -> None:
    """Print Parts List as formatted console table."""
    print(f"\n{parts_data.project_name} - Parts List")
    print("=" * 60)

    if not parts_data.entries:
        print("No components found.")
        return

    rows = [
        {
            header: _get_parts_field_value(entry, field_name)
            for field_name, header in zip(selected_fields, headers)
        }
        for entry in parts_data.entries
    ]
    columns = [
        Column(header=header, key=header, preferred_width=width, wrap=True)
        for header, width in zip(headers, widths)
    ]
    print_table(rows, columns, terminal_width=get_terminal_width())

    print(
        f"\nTotal: {parts_data.total_components} components in {parts_data.total_groups} groups"
    )

    # Show inventory enhancement info if available
    if "matched_entries" in parts_data.metadata:
        matched = parts_data.metadata["matched_entries"]
        print(
            f"Inventory enhanced: {matched}/{parts_data.total_components} items matched"
        )


def _print_csv(
    parts_data: PartsListData,
    selected_fields: list[str],
    headers: list[str],
    *,
    out: TextIO,
) -> None:
    """Print Parts List as CSV to a file-like object."""
    # QUOTE_ALL ensures values like "0603" are written as "\"0603\"" so
    # spreadsheet apps treat them as text and preserve leading zeros.
    writer = csv.writer(out, quoting=csv.QUOTE_ALL)
    writer.writerow(headers)
    for entry in parts_data.entries:
        writer.writerow(
            [
                _get_parts_field_value(entry, field_name)
                for field_name in selected_fields
            ]
        )
