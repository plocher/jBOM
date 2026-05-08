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
from jbom.services.bom_generator import BOMData, BOMEntry
from jbom.services.fabricator_projection_service import (
    FabricatorProjectionService,
)
from jbom.services.field_listing_service import (
    FieldListingService,
    resolve_field,
)
from jbom.services.component_merge_service import ComponentMergeResult
from jbom.config.fabricators import (
    FabricatorConfig,
    get_available_fabricators,
    get_fabricator_presets,
)
from jbom.common.fields import (
    get_available_presets,
    normalize_field_name,
    split_kicad_strip_field,
)
from jbom.common.component_filters import (
    add_component_filter_arguments,
    create_filter_config,
)
from jbom.common.component_utils import derive_package_from_footprint
from jbom.common.package_matching import PackageType
from jbom.cli.formatting import Column, print_table, get_terminal_width
from jbom.application.bom_workflow import (
    BOMWorkflow,
    BOMMode,
    BOMRequest,
    enforce_bom_device_footprints as _service_enforce_bom_device_footprints,
    enrich_bom_smd_from_project_pcb as _service_enrich_bom_smd_from_project_pcb,
    enrich_bom_with_merge_namespaces as _service_enrich_bom_with_merge_namespaces,
    entry_smd_from_reference_lookup as _service_entry_smd_from_reference_lookup,
    filter_inventory_dnp_entries as _service_filter_inventory_dnp_entries,
)
from jbom.application.jobs.contracts import (
    JobArtifact,
    JobContext,
    JobDiagnosticSeverity,
    JobOutcome,
    JobRequest,
)
from jbom.application.jobs.runner import JobEventStream, JobRunPayload, JobRunner

_BOM_SOURCE_PRIORITY = "pis"


def _enrich_bom_with_merge_namespaces(
    bom_data: BOMData,
    merge_result: ComponentMergeResult | None,
) -> BOMData:
    """Attach stable merge-model namespaces (`s:/p:/a:`) onto BOM entries."""
    return _service_enrich_bom_with_merge_namespaces(bom_data, merge_result)


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
        type=lambda value: str(value).strip().lower(),
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


def _resolve_requested_fabricator(args: argparse.Namespace) -> str:
    """Resolve effective fabricator selector from command arguments."""

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
    return str(fabricator)


def _predict_bom_artifacts(args: argparse.Namespace) -> tuple[JobArtifact, ...]:
    """Predict adapter-level BOM artifact descriptors from CLI output arguments."""

    output = str(args.output or "").strip()
    if output.lower() == "console":
        return ()
    if output == "-":
        return (
            JobArtifact(
                name="bom.csv",
                location="stdout://bom.csv",
                media_type="text/csv",
            ),
        )
    if output:
        output_path = Path(output)
        return (
            JobArtifact(
                name=output_path.name or "bom.csv",
                location=str(output_path),
                media_type="text/csv",
            ),
        )
    return (
        JobArtifact(
            name="bom.csv",
            location="project-default://bom.csv",
            media_type="text/csv",
        ),
    )


def _build_bom_job_request(args: argparse.Namespace) -> JobRequest:
    """Build adapter-neutral `JobRequest` contract for BOM execution."""

    inventory_files = tuple(str(path) for path in (args.inventory_files or []))
    options: dict[str, object] = {
        "input": str(args.input or "."),
        "output": str(args.output or ""),
        "fabricator": _resolve_requested_fabricator(args),
        "inventory_files": inventory_files,
        "verbose": bool(args.verbose),
        "list_fields": bool(args.list_fields),
    }
    return JobRequest(
        job_type="bom",
        intent="generate_bom",
        project_ref=str(args.input or "."),
        options=options,
        metadata={"adapter": "cli"},
    )


def handle_bom(args: argparse.Namespace) -> int:
    """Handle BOM command through the shared adapter-neutral job runner."""

    request = _build_bom_job_request(args)
    context = JobContext(
        adapter_id="cli",
        session_id="local-process",
        capabilities={
            "event_stream": True,
            "diagnostics": True,
            "cancellation": False,
        },
    )
    runner = JobRunner()

    def _execute(events: JobEventStream) -> JobRunPayload:
        events.progress(
            phase="resolve",
            message="Resolving project input and BOM orchestration plan",
        )
        exit_code = _execute_bom_command(args)
        if exit_code == 0:
            events.progress(
                phase="emit",
                message="BOM output emitted",
            )
        else:
            events.diagnostic(
                severity=JobDiagnosticSeverity.ERROR,
                message="BOM command execution failed",
                code="bom_execution_failed",
                details={"exit_code": exit_code},
            )

        return JobRunPayload(
            outcome=JobOutcome.SUCCEEDED if exit_code == 0 else JobOutcome.FAILED,
            artifacts=_predict_bom_artifacts(args) if exit_code == 0 else (),
            metadata={
                "exit_code": exit_code,
                "command": "bom",
                "fabricator": request.options.get("fabricator", "generic"),
            },
        )

    result = runner.run(request=request, context=context, execute=_execute)
    if result.outcome == JobOutcome.CANCELLED:
        return 130
    return int(result.metadata.get("exit_code", 1))


