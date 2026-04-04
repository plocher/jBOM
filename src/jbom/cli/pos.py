"""POS (Position) command - generate component placement files."""

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
from jbom.services.pcb_reader import DefaultKiCadReaderService
from jbom.services.pos_generator import POSGenerator
from jbom.services.project_file_resolver import ProjectFileResolver
from jbom.services.schematic_reader import SchematicReader
from jbom.services.component_merge_service import (
    ComponentMergeResult,
    ComponentMergeService,
)
from jbom.services.field_listing_service import (
    FieldListingService,
    get_field_names,
    get_namespaced_field_tokens,
    resolve_field,
)
from jbom.services.project_component_collector import ProjectComponentCollector
from jbom.common.options import PlacementOptions, GeneratorOptions
from jbom.common.cli_fabricator import (
    add_fabricator_arguments,
    resolve_fabricator_from_args,
)
from jbom.common.field_parser import parse_fields_argument
from jbom.common.fields import field_to_header, normalize_field_name
from jbom.common.component_filters import (
    add_component_filter_arguments,
    create_filter_config,
)
from jbom.config.fabricators import (
    FabricatorConfig,
    get_fabricator_default_fields,
)
from jbom.cli.formatting import Column, print_table, get_terminal_width
from jbom.services.fabricator_projection_service import FabricatorProjectionService

_NUMERIC_POS_FIELDS: frozenset[str] = frozenset({"x", "y", "rotation"})
_POS_SOURCE_PRIORITY = "pis"
_POS_COMPUTED_FIELDS: tuple[str, ...] = (
    "reference",
    "x",
    "y",
    "rotation",
    "side",
    "footprint",
    "package",
    "value",
    "fabricator_part_number",
)


def _run_pos_component_merge(
    *,
    schematic_components: list[Any],
    pcb_components: list[Any],
    schematic_files: list[Path],
    pcb_file: Optional[Path],
    verbose: bool,
) -> ComponentMergeResult | None:
    """Best-effort collector/merge execution for POS namespace enrichment."""

    try:
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


def _enrich_pos_with_merge_namespaces(
    pos_data: list[dict[str, Any]],
    merge_result: ComponentMergeResult | None,
) -> list[dict[str, Any]]:
    """Attach merge namespace fields (`s:/p:/a:`) onto POS row dictionaries."""

    if merge_result is None or not merge_result.records:
        return pos_data

    enriched_rows: list[dict[str, Any]] = []
    any_updated = False
    for row in pos_data:
        reference = str(row.get("reference", "")).strip()
        merge_record = merge_result.records.get(reference)
        if merge_record is None:
            enriched_rows.append(row)
            continue

        merged_fields: dict[str, str] = {}
        merged_fields.update(merge_record.source_fields)
        merged_fields.update(merge_record.annotated_fields)
        if not merged_fields:
            enriched_rows.append(row)
            continue

        updated_row = dict(row)
        row_updated = False
        for field_key, field_value in merged_fields.items():
            normalized_value = str(field_value or "").strip()
            if not normalized_value:
                continue
            if str(updated_row.get(field_key, "")).strip() == normalized_value:
                continue
            updated_row[field_key] = normalized_value
            row_updated = True

        if row_updated:
            any_updated = True
            enriched_rows.append(updated_row)
        else:
            enriched_rows.append(row)

    return enriched_rows if any_updated else pos_data


