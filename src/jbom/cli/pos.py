"""POS (Position) command - generate component placement files."""

import argparse
import csv
import os
import sys
from pathlib import Path
from typing import Any, Optional, TextIO

from jbom.application.jobs.contracts import (
    JobArtifact,
    JobContext,
    JobDiagnosticSeverity,
    JobOutcome,
    JobRequest,
)
from jbom.application.jobs.runner import JobEventStream, JobRunPayload, JobRunner
from jbom.application.pos_workflow import (
    POSFieldListingPayload,
    POSRequest,
    POSWorkflow,
    apply_pos_dnp_filter as _service_apply_pos_dnp_filter,
    enrich_pos_with_merge_namespaces as _service_enrich_pos_with_merge_namespaces,
    resolve_pos_output_projection as _service_resolve_pos_output_projection,
)
from jbom.cli.formatting import Column, get_terminal_width, print_table
from jbom.cli.output import (
    OutputDestination,
    OutputKind,
    OutputRefusedError,
    add_force_argument,
    open_output_text_file,
    resolve_output_destination,
)
from jbom.common.cli_fabricator import (
    add_fabricator_arguments,
    resolve_fabricator_from_args,
)
from jbom.common.component_filters import add_component_filter_arguments
from jbom.common.component_utils import derive_package_from_footprint
from jbom.common.fields import normalize_field_name, split_kicad_strip_field
from jbom.config.fabricators import FabricatorConfig
from jbom.services.fabricator_projection_service import FabricatorProjectionService
from jbom.services.field_listing_service import FieldListingService, resolve_field

_NUMERIC_POS_FIELDS: frozenset[str] = frozenset({"x", "y", "rotation"})
_POS_SOURCE_PRIORITY = "pis"
_MAX_POS_CONSOLE_COLUMN_WIDTH = 50


def _enrich_pos_with_merge_namespaces(
    pos_data: list[dict[str, Any]],
    merge_result: Any,
) -> list[dict[str, Any]]:
    """Compatibility wrapper for legacy CLI helper imports in tests."""

    return _service_enrich_pos_with_merge_namespaces(pos_data, merge_result)


def _apply_pos_dnp_filter(
    pos_data: list[dict[str, Any]],
    *,
    component_filters: dict[str, Any],
) -> list[dict[str, Any]]:
    """Compatibility wrapper for legacy CLI helper imports in tests."""

    include_dnp = not component_filters.get("exclude_dnp", True)
    return _service_apply_pos_dnp_filter(pos_data, include_dnp=include_dnp)


def _resolve_pos_output_projection(
    *,
    selected_fields: list[str] | None,
    fabricator: str,
    user_specified_fields: bool,
    projection_service: FabricatorProjectionService | None = None,
) -> tuple[list[str], list[str], Optional[FabricatorConfig]]:
    """Compatibility wrapper for POS projection tests."""

    return _service_resolve_pos_output_projection(
        selected_fields=selected_fields,
        fabricator=fabricator,
        user_specified_fields=user_specified_fields,
        projection_service=projection_service,
    )


def register_command(subparsers) -> None:
    """Register pos command with argument parser."""
    parser = subparsers.add_parser(
        "pos", help="Generate component placement files from KiCad PCB"
    )

    parser.add_argument(
        "input",
        nargs="?",
        default=".",
        help="Path to .kicad_pcb file, project directory, or base name (default: current directory)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help='Output destination: omit for default file output, use "console" for table, "-" for CSV to stdout, or a file path',
    )
    add_force_argument(parser)

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
    parser.add_argument(
        "--units",
        choices=["mm"],
        default="mm",
        help="Units for POS output (mm only)",
    )
    parser.add_argument(
        "--origin",
        choices=["board", "aux"],
        default="board",
        help="Origin reference (default: board)",
    )
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
    add_component_filter_arguments(parser, command_type="pos")
    add_fabricator_arguments(parser)
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.set_defaults(handler=handle_pos)