def _execute_bom_command(args: argparse.Namespace) -> int:
    """Execute BOM command body with project-centric input resolution."""
    try:
        fabricator = _resolve_requested_fabricator(args)
        request = BOMRequest(
            input_path=str(args.input or "."),
            fabricator=fabricator,
            fields_argument=args.fields,
            inventory_files=tuple(str(path) for path in (args.inventory_files or [])),
            filter_config=create_filter_config(args),
            verbose=bool(args.verbose),
            list_fields=bool(args.list_fields),
        )
        result = BOMWorkflow().run(request)
        for diagnostic in result.diagnostics:
            print(diagnostic, file=sys.stderr)

        if result.mode == BOMMode.LIST_FIELDS:
            if result.field_listing is None:
                raise ValueError("Missing field listing payload for list-fields output")
            _list_available_fields(
                fabricator,
                known_fields=dict(result.field_listing.known_fields),
            )
            return 0

        if result.generation is None:
            raise ValueError("Missing BOM generation payload")
        return _output_bom(
            result.generation.bom_data,
            args.output,
            list(result.generation.selected_fields),
            fabricator,
            default_output_path=result.generation.default_output_path,
            force=args.force,
        )

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _list_available_fields(
    fabricator: str,
    *,
    known_fields: dict[str, str],
) -> None:
    """List known BOM fields and presets for the given fabricator.

    Args:
        fabricator: Current fabricator ID (for fabricator-specific presets)
        known_fields: Precomputed field dictionary from application service
    """

    print(
        "\nKnown fields (any field name is accepted \u2014 unknown fields produce blank cells):"
    )
    matrix_rows = FieldListingService().build_namespace_matrix(known_fields.keys())
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


def _filter_inventory_dnp_entries(
    bom_data: BOMData,
    *,
    include_inventory_dnp: bool,
) -> BOMData:
    """Filter out inventory-DNP BOM rows unless explicitly included by CLI flags."""
    return _service_filter_inventory_dnp_entries(
        bom_data,
        include_inventory_dnp=include_inventory_dnp,
    )


def _entry_smd_from_reference_lookup(
    entry: BOMEntry, smd_by_reference: dict[str, bool]
) -> Optional[bool]:
    """Resolve an entry-level SMD boolean from per-reference PCB mount metadata."""
    return _service_entry_smd_from_reference_lookup(entry, smd_by_reference)


def _enrich_bom_smd_from_project_pcb(
    bom_data: BOMData,
    pcb_file: Optional[Path],
    *,
    verbose: bool = False,
) -> BOMData:
    """Populate missing BOM `smd` attributes from PCB mount metadata."""
    enriched_bom_data, diagnostics = _service_enrich_bom_smd_from_project_pcb(
        bom_data,
        pcb_file,
        verbose=verbose,
    )
    for diagnostic in diagnostics:
        print(diagnostic, file=sys.stderr)
    return enriched_bom_data


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


def _resolve_standard_field_value(
    entry: BOMEntry,
    field: str,
    *,
    fabricator_id: str,
    fabricator_config: Optional[FabricatorConfig],
) -> str:
    """Resolve a standard (non-prefixed) BOM field."""

    if field == "reference":
        return entry.references_string
    if field == "quantity":
        return str(entry.quantity)
    if field == "fabricator_part_number":
        return _resolve_fabricator_part_number(
            entry,
            fabricator_id=fabricator_id,
            fabricator_config=fabricator_config,
        )
    if field == "smd":
        return _resolve_smd_indicator(entry)

    row_sources = _build_bom_row_sources(entry, include_unqualified_fallback=True)
    if field == "mfgpn":
        return resolve_field(
            "manufacturer_part",
            row_sources,
            priority=_BOM_SOURCE_PRIORITY,
        ) or resolve_field(
            "mfgpn",
            row_sources,
            priority=_BOM_SOURCE_PRIORITY,
        )
    if field == "package":
        return resolve_field(
            "package",
            row_sources,
            priority=_BOM_SOURCE_PRIORITY,
        ) or derive_package_from_footprint(entry.footprint)
    if field == "lcsc":
        return resolve_field(
            "lcsc",
            row_sources,
            priority=_BOM_SOURCE_PRIORITY,
        ) or _get_attribute_value(entry, "LCSC")
    resolved_value = resolve_field(
        field,
        row_sources,
        priority=_BOM_SOURCE_PRIORITY,
    )
    if resolved_value:
        return resolved_value

    return _get_attribute_value(entry, field)