def register_command(subparsers) -> None:
    """Register pos command with argument parser."""
    parser = subparsers.add_parser(
        "pos", help="Generate component placement files from KiCad PCB"
    )

    # Positional argument - now supports project-centric inputs
    parser.add_argument(
        "input",
        nargs="?",
        default=".",
        help="Path to .kicad_pcb file, project directory, or base name (default: current directory)",
    )

    # Output options
    parser.add_argument(
        "-o",
        "--output",
        help='Output destination: omit for default file output, use "console" for table, "-" for CSV to stdout, or a file path',
    )
    add_force_argument(parser)

    # Filtering options
    parser.add_argument(
        "--smd-only",
        action="store_true",
        help="Include only SMD components",
    )

    parser.add_argument(
        "--layer",
        choices=["TOP", "BOTTOM"],
        help="Include only components on specified layer",
    )

    # Units flag retained for backward compatible CLI help and UX tests.
    # POS currently always uses mm internally.
    parser.add_argument(
        "--units",
        choices=["mm"],
        default="mm",
        help="Units for POS output (mm only)",
    )

    # Origin options
    parser.add_argument(
        "--origin",
        choices=["board", "aux"],
        default="board",
        help="Origin reference (default: board)",
    )

    # Field selection options
    parser.add_argument(
        "-f",
        "--fields",
        help=(
            "Select specific fields for POS output. Comma-separated list or +preset. "
            "Any field name is accepted; unknown fields produce blank cells. "
            "Use --list-fields to see known fields."
        ),
    )

    parser.add_argument(
        "--list-fields",
        action="store_true",
        help="List available fields and presets, then exit",
    )

    # Component filtering (POS-specific: only DNP filtering applies)
    add_component_filter_arguments(parser, command_type="pos")

    # Fabricator selection (for field presets / predictable output)
    add_fabricator_arguments(parser)

    # Options
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    parser.set_defaults(handler=handle_pos)