def _predict_pos_artifacts(args: argparse.Namespace) -> tuple[JobArtifact, ...]:
    """Predict adapter-level POS artifact descriptors from CLI output arguments."""

    output = str(args.output or "").strip()
    if output.lower() == "console":
        return ()
    if output == "-":
        return (
            JobArtifact(
                name="pos.csv",
                location="stdout://pos.csv",
                media_type="text/csv",
            ),
        )
    if output:
        output_path = Path(output)
        return (
            JobArtifact(
                name=output_path.name or "pos.csv",
                location=str(output_path),
                media_type="text/csv",
            ),
        )
    return (
        JobArtifact(
            name="pos.csv",
            location="project-default://pos.csv",
            media_type="text/csv",
        ),
    )


def _build_pos_job_request(args: argparse.Namespace) -> JobRequest:
    """Build adapter-neutral `JobRequest` contract for POS execution."""

    options: dict[str, object] = {
        "input": str(args.input or "."),
        "output": str(args.output or ""),
        "fabricator": resolve_fabricator_from_args(args),
        "smd_only": bool(args.smd_only),
        "layer": str(args.layer or ""),
        "origin": str(args.origin or "board"),
        "verbose": bool(args.verbose),
        "list_fields": bool(args.list_fields),
        "include_dnp": bool(getattr(args, "include_dnp", False)),
    }
    return JobRequest(
        job_type="pos",
        intent="generate_pos",
        project_ref=str(args.input or "."),
        options=options,
        metadata={"adapter": "cli"},
    )


def _build_pos_request(
    args: argparse.Namespace,
) -> POSRequest:
    """Map CLI args to an adapter-neutral POS orchestration request."""

    return POSRequest(
        input_path=str(args.input or "."),
        output=str(args.output or ""),
        fabricator=resolve_fabricator_from_args(args),
        smd_only=bool(args.smd_only),
        layer=str(args.layer or ""),
        origin=str(args.origin or "board"),
        fields=args.fields if args.fields is not None else None,
        list_fields=bool(args.list_fields),
        include_dnp=bool(getattr(args, "include_dnp", False)),
        verbose=bool(args.verbose),
        quiet=bool(os.environ.get("JBOM_QUIET")),
    )


def _emit_cli_diagnostic(message: str) -> None:
    """Render one orchestration diagnostic message to stderr."""

    print(message, file=sys.stderr)


def handle_pos(args: argparse.Namespace) -> int:
    """Handle POS command through the shared adapter-neutral job runner."""

    request = _build_pos_job_request(args)
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
            message="Resolving project input and POS orchestration plan",
        )
        exit_code = _execute_pos_command(args)
        if exit_code == 0:
            events.progress(
                phase="emit",
                message="POS output emitted",
            )
        else:
            events.diagnostic(
                severity=JobDiagnosticSeverity.ERROR,
                message="POS command execution failed",
                code="pos_execution_failed",
                details={"exit_code": exit_code},
            )
        return JobRunPayload(
            outcome=JobOutcome.SUCCEEDED if exit_code == 0 else JobOutcome.FAILED,
            artifacts=_predict_pos_artifacts(args) if exit_code == 0 else (),
            metadata={
                "exit_code": exit_code,
                "command": "pos",
                "fabricator": request.options.get("fabricator", "generic"),
            },
        )

    result = runner.run(request=request, context=context, execute=_execute)
    if result.outcome == JobOutcome.CANCELLED:
        return 130
    return int(result.metadata.get("exit_code", 1))