def _resolve_namespaced_field_value(
    entry: BOMEntry,
    namespace: str,
    namespaced_field: str,
    *,
    fabricator_id: str,
    fabricator_config: Optional[FabricatorConfig],
) -> str:
    """Resolve a namespace-qualified field under strict source semantics."""

    row_sources = _build_bom_row_sources(entry, include_unqualified_fallback=False)
    return resolve_field(
        f"{namespace}:{namespaced_field}",
        row_sources,
        priority=_BOM_SOURCE_PRIORITY,
    )


def _build_bom_row_sources(
    entry: BOMEntry,
    *,
    include_unqualified_fallback: bool,
) -> dict[str, dict[str, object]]:
    """Build source field maps for one BOM row (`s`, `p`, `i`)."""

    row_sources: dict[str, dict[str, object]] = {"s": {}, "p": {}, "i": {}}
    for attr_key, attr_value in entry.attributes.items():
        normalized_key = normalize_field_name(str(attr_key or ""))
        prefix, separator, remainder = normalized_key.partition(":")
        if separator and prefix in {"s", "p", "i"} and remainder:
            row_sources[prefix][remainder] = attr_value

    if include_unqualified_fallback:
        # Keep unqualified behavior stable when merge enrichment is absent.
        if entry.value:
            row_sources["s"].setdefault("value", entry.value)
        if entry.footprint:
            row_sources["s"].setdefault("footprint", entry.footprint)
        package_value = _get_attribute_value(entry, "package")
        if package_value:
            row_sources["s"].setdefault("package", package_value)

    return row_sources


def _entry_has_namespaced_field(entry: BOMEntry, namespaced_field: str) -> bool:
    """Return True when an entry explicitly carries a given namespaced field."""

    normalized_target = normalize_field_name(namespaced_field)
    for attribute_key in entry.attributes.keys():
        normalized_key = normalize_field_name(str(attribute_key or ""))
        if normalized_key == normalized_target:
            return True
    return False


def _resolve_entry_device_footprint(entry: BOMEntry) -> str:
    """Resolve the concrete device footprint for BOM/device workflows.

    Precedence is intentionally physical-first:
    1) Explicit PCB-resolved footprint (`p:footprint`) is authoritative
    2) If PCB footprint is absent, fall back to schematic footprint (`s:footprint`)
       then entry footprint
    """

    row_sources = _build_bom_row_sources(entry, include_unqualified_fallback=True)
    has_pcb_footprint = _entry_has_namespaced_field(entry, "p:footprint")

    pcb_footprint = resolve_field(
        "p:footprint",
        row_sources,
        priority=_BOM_SOURCE_PRIORITY,
    )
    if has_pcb_footprint:
        return str(pcb_footprint or "").strip()

    schematic_footprint = resolve_field(
        "s:footprint",
        row_sources,
        priority=_BOM_SOURCE_PRIORITY,
    )

    fallback_footprint = str(entry.footprint or "").strip()
    for candidate in (schematic_footprint, fallback_footprint):
        if _is_concrete_footprint(candidate):
            return str(candidate).strip()
    for candidate in (schematic_footprint, fallback_footprint):
        normalized_candidate = str(candidate or "").strip()
        if normalized_candidate:
            return normalized_candidate

    return ""


def _is_concrete_footprint(value: str) -> bool:
    """Return True when a footprint token is concrete enough for BOM devices."""

    token = str(value or "").strip()
    if not token or token == "~":
        return False
    if "*" in token or "?" in token:
        return False
    return True


def _enforce_bom_device_footprints(bom_data: BOMData) -> BOMData:
    """Enforce concrete footprint availability for BOM/device generation.

    For BOM workflows, a tangible device footprint is mandatory.
    - resolves entry footprint with PCB precedence (`p:footprint` over schematic)
    - raises ValueError when a concrete footprint cannot be resolved
    """
    return _service_enforce_bom_device_footprints(bom_data)


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

    if not lines:
        return ""

    unique_lines: list[tuple[str, str]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for namespace_value in lines:
        if namespace_value in seen_pairs:
            continue
        seen_pairs.add(namespace_value)
        unique_lines.append(namespace_value)

    return "\n".join(f"{namespace}:{value}" for namespace, value in unique_lines)


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
    import logging

    # Handle k: modifier — KiCad LIBRARY:NAME → NAME (strip library nickname).
    # "k:footprint" defaults to inventory source; use "i:k:", "s:k:", "p:k:" explicitly.
    kicad_parts = split_kicad_strip_field(field)
    if kicad_parts is not None:
        source, inner = kicad_parts
        if field.startswith("k:"):
            logging.getLogger(__name__).debug(
                "k:%s: no source prefix specified, defaulting to i: (inventory). "
                "Use i:k:, s:k:, or p:k: to be explicit.",
                inner,
            )
        raw = _resolve_namespaced_field_value(
            entry,
            source,
            inner,
            fabricator_id=fabricator_id,
            fabricator_config=fabricator_config,
        )
        return derive_package_from_footprint(raw)

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