def handle_pos(args: argparse.Namespace) -> int:
    """Handle POS command with project-centric input resolution."""
    try:
        # Create options
        gen_options = GeneratorOptions(verbose=args.verbose) if args.verbose else None

        # Resolve fabricator from arguments
        fabricator = resolve_fabricator_from_args(args)
        if args.list_fields:
            list_pcb_components: list[Any] = []
            list_schematic_components: list[Any] = []
            try:
                list_resolver = ProjectFileResolver(
                    prefer_pcb=True,
                    target_file_type="pcb",
                    options=gen_options,
                )
                list_resolved = list_resolver.resolve_input(args.input)
                if not list_resolved.is_pcb:
                    list_resolved = list_resolver.resolve_for_wrong_file_type(
                        list_resolved,
                        "pcb",
                    )
                list_pcb_path = list_resolved.resolved_path
                if list_pcb_path.exists():
                    list_board = DefaultKiCadReaderService().read_pcb_file(
                        list_pcb_path
                    )
                    list_pcb_components = list(list_board.footprints)
                list_project_context = list_resolved.project_context
                if list_project_context is not None:
                    list_schematic_files = [
                        file_path
                        for file_path in list_project_context.get_hierarchical_schematic_files()
                        if file_path.suffix.lower() == ".kicad_sch"
                        and file_path.exists()
                    ]
                    list_schematic_reader = SchematicReader(gen_options)
                    for schematic_file in list_schematic_files:
                        list_schematic_components.extend(
                            list_schematic_reader.load_components(schematic_file)
                        )
            except Exception:
                pass

            _list_available_pos_fields(
                fabricator,
                schematic_components=list_schematic_components or None,
                pcb_components=list_pcb_components or None,
            )
            return 0

        # Use ProjectFileResolver for intelligent input resolution
        resolver = ProjectFileResolver(
            prefer_pcb=True, target_file_type="pcb", options=gen_options
        )
        resolved_input = resolver.resolve_input(args.input)

        # Handle cross-command intelligence - if user provided wrong file type, try to resolve it
        if not resolved_input.is_pcb:
            # Provide guidance about cross-resolution unless quiet
            import os as _os

            if not _os.environ.get("JBOM_QUIET"):
                print(
                    f"Note: POS generation requires a PCB file. "
                    f"Found {resolved_input.resolved_path.suffix} file, trying to find matching PCB.",
                    file=sys.stderr,
                )

            resolved_input = resolver.resolve_for_wrong_file_type(resolved_input, "pcb")
            # Emit phrasing expected by Gherkin tests unless quiet
            import os as _os

            if not _os.environ.get("JBOM_QUIET"):
                print(
                    f"found matching PCB {resolved_input.resolved_path.name}",
                    file=sys.stderr,
                )
                print(
                    f"Using PCB: {resolved_input.resolved_path.name}", file=sys.stderr
                )

        pcb_file = resolved_input.resolved_path

        if not resolved_input.project_context:
            raise ValueError("No project context available")

        project_context = resolved_input.project_context
        project_name = project_context.project_base_name
        default_output_path = (
            project_context.project_directory / f"{project_name}.pos.csv"
        )

        # If project has hierarchical schematics, emit a helpful diagnostic (tests expect this)
        if resolved_input.project_context:
            try:
                hier_files = (
                    resolved_input.project_context.get_hierarchical_schematic_files()
                )
                if hier_files and len(hier_files) > 1:
                    print("Processing hierarchical design", file=sys.stderr)
            except Exception:
                pass

        # Create placement options - units removed, always mm with raw token echo
        options = PlacementOptions(
            origin=args.origin,
            smd_only=args.smd_only,
            layer_filter=args.layer,
        )

        # Create component filter configuration (for future DNP filtering support)
        component_filters = create_filter_config(args, command_type="pos")
        if args.verbose and not component_filters.get("exclude_dnp", True):
            print("Including DNP components in POS output", file=sys.stderr)

        # Use services to generate POS data
        reader = DefaultKiCadReaderService()
        generator = POSGenerator(options)

        # Read PCB data
        board = reader.read_pcb_file(pcb_file)

        # Generate position data
        pos_data = generator.generate_pos_data(board)
        schematic_files: list[Path] = []
        try:
            discovered_files = list(project_context.get_hierarchical_schematic_files())
            schematic_files = [
                file_path
                for file_path in discovered_files
                if file_path.suffix.lower() == ".kicad_sch" and file_path.exists()
            ]
        except Exception as exc:
            if args.verbose:
                print(
                    f"Warning: could not load schematic files for merge enrichment: {exc}",
                    file=sys.stderr,
                )
        schematic_components: list[Any] = []
        if schematic_files:
            schematic_reader = SchematicReader(gen_options)
            for schematic_file in schematic_files:
                try:
                    schematic_components.extend(
                        schematic_reader.load_components(schematic_file)
                    )
                except Exception as exc:
                    if args.verbose:
                        print(
                            "Warning: skipping schematic source for merge enrichment "
                            f"({schematic_file}): {exc}",
                            file=sys.stderr,
                        )
        merge_result = _run_pos_component_merge(
            schematic_components=schematic_components,
            pcb_components=list(board.footprints),
            schematic_files=schematic_files,
            pcb_file=pcb_file,
            verbose=args.verbose,
        )
        pos_data = _enrich_pos_with_merge_namespaces(pos_data, merge_result)
        pos_data = _apply_pos_dnp_filter(pos_data, component_filters=component_filters)

        # Parse field selection with fabricator awareness
        available_pos_fields = _get_available_pos_fields(
            schematic_components=schematic_components,
            pcb_components=list(board.footprints),
        )
        # NOTE: Don't pass BOM fabricator_presets to POS - they contain incompatible fields
        # POS uses get_fabricator_default_fields() instead

        # Explicitly reject empty --fields (e.g., --fields '' or only commas)
        if args.fields is not None:
            raw = [t.strip() for t in args.fields.split(",")]
            tokens = []
            for tok in raw:
                if not tok:
                    continue
                if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in ("'", '"'):
                    tok = tok[1:-1].strip()
                if tok:
                    tokens.append(tok)
            if not tokens:
                print("Error: --fields parameter cannot be empty", file=sys.stderr)
                return 1

        # Track whether fields were user-specified or came from fabricator defaults
        # If user specified a non-generic fabricator, treat field additions as fabricator preset modifications
        user_specified_fields = args.fields is not None and fabricator == "generic"

        try:
            selected_fields = parse_fields_argument(
                args.fields,
                available_pos_fields,
                fabricator,
                None,  # No BOM presets for POS
                context="pos",
            )
            # Permissive: unknown fields are accepted and produce blank cells.
            # No strict validation — jBOM is a flexible tool, not a gatekeeper.

        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        # Handle output
        return _output_pos(
            pos_data,
            args.output,
            fabricator,
            selected_fields,
            user_specified_fields,
            default_output_path=default_output_path,
            force=args.force,
        )

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _get_available_pos_fields(
    *,
    schematic_components: list | None = None,
    pcb_components: list | None = None,
    inventory_column_names: list[str] | None = None,
) -> dict[str, str]:
    """Get available POS fields with descriptions.

    Returns:
        Dict mapping field names to descriptions
    """
    known_fields = {
        field_name: "Computed POS field" for field_name in _POS_COMPUTED_FIELDS
    }
    for source_token in get_namespaced_field_tokens(
        schematic_components=schematic_components or [],
        pcb_components=pcb_components or [],
        inventory_column_names=inventory_column_names or [],
    ):
        known_fields[source_token] = "Discovered source field"
    for field_name in get_field_names(
        schematic_components=schematic_components or [],
        pcb_components=pcb_components or [],
        inventory_column_names=inventory_column_names or [],
        source="all",
    ):
        known_fields.setdefault(field_name, "Discovered field")
    return known_fields