def _execute_pos_command(args: argparse.Namespace) -> int:
    """Execute POS command via application-layer orchestration service."""

    orchestration_service = POSWorkflow()
    pos_request = _build_pos_request(args)
    try:
        result = orchestration_service.run(pos_request)
        for diagnostic in result.diagnostics:
            _emit_cli_diagnostic(diagnostic)
        if result.field_listing is not None:
            _list_available_pos_fields(
                pos_request.fabricator,
                field_listing=result.field_listing,
            )
            return 0
        if result.generation is None:
            raise ValueError("POS orchestration produced no generation payload")

        output_payload = result.generation
        return _output_pos(
            list(output_payload.pos_data),
            args.output,
            selected_fields=list(output_payload.selected_fields),
            headers=list(output_payload.headers),
            fabricator=output_payload.fabricator,
            fabricator_config=output_payload.fabricator_config,
            default_output_path=output_payload.default_output_path,
            force=args.force,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _list_available_pos_fields(
    fabricator: str,
    *,
    field_listing: POSFieldListingPayload,
) -> None:
    """Render POS known fields and defaults in CLI format."""

    matrix_rows = FieldListingService().build_namespace_matrix(
        field_listing.known_fields.keys()
    )
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

    if field_listing.default_fields:
        print(
            f"\nDefault fields for {fabricator} fabricator (when --fields not specified):"
        )
        print(f"  {', '.join(field_listing.default_fields)}")


def _output_pos(
    pos_data: list,
    output: str | None,
    *,
    selected_fields: list[str],
    headers: list[str],
    fabricator: str,
    fabricator_config: Optional[FabricatorConfig],
    default_output_path: Path,
    force: bool,
) -> int:
    """Output position data in the requested adapter format."""

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
        ) as file_handle:
            _print_csv(
                pos_data,
                selected_fields,
                headers,
                out=file_handle,
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
                field_name,
                fabricator_id=fabricator_id,
                fabricator_config=fabricator_config,
            )
            for field_name, h in zip(selected_fields, headers)
        }
        for entry in pos_data
    ]
    columns = _build_pos_console_columns(
        selected_fields=selected_fields,
        headers=headers,
        rows=rows,
    )
    print_table(rows, columns, terminal_width=get_terminal_width())
    print(f"\nTotal: {len(pos_data)} components")


def _build_pos_console_columns(
    *,
    selected_fields: list[str],
    headers: list[str],
    rows: list[dict[str, str]],
) -> list[Column]:
    """Build POS console columns with data-aware preferred widths."""

    columns: list[Column] = []
    last_column_index = len(headers) - 1
    for column_index, (field_name, header) in enumerate(zip(selected_fields, headers)):
        max_value_width = max(
            (len(str(row.get(header, ""))) for row in rows), default=0
        )
        preferred_width = max(
            len(header),
            min(max_value_width, _MAX_POS_CONSOLE_COLUMN_WIDTH),
        )
        if column_index == last_column_index:
            preferred_width += 1
        columns.append(
            Column(
                header=header,
                key=header,
                preferred_width=preferred_width,
                wrap=False,
                align="right" if field_name in _NUMERIC_POS_FIELDS else "left",
            )
        )
    return columns


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

    writer = csv.writer(out, quoting=csv.QUOTE_ALL)
    writer.writerow(headers)
    for entry in pos_data:
        row = []
        for field_name in selected_fields:
            value = _get_pos_field_value(
                entry,
                field_name,
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
    """Extract field value from POS entry."""
    import logging

    row_sources = _build_pos_row_sources(entry)

    kicad_parts = split_kicad_strip_field(field)
    if kicad_parts is not None:
        source, inner = kicad_parts
        if field.startswith("k:"):
            logging.getLogger(__name__).debug(
                "k:%s: no source prefix specified, defaulting to i: (inventory). "
                "Use i:k:, s:k:, or p:k: to be explicit.",
                inner,
            )
        raw = resolve_field(
            f"{source}:{inner}", row_sources, priority=_POS_SOURCE_PRIORITY
        )
        return derive_package_from_footprint(raw)

    namespace_prefix, separator, _ = field.partition(":")
    if separator and namespace_prefix in {"s", "p", "i"}:
        return resolve_field(field, row_sources, priority=_POS_SOURCE_PRIORITY)
    if separator and namespace_prefix == "a":
        return str(entry.get(field, "") or "")

    if field == "x":
        if entry.get("x_raw"):
            return str(entry["x_raw"])
        return f"{entry['x_mm']:.4f}"
    if field == "y":
        if entry.get("y_raw"):
            return str(entry["y_raw"])
        return f"{entry['y_mm']:.4f}"
    if field == "rotation":
        if entry.get("rotation_raw") is not None:
            return str(entry["rotation_raw"])
        return f"{entry['rotation']:.1f}"

    if field == "fabricator_part_number":
        return _resolve_fabricator_part_number(
            entry,
            fabricator_id=fabricator_id,
            fabricator_config=fabricator_config,
        )

    field_mapping = {
        "reference": "reference",
        "side": "side",
    }
    if field in field_mapping:
        return str(entry.get(field_mapping[field], ""))
    if field in {"value", "footprint", "package"}:
        return resolve_field(
            field,
            row_sources,
            priority=_POS_SOURCE_PRIORITY,
        )
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