def _list_available_pos_fields(
    fabricator: str,
    *,
    schematic_components: list | None = None,
    pcb_components: list | None = None,
    inventory_column_names: list[str] | None = None,
) -> None:
    """List known POS fields and fabricator defaults.

    Fields are dynamically derived from the POS schema. Any field name is accepted;
    unknown fields produce blank cells.

    Args:
        fabricator: Current fabricator ID
    """

    known_fields = _get_available_pos_fields(
        schematic_components=schematic_components,
        pcb_components=pcb_components,
        inventory_column_names=inventory_column_names,
    )
    matrix_rows = FieldListingService().build_namespace_matrix(known_fields.keys())

    print(
        "\nKnown POS fields (any field name is accepted — unknown fields produce blank cells):"
    )
    columns = [
        Column(header="Name", key="Name", preferred_width=22, wrap=False),
        Column(header="s:", key="s:", preferred_width=16, wrap=False),
        Column(header="p:", key="p:", preferred_width=16, wrap=False),
        Column(header="i:", key="i:", preferred_width=16, wrap=False),
    ]
    print_table(
        [row.to_console_row() for row in matrix_rows],
        columns,
        terminal_width=get_terminal_width(),
    )

    # Show default fields for the active fabricator
    default_fields = get_fabricator_default_fields(fabricator, "pos")
    if default_fields:
        print(
            f"\nDefault fields for {fabricator} fabricator (when --fields not specified):"
        )
        print(f"  {', '.join(default_fields)}")


def _resolve_pos_output_projection(
    *,
    selected_fields: list[str] | None,
    fabricator: str,
    user_specified_fields: bool,
    projection_service: FabricatorProjectionService | None = None,
) -> tuple[list[str], list[str], Optional[FabricatorConfig]]:
    """Resolve effective POS fields, headers, and fabricator config."""

    effective_fields = list(selected_fields) if selected_fields else []
    if not effective_fields:
        effective_fields = _resolve_default_pos_fields(fabricator)

    service = projection_service or FabricatorProjectionService()
    projection = service.build_projection(
        fabricator_id=fabricator,
        output_type="pos",
        selected_fields=effective_fields,
    )

    headers = (
        [field_to_header(field) for field in effective_fields]
        if user_specified_fields
        else list(projection.headers)
    )
    return effective_fields, headers, projection.fabricator_config


def _resolve_default_pos_fields(fabricator: str) -> list[str]:
    """Resolve POS default output fields from fabricator profile metadata."""

    fabricator_defaults = get_fabricator_default_fields(fabricator, "pos")
    if fabricator_defaults:
        return list(fabricator_defaults)

    generic_defaults = get_fabricator_default_fields("generic", "pos")
    if generic_defaults:
        return list(generic_defaults)

    raise ValueError(
        "No POS default fields found in fabricator profile configuration for "
        f"'{fabricator}' or 'generic'"
    )


def _output_pos(
    pos_data: list,
    output: str | None,
    fabricator: str = "generic",
    selected_fields: list | None = None,
    user_specified_fields: bool = False,
    *,
    default_output_path: Path,
    force: bool,
) -> int:
    """Output position data in the requested format."""
    selected_fields, headers, fabricator_config = _resolve_pos_output_projection(
        selected_fields=selected_fields,
        fabricator=fabricator,
        user_specified_fields=user_specified_fields,
    )

    dest = resolve_output_destination(
        output,
        default_destination=OutputDestination(
            OutputKind.FILE, path=default_output_path
        ),
    )

    if dest.kind == OutputKind.CONSOLE:
        _print_console_table(
            pos_data,
            selected_fields,
            headers,
            fabricator_id=fabricator,
            fabricator_config=fabricator_config,
        )
        return 0

    if dest.kind == OutputKind.STDOUT:
        _print_csv(
            pos_data,
            selected_fields,
            headers,
            out=sys.stdout,
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
            _print_csv(
                pos_data,
                selected_fields,
                headers,
                out=f,
                fabricator_id=fabricator,
                fabricator_config=fabricator_config,
            )
    except OutputRefusedError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Position file written to {output_path}")
    return 0


def _print_console_table(
    pos_data: list,
    selected_fields: list,
    headers: list,
    *,
    fabricator_id: str,
    fabricator_config: Optional[FabricatorConfig],
) -> None:
    """Print position data as formatted console table."""
    print(f"\nComponent Placement Data ({len(pos_data)} components)")
    print("=" * 80)

    if not pos_data:
        print("No components found.")
        return

    rows = [
        {
            h: _get_pos_field_value(
                entry,
                f,
                fabricator_id=fabricator_id,
                fabricator_config=fabricator_config,
            )
            for f, h in zip(selected_fields, headers)
        }
        for entry in pos_data
    ]
    columns = [
        Column(
            header=h,
            key=h,
            preferred_width=max(10, len(h)),
            wrap=False,
            align="right" if f in _NUMERIC_POS_FIELDS else "left",
        )
        for f, h in zip(selected_fields, headers)
    ]
    print_table(rows, columns, terminal_width=get_terminal_width())

    print(f"\nTotal: {len(pos_data)} components")


def _print_csv(
    pos_data: list,
    selected_fields: list,
    headers: list,
    *,
    out: TextIO,
    fabricator_id: str,
    fabricator_config: Optional[FabricatorConfig],
) -> None:
    """Print position data as CSV to a file-like object."""

    # QUOTE_ALL ensures values like "0603" are written as "\"0603\"" so
    # spreadsheet apps treat them as text and preserve leading zeros.
    writer = csv.writer(out, quoting=csv.QUOTE_ALL)

    # Use headers exactly as provided by fabricator column mapping
    writer.writerow(headers)

    # Data rows - output only selected fields in specified order
    for entry in pos_data:
        row = []
        for field in selected_fields:
            value = _get_pos_field_value(
                entry,
                field,
                fabricator_id=fabricator_id,
                fabricator_config=fabricator_config,
            )
            row.append(value)
        writer.writerow(row)


def _resolve_fabricator_part_number(
    entry: dict[str, Any],
    *,
    fabricator_id: str,
    fabricator_config: Optional[FabricatorConfig],
) -> str:
    """Resolve fabricator part number using shared projection service behavior."""

    return FabricatorProjectionService.resolve_fabricator_part_number(
        entry,
        fabricator_id=fabricator_id,
        fabricator_config=fabricator_config,
    )


def _get_pos_field_value(
    entry: dict[str, Any],
    field: str,
    *,
    fabricator_id: str = "generic",
    fabricator_config: Optional[FabricatorConfig] = None,
) -> str:
    """Extract field value from POS entry.

    Args:
        entry: POS entry dictionary
        field: Field name to extract

    Returns:
        String value for the field
    """
    row_sources = _build_pos_row_sources(entry)
    namespace_prefix, separator, _ = field.partition(":")
    if separator and namespace_prefix in {"s", "p", "i"}:
        return resolve_field(field, row_sources, priority=_POS_SOURCE_PRIORITY)
    if separator and namespace_prefix == "a":
        return str(entry.get(field, "") or "")
    # Handle coordinate/rotation fields
    if field == "x":
        if entry.get("x_raw"):
            return str(entry["x_raw"])  # echo exactly as authored in PCB (mm)
        return f"{entry['x_mm']:.4f}"
    elif field == "y":
        if entry.get("y_raw"):
            return str(entry["y_raw"])  # echo exactly as authored in PCB (mm)
        return f"{entry['y_mm']:.4f}"
    elif field == "rotation":
        if entry.get("rotation_raw") is not None:
            return str(entry["rotation_raw"])  # echo raw if available
        return f"{entry['rotation']:.1f}"

    if field == "fabricator_part_number":
        return _resolve_fabricator_part_number(
            entry,
            fabricator_id=fabricator_id,
            fabricator_config=fabricator_config,
        )

    # Handle standard POS fields
    field_mapping = {
        "reference": "reference",
        "side": "side",
    }

    if field in field_mapping:
        pos_key = field_mapping[field]
        return str(entry.get(pos_key, ""))
    if field in {"value", "footprint", "package"}:
        return resolve_field(
            field,
            row_sources,
            priority=_POS_SOURCE_PRIORITY,
        )

    # Fallback for unknown fields
    return resolve_field(
        field,
        row_sources,
        priority=_POS_SOURCE_PRIORITY,
    ) or str(entry.get(field, ""))


def _build_pos_row_sources(entry: dict[str, Any]) -> dict[str, dict[str, object]]:
    """Build source field maps for one POS row (`s`, `p`, `i`)."""

    row_sources: dict[str, dict[str, object]] = {"s": {}, "p": {}, "i": {}}
    for key, value in entry.items():
        normalized_key = normalize_field_name(str(key or ""))
        prefix, separator, remainder = normalized_key.partition(":")
        if separator and prefix in {"s", "p", "i"} and remainder:
            row_sources[prefix][remainder] = value
        elif normalized_key:
            row_sources["p"].setdefault(normalized_key, value)

    if entry.get("x_raw"):
        row_sources["p"].setdefault("x", entry.get("x_raw"))
    elif entry.get("x_mm") is not None:
        row_sources["p"].setdefault("x", f"{entry['x_mm']:.4f}")

    if entry.get("y_raw"):
        row_sources["p"].setdefault("y", entry.get("y_raw"))
    elif entry.get("y_mm") is not None:
        row_sources["p"].setdefault("y", f"{entry['y_mm']:.4f}")

    if entry.get("rotation_raw") is not None:
        row_sources["p"].setdefault("rotation", entry.get("rotation_raw"))
    elif entry.get("rotation") is not None:
        row_sources["p"].setdefault("rotation", f"{entry['rotation']:.1f}")

    return row_sources


def _is_truthy_dnp_marker(value: object) -> bool:
    """Return True when a DNP marker should exclude a POS row."""

    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().lower()
    if not normalized:
        return False
    return normalized in {
        "1",
        "true",
        "t",
        "yes",
        "y",
        "x",
        "dnp",
        "do not populate",
    }


def _entry_has_dnp_marker(entry: dict[str, Any]) -> bool:
    """Return True when a POS row contains schematic/inventory DNP flags."""

    for key in ("dnp", "s:dnp", "i:dnp"):
        if _is_truthy_dnp_marker(entry.get(key)):
            return True
    return False


def _apply_pos_dnp_filter(
    pos_data: list[dict[str, Any]],
    *,
    component_filters: dict[str, Any],
) -> list[dict[str, Any]]:
    """Filter DNP rows from POS data unless `--include-dnp` is active."""

    if not component_filters.get("exclude_dnp", True):
        return pos_data
    return [entry for entry in pos_data if not _entry_has_dnp_marker(entry)]
