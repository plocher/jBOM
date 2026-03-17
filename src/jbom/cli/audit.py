"""audit command — field quality checks and inventory coverage analysis.

Usage
-----
Project mode (positionals resolve to KiCad project directories or schematics)::

    jbom audit <proj> [<proj> ...]  \
        [--inventory cat.csv]       \
        [-o report.csv]             \
        [--strict]

Inventory mode (positionals are ``.csv`` files)::

    jbom audit <cat.csv> [<cat.csv> ...]  \
        [--requirements req.csv]           \
        [-o report.csv]                    \
        [--strict]

Mode is detected automatically: if every positional argument ends with
``.csv`` the command operates in inventory mode; otherwise it operates in
project mode.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any

from jbom.cli.formatting import Column, print_table
from jbom.cli.output import OutputDestination, OutputKind, resolve_output_destination
from jbom.common.component_classification import get_component_type
from jbom.common.component_filters import apply_component_filters
from jbom.common.field_taxonomy import get_required_fields
from jbom.common.package_matching import extract_package_from_footprint
from jbom.config.defaults import DefaultsConfig, get_defaults
from jbom.services.audit_service import (
    REPORT_CSV_COLUMNS,
    AuditRow,
    AuditService,
    CheckType,
    Severity,
    _EXACT_THRESHOLD as _AUDIT_MATCH_EXACT_THRESHOLD,
)
from jbom.services.audit_service import _resolve_project as _resolve_project_for_cli
from jbom.services.schematic_reader import SchematicReader
from jbom.services.search.inventory_search_service import InventorySearchService

_PROJECT_REPORT_BASE_COLUMNS: list[str] = [
    "RowType",
    "ProjectPath",
    "RefDes",
    "UUID",
    "Category",
]
_PROJECT_REPORT_CONTEXT_COLUMNS: list[str] = [
    "Value",
    "Footprint",
    "Package",
    "Description",
    "LCSC",
]

_PROJECT_REPORT_TRAILING_COLUMNS: list[str] = [
    "Action",
    "Notes",
]
_PROJECT_REPORT_VERBOSE_COLUMNS: list[str] = ["Debug"]
_PROJECT_SUPPLY_CHAIN_FIELDS: set[str] = {
    "Manufacturer",
    "MFGPN",
}
_PROJECT_SUGGESTED_ACTION = "SKIP/SET"
_PROJECT_MISSING_VALUE = "MISSING"
_PROJECT_HEURISTIC_VALUE = "HEURISTIC"
_PROJECT_MATCH_EXACT_THRESHOLD = _AUDIT_MATCH_EXACT_THRESHOLD
_PROJECT_EM_MATCH_EXACT = "EM_EXACT"
_PROJECT_EM_MATCH_HEURISTIC = "EM_HEURISTIC"
_PROJECT_EM_MATCH_NEEDS_CLUE = "EM_NEEDS_CLUE"
_PROJECT_SUPPLIER_NOT_REQUESTED = "NOT_REQUESTED"
_PROJECT_SUPPLIER_EXACT_SPN = "SUPPLIER_EXACT_SPN"
_PROJECT_SUPPLIER_MPN_CANDIDATE = "SUPPLIER_MPN_CANDIDATE"
_PROJECT_SUPPLIER_NEEDS_CLUE = "SUPPLIER_NEEDS_CLUE"
_PROJECT_EM_BASIS_SUFFICIENT = "EM attributes sufficient"
_PROJECT_EM_BASIS_HEURISTIC = "EM attributes + heuristics sufficient"
_PROJECT_EM_BASIS_INSUFFICIENT = "EM attributes + heuristics insufficient"
_PROJECT_SUPPLIER_BASIS_NOT_REQUESTED = "Supplier pass not requested"
_PROJECT_SUPPLIER_BASIS_SPN = "Supplier SPN present (overrides EM ambiguity)"
_PROJECT_SUPPLIER_BASIS_MPN = "MPN provided (supplier candidate override)"
_PROJECT_SUPPLIER_BASIS_NEEDS_CLUE = "Supplier anchor missing (need SPN or MPN)"
_PROJECT_REQUIRED_FIELDS: tuple[str, ...] = tuple(
    spec.name for spec in get_required_fields()
)
_PROJECT_RES_CATEGORY = "RES"
_PROJECT_CAP_CATEGORY = "CAP"
_PROJECT_LED_CATEGORY = "LED"
_PROJECT_LED_COLOR_WAVELENGTH_RULES: tuple[tuple[frozenset[str], str], ...] = (
    (frozenset({"ULTRAVIOLET", "UV"}), "<380nm"),
    (frozenset({"VIOLET", "PURPLE"}), "370-450nm"),
    (frozenset({"BLUE"}), "450-495nm"),
    (frozenset({"CYAN", "AQUA"}), "495-520nm"),
    (frozenset({"GREEN"}), "495-570nm"),
    (frozenset({"YELLOW", "AMBER"}), "570-595nm"),
    (frozenset({"ORANGE"}), "590-620nm"),
    (frozenset({"RED"}), "620-750nm"),
    (frozenset({"INFRARED", "IR"}), ">750nm (typ. 850-940nm)"),
    (frozenset({"WHITE"}), "400-700nm"),
)
_PROJECT_LED_NAMED_COLOR_WAVELENGTH_RULES: tuple[tuple[frozenset[str], str], ...] = (
    (frozenset({"RAILROAD", "GREEN"}), "505-508nm"),
    (frozenset({"RAILROAD", "RED"}), "627-635nm"),
    (frozenset({"RAILROAD", "YELLOW"}), "589-599nm"),
    (frozenset({"LUNAR", "WHITE"}), "400-700nm (cool white, CCT 3250-5600K)"),
)
_AUDIT_CONSOLE_WRAP_FIELDS: frozenset[str] = frozenset(
    {"Description", "Notes", "ProjectPath"}
)
_AUDIT_CONSOLE_FIELD_WIDTHS: dict[str, int] = {
    "RowType": 10,
    "CheckType": 16,
    "Severity": 8,
    "RefDes": 8,
    "UUID": 14,
    "Category": 10,
    "Field": 12,
    "CurrentValue": 16,
    "SuggestedValue": 16,
    "Action": 8,
    "Supplier": 10,
    "SupplierPN": 14,
    "Value": 12,
    "Footprint": 18,
    "Package": 12,
    "Description": 28,
    "Notes": 28,
}


def register_command(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    """Register the audit sub-command with the top-level argument parser."""

    parser = subparsers.add_parser(
        "audit",
        help="Audit component fields and inventory coverage",
        description=(
            "Diagnose field-quality issues and inventory coverage gaps.\n\n"
            "PROJECT MODE  — pass KiCad project directories or schematic files.\n"
            "INVENTORY MODE — pass inventory CSV files (mode detected automatically)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "inputs",
        nargs="*",
        default=["."],
        metavar="PATH",
        help=(
            "One or more KiCad project directories (project mode) "
            "or inventory CSV files (inventory mode). Defaults to current directory."
        ),
    )

    # Project mode option
    parser.add_argument(
        "--inventory",
        metavar="CATALOG_CSV",
        type=Path,
        default=None,
        help=(
            "Inventory catalog CSV for coverage dry-run "
            "(project mode only; triggers COVERAGE_GAP / MATCH_* rows)"
        ),
    )

    # Inventory mode option
    parser.add_argument(
        "--requirements",
        metavar="REQ_CSV",
        type=Path,
        default=None,
        help=(
            "Requirements CSV (output of 'jbom inventory proj') for coverage check "
            "(inventory mode only; triggers COVERAGE_GAP / UNUSED_ITEM rows)"
        ),
    )

    parser.add_argument(
        "-o",
        "--output",
        metavar="DEST",
        default=None,
        help=(
            "Output destination: omit for CSV to stdout, use 'console' for table output, "
            "'-' for CSV to stdout, or a file path"
        ),
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with non-zero status when WARN-severity rows exist (default: only on ERROR)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Include debug diagnostics in project output (may be repeated)",
    )

    # Supplier validation options (optional; require live API access)
    parser.add_argument(
        "--supplier",
        metavar="SUPPLIER_ID",
        default=None,
        help=(
            "Supplier ID to validate component sourcing against (e.g. 'mouser', 'lcsc'). "
            "Emits SUPPLIER_MISS rows for components not found. "
            "Emits INVENTORY_GAP rows (INFO) when combined with --inventory/--requirements."
        ),
    )

    parser.add_argument(
        "--api-key",
        metavar="KEY",
        default=None,
        help="API key for the supplier search provider (overrides env vars)",
    )

    parser.set_defaults(handler=handle_audit)


def handle_audit(args: argparse.Namespace) -> int:
    """Handle the ``jbom audit`` command.

    Returns:
        Exit code: 0 on success (no ERROR/WARN depending on ``--strict``), 1 otherwise.
    """
    try:
        inputs = [Path(p) for p in args.inputs]

        # Mode detection: all .csv → inventory mode; anything else → project mode.
        if all(p.suffix.lower() == ".csv" for p in inputs):
            return _run_inventory_mode(args, inputs)
        return _run_project_mode(args, inputs)

    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _run_project_mode(args: argparse.Namespace, inputs: list[Path]) -> int:
    """Execute audit in project mode."""
    if args.requirements is not None:
        print(
            "Error: --requirements is only valid in inventory mode "
            "(positional arguments must be .csv files for inventory mode)",
            file=sys.stderr,
        )
        return 1

    supplier_service, supplier_id = _build_supplier_service(args)

    service = AuditService()
    report = service.audit_project(
        project_paths=inputs,
        inventory_path=getattr(args, "inventory", None),
        supplier_service=supplier_service,
        supplier_id=supplier_id,
    )
    component_context = _collect_project_component_contexts(inputs)
    visible_counts = _write_project_report(
        args,
        report,
        component_context=component_context,
        supplier_id=supplier_id,
    )
    _print_summary(report, counts_override=visible_counts)

    return report.exit_code_strict() if args.strict else report.exit_code


def _run_inventory_mode(args: argparse.Namespace, inputs: list[Path]) -> int:
    """Execute audit in inventory mode."""
    if args.inventory is not None:
        print(
            "Error: --inventory is only valid in project mode "
            "(pass KiCad project directories for project mode)",
            file=sys.stderr,
        )
        return 1

    supplier_service, supplier_id = _build_supplier_service(args)

    service = AuditService()
    report = service.audit_inventory(
        catalog_paths=inputs,
        requirements_path=getattr(args, "requirements", None),
        supplier_service=supplier_service,
        supplier_id=supplier_id,
    )

    _write_inventory_report(args, report)
    _print_summary(report)

    return report.exit_code_strict() if args.strict else report.exit_code


def _build_supplier_service(
    args: argparse.Namespace,
) -> tuple[InventorySearchService | None, str]:
    """Build a supplier search service from CLI args, or return (None, '')."""
    supplier_id = (getattr(args, "supplier", None) or "").strip().lower()
    if not supplier_id:
        return None, ""

    api_key = getattr(args, "api_key", None)

    from jbom.services.search.provider_factory import create_search_provider

    provider = create_search_provider(
        supplier_id,
        api_key=api_key,
        cache=None,  # default DiskSearchCache
    )
    service = InventorySearchService(provider, request_delay_seconds=0.2)
    return service, supplier_id


def _write_project_report(
    args: argparse.Namespace,
    report: Any,
    *,
    component_context: dict[tuple[str, str, str, str], dict[str, str]],
    supplier_id: str,
) -> tuple[int, int, int]:
    """Write project-mode report as wide CURRENT/SUGGESTED couplets."""
    visible_counts = _count_visible_project_findings(
        report.rows,
        component_context=component_context,
        supplier_id=supplier_id,
    )
    fieldnames, rows = _build_project_couplet_rows(
        report.rows,
        component_context=component_context,
        supplier_id=supplier_id,
        verbose_level=int(getattr(args, "verbose", 0) or 0),
    )
    destination = _resolve_audit_output_destination(getattr(args, "output", None))

    if destination.kind == OutputKind.CONSOLE:
        _print_audit_console_table(
            rows,
            fieldnames,
            title="Audit report (project mode)",
        )
        return visible_counts
    if destination.kind == OutputKind.STDOUT:
        buf = io.StringIO()
        _write_csv_rows(buf, fieldnames, rows)
        print(buf.getvalue(), end="")
        return visible_counts

    if not destination.path:
        raise ValueError("Internal error: file output selected but no path provided")

    with destination.path.open("w", encoding="utf-8", newline="") as handle:
        _write_csv_rows(handle, fieldnames, rows)
    print(f"Audit report written to {destination.path}", file=sys.stderr)
    return visible_counts


def _write_inventory_report(args: argparse.Namespace, report: Any) -> None:
    """Write inventory-mode report using the stable audit CSV schema."""
    destination = _resolve_audit_output_destination(getattr(args, "output", None))

    if destination.kind == OutputKind.CONSOLE:
        rows = [row.to_csv_row() for row in report.rows]
        _print_audit_console_table(
            rows,
            REPORT_CSV_COLUMNS,
            title="Audit report (inventory mode)",
        )
        return
    if destination.kind == OutputKind.STDOUT:
        buf = io.StringIO()
        report.write_csv(buf)
        print(buf.getvalue(), end="")
        return

    if not destination.path:
        raise ValueError("Internal error: file output selected but no path provided")

    with destination.path.open("w", encoding="utf-8", newline="") as handle:
        report.write_csv(handle)
    print(f"Audit report written to {destination.path}", file=sys.stderr)


def _resolve_audit_output_destination(output: str | Path | None) -> OutputDestination:
    """Resolve audit output destination using shared CLI output semantics."""
    raw_output = str(output) if output is not None else None
    return resolve_output_destination(
        raw_output,
        default_destination=OutputDestination(OutputKind.STDOUT),
    )


def _print_audit_console_table(
    rows: list[dict[str, str]],
    fieldnames: list[str],
    *,
    title: str,
) -> None:
    """Print audit rows as a human-readable console table."""
    if not rows:
        print(f"{title}: no rows")
        return

    normalized_rows: list[dict[str, str]] = [
        {
            field_name: _normalize_audit_console_cell(
                field_name,
                row.get(field_name, ""),
            )
            for field_name in fieldnames
        }
        for row in rows
    ]

    columns = [
        Column(
            header=field_name,
            key=field_name,
            preferred_width=_AUDIT_CONSOLE_FIELD_WIDTHS.get(field_name, 14),
            wrap=field_name in _AUDIT_CONSOLE_WRAP_FIELDS,
            align="left",
        )
        for field_name in fieldnames
    ]
    print_table(
        normalized_rows,
        columns,
        terminal_width=None,
        title=title,
    )
    print(f"\nTotal: {len(normalized_rows)} rows")


def _normalize_audit_console_cell(field_name: str, value: Any) -> str:
    """Normalize audit console table cell text for readability."""
    text = str(value or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = re.sub(r"[ \t]{2,}", " ", text)
    if field_name == "ProjectPath":
        text = _format_project_path_for_console(text)
    if text.startswith("CheckType."):
        return text.removeprefix("CheckType.")
    if text.startswith("Severity."):
        return text.removeprefix("Severity.")
    return text


def _format_project_path_for_console(project_path: str) -> str:
    """Render project paths compactly for console tables."""
    normalized = str(project_path or "").strip()
    if not normalized:
        return ""
    if not normalized.startswith("/"):
        return normalized

    display_path = Path(normalized)
    if display_path.suffix.lower() == ".kicad_pro":
        display_path = display_path.parent

    home_path = Path.home()
    if display_path == home_path:
        return "~"
    try:
        relative_to_home = display_path.relative_to(home_path)
    except ValueError:
        return str(display_path)
    return f"~/{relative_to_home}"


def _build_project_couplet_rows(
    report_rows: list[AuditRow],
    *,
    component_context: dict[tuple[str, str, str, str], dict[str, str]],
    supplier_id: str = "",
    verbose_level: int = 0,
) -> tuple[list[str], list[dict[str, str]]]:
    """Build wide CURRENT/SUGGESTED rows from tall QUALITY_ISSUE findings."""
    defaults = get_defaults()
    include_debug = verbose_level > 0
    supplier_identifier_fields = _resolve_supplier_identifier_fields(supplier_id)
    grouped: OrderedDict[tuple[str, str, str, str], dict[str, Any]] = OrderedDict()
    field_order: list[str] = []

    for row in report_rows:
        if row.check_type not in {CheckType.QUALITY_ISSUE, CheckType.MERGE_MISMATCH}:
            continue

        key = (row.project_path, row.ref_des, row.uuid, row.category)
        group = grouped.setdefault(
            key,
            {
                "current": {},
                "suggested": {},
                "missing_fields": [],
                "heuristic_suggestions": {},
                "mismatch_notes": [],
            },
        )

        if row.check_type == CheckType.QUALITY_ISSUE:
            field_name = (row.field or "").strip()
            if not field_name or field_name in _PROJECT_SUPPLY_CHAIN_FIELDS:
                continue

            if field_name not in field_order:
                field_order.append(field_name)
            if field_name not in group["missing_fields"]:
                group["missing_fields"].append(field_name)

            current_value = (row.current_value or "").strip()
            if field_name not in group["current"] and current_value:
                group["current"][field_name] = current_value
            group["suggested"][field_name] = _PROJECT_MISSING_VALUE
            continue

        if row.check_type == CheckType.MERGE_MISMATCH:
            mismatch_note = _format_merge_mismatch_note(row)
            if mismatch_note and mismatch_note not in group["mismatch_notes"]:
                group["mismatch_notes"].append(mismatch_note)

    fieldnames = (
        _PROJECT_REPORT_BASE_COLUMNS
        + _PROJECT_REPORT_CONTEXT_COLUMNS
        + (_PROJECT_REPORT_VERBOSE_COLUMNS if include_debug else [])
        + field_order
        + _PROJECT_REPORT_TRAILING_COLUMNS
    )
    if not grouped:
        return fieldnames, []

    output_rows: list[dict[str, str]] = []
    for (project_path, ref_des, uuid, category), group in grouped.items():
        current_row = {name: "" for name in fieldnames}
        suggested_row = {name: "" for name in fieldnames}

        current_row["RowType"] = "CURRENT"
        current_row["ProjectPath"] = project_path
        current_row["RefDes"] = ref_des
        current_row["UUID"] = uuid
        current_row["Category"] = category

        suggested_row["RowType"] = "SUGGESTED"
        suggested_row["ProjectPath"] = project_path
        suggested_row["RefDes"] = ref_des
        suggested_row["UUID"] = uuid
        suggested_row["Category"] = category
        context = component_context.get((project_path, ref_des, uuid, category), {})
        for context_col in _PROJECT_REPORT_CONTEXT_COLUMNS:
            context_value = context.get(context_col, "")
            current_row[context_col] = context_value
            suggested_row[context_col] = context_value

        for field_name in field_order:
            current_row[field_name] = group["current"].get(field_name, "")
            raw_suggested = group["suggested"].get(field_name, "")
            if raw_suggested:
                heuristic_suggestion = _resolve_project_default_suggestion(
                    category=category,
                    field_name=field_name,
                    context=context,
                    defaults=defaults,
                )
                group["heuristic_suggestions"][field_name] = heuristic_suggestion
                suggested_row[field_name] = _format_project_suggested_cell(
                    heuristic_suggestion
                )
            else:
                suggested_row[field_name] = raw_suggested

        em_matchability, _em_basis, em_debug = _classify_em_matchability(
            category=category,
            context=context,
            missing_fields=group["missing_fields"],
            suggested_row=suggested_row,
            include_debug=include_debug,
        )
        (
            supplier_matchability,
            _supplier_basis,
            supplier_debug,
        ) = _classify_supplier_matchability(
            context=context,
            supplier_id=supplier_id,
            supplier_identifier_fields=supplier_identifier_fields,
            include_debug=include_debug,
        )
        supplier_identifier_field = _resolve_supplier_identifier_field(
            context,
            supplier_identifier_fields=supplier_identifier_fields,
        )
        supplier_identifier_label = _resolve_supplier_identifier_label(
            supplier_id=supplier_id,
            supplier_identifier_field=supplier_identifier_field,
        )
        audit_summary = _build_project_audit_summary(
            ref_des=ref_des,
            missing_fields=group["missing_fields"],
            em_matchability=em_matchability,
            supplier_matchability=supplier_matchability,
            supplier_id=supplier_id,
            supplier_identifier_label=supplier_identifier_label,
        )
        if include_debug:
            debug_details = "; ".join(
                part for part in (em_debug, supplier_debug) if part
            )
            current_row["Debug"] = debug_details
            suggested_row["Debug"] = debug_details
        notes_segments = [audit_summary]
        if group["mismatch_notes"]:
            notes_segments.append(
                "Merge mismatch diagnostics: " + " | ".join(group["mismatch_notes"])
            )
        current_row["Notes"] = "; ".join(
            segment for segment in notes_segments if segment
        )
        suggested_row["Notes"] = ""
        current_row["Action"] = ""
        suggested_row["Action"] = _PROJECT_SUGGESTED_ACTION

        output_rows.extend([current_row, suggested_row])

    return fieldnames, output_rows


def _format_merge_mismatch_note(row: AuditRow) -> str:
    """Format a concise merge mismatch note for project couplet summaries."""

    field_name = (row.field or "").strip() or "field"
    source_summary = (row.current_value or "").strip()

    if source_summary:
        return f"{field_name} ({source_summary})"
    return field_name


def _build_project_audit_summary(
    *,
    ref_des: str,
    missing_fields: list[str],
    em_matchability: str,
    supplier_matchability: str,
    supplier_id: str,
    supplier_identifier_label: str,
) -> str:
    """Build designer-facing summary text for project-mode audit rows."""
    missing_required = [f for f in missing_fields if f in _PROJECT_REQUIRED_FIELDS]
    supplier_identifier_note = str(supplier_identifier_label or "").strip()

    if (
        missing_fields
        and not missing_required
        and supplier_identifier_note
        and supplier_matchability == _PROJECT_SUPPLIER_EXACT_SPN
    ):
        return f"{ref_des}: {supplier_identifier_note} used"
    if (
        missing_fields
        and not missing_required
        and supplier_matchability == _PROJECT_SUPPLIER_NOT_REQUESTED
        and em_matchability in {_PROJECT_EM_MATCH_EXACT, _PROJECT_EM_MATCH_HEURISTIC}
    ):
        return f"{ref_des}: heuristics are sufficient"

    notes_parts: list[str] = []
    if missing_fields:
        notes_parts.append(
            f"{ref_des}: Missing attributes: {', '.join(missing_fields)}"
        )
    if missing_required:
        notes_parts.append(
            f"Required fields still missing: {', '.join(missing_required)}"
        )
    else:
        notes_parts.append("Audit successful: all required fields have values")

    if em_matchability == _PROJECT_EM_MATCH_EXACT:
        notes_parts.append("EM matching clues are sufficient")
    elif em_matchability == _PROJECT_EM_MATCH_HEURISTIC:
        notes_parts.append("EM matching is sufficient with heuristics")
    else:
        notes_parts.append("EM matching needs stronger clues")

    supplier_tag = (supplier_id or "supplier").upper()
    if supplier_matchability == _PROJECT_SUPPLIER_EXACT_SPN:
        notes_parts.append(
            f"{supplier_tag} part number present; uniquely identifies this component"
        )
        notes_parts.append(
            "For other suppliers, required fields and heuristics should be sufficient"
        )
    elif supplier_matchability == _PROJECT_SUPPLIER_MPN_CANDIDATE:
        notes_parts.append("Supplier matching can use MPN as a candidate override")
    elif supplier_matchability == _PROJECT_SUPPLIER_NOT_REQUESTED:
        notes_parts.append(
            "For other suppliers, required fields and heuristics should be sufficient"
        )
    else:
        notes_parts.append("Supplier anchor missing (need SPN or MPN)")

    return "; ".join(notes_parts)


def _resolve_supplier_identifier_label(
    *, supplier_id: str, supplier_identifier_field: str
) -> str:
    """Resolve a human-readable supplier identifier label from supplier profile data."""
    if not str(supplier_identifier_field or "").strip():
        return ""

    sid = (supplier_id or "").strip().lower()
    if not sid:
        return "Supplier part number"
    try:
        from jbom.config.suppliers import resolve_supplier_by_id

        supplier = resolve_supplier_by_id(sid)
    except Exception:
        supplier = None
    if supplier is None:
        return "Supplier part number"
    display_name = str(supplier.inventory_column or "").strip()
    if not display_name:
        return "Supplier part number"
    return f"{display_name} part number"


def _format_project_suggested_cell(suggestion: str) -> str:
    """Format suggested cell text for missing-field rows."""
    normalized = str(suggestion or "").strip()
    if not _is_meaningful_match_value(normalized):
        return _PROJECT_MISSING_VALUE
    return f"{_PROJECT_HEURISTIC_VALUE}\n({normalized})"


def _resolve_project_default_suggestion(
    *,
    category: str,
    field_name: str,
    context: dict[str, str],
    defaults: DefaultsConfig,
) -> str:
    """Return a deterministic suggested value for a missing project audit field."""
    normalized_category = (category or "").strip().upper()
    normalized_field = (field_name or "").strip()
    package_code = _extract_context_package_code(context)

    if normalized_category == _PROJECT_RES_CATEGORY:
        if normalized_field == "Tolerance":
            suggestion = defaults.get_domain_default(
                "resistor", "tolerance", fallback=""
            ).strip()
            if suggestion:
                return suggestion
        if normalized_field == "Power" and package_code:
            suggestion = defaults.get_package_power(package_code).strip()
            if suggestion:
                return suggestion

    if normalized_category == _PROJECT_CAP_CATEGORY:
        if normalized_field == "Tolerance":
            suggestion = defaults.get_domain_default(
                "capacitor", "tolerance", fallback=""
            ).strip()
            if suggestion:
                return suggestion
        if normalized_field == "Voltage" and package_code:
            suggestion = defaults.get_package_voltage(package_code).strip()
            if suggestion:
                return suggestion
    if (
        normalized_category == _PROJECT_LED_CATEGORY
        and normalized_field == "Wavelength"
    ):
        suggestion = _resolve_led_wavelength_from_context(context)
        if suggestion:
            return suggestion

    return _PROJECT_MISSING_VALUE


def _classify_em_matchability(
    *,
    category: str,
    context: dict[str, str],
    missing_fields: list[str],
    suggested_row: dict[str, str],
    include_debug: bool,
) -> tuple[str, str, str]:
    """Classify EM-only matchability using matcher-aligned semantics."""
    current_score = _estimate_matcher_score_from_context(
        category=category, context=context
    )
    enriched_context = _build_matchability_enriched_context(
        context=context,
        missing_fields=missing_fields,
        suggested_row=suggested_row,
    )
    enriched_score = _estimate_matcher_score_from_context(
        category=category,
        context=enriched_context,
    )
    debug_text = (
        "em_debug:"
        f" current_score={current_score}, enriched_score={enriched_score},"
        f" exact_threshold={_PROJECT_MATCH_EXACT_THRESHOLD}"
    )

    if current_score >= _PROJECT_MATCH_EXACT_THRESHOLD:
        return (
            _PROJECT_EM_MATCH_EXACT,
            _PROJECT_EM_BASIS_SUFFICIENT,
            debug_text if include_debug else "",
        )

    if max(current_score, enriched_score) > 0:
        return (
            _PROJECT_EM_MATCH_HEURISTIC,
            _PROJECT_EM_BASIS_HEURISTIC,
            debug_text if include_debug else "",
        )

    return (
        _PROJECT_EM_MATCH_NEEDS_CLUE,
        _PROJECT_EM_BASIS_INSUFFICIENT,
        debug_text if include_debug else "",
    )


def _build_matchability_enriched_context(
    *,
    context: dict[str, str],
    missing_fields: list[str],
    suggested_row: dict[str, str],
) -> dict[str, str]:
    """Return context enriched with deterministic suggestions for matching."""
    enriched = dict(context)
    for field_name in missing_fields:
        suggested_value = str(suggested_row.get(field_name, "")).strip()
        if not _is_meaningful_match_value(suggested_value):
            continue
        current_value = str(enriched.get(field_name, "")).strip()
        if _is_meaningful_match_value(current_value):
            continue
        enriched[field_name] = suggested_value
    return enriched


def _estimate_matcher_score_from_context(
    *, category: str, context: dict[str, str]
) -> int:
    """Estimate jBOM matcher score from known component attributes."""
    score = 0
    normalized_category = (category or "").strip().upper()
    if normalized_category and normalized_category not in {"UNK", "UNKNOWN"}:
        score += 50

    if _is_meaningful_match_value(str(context.get("Value", ""))):
        score += 40

    if _extract_context_package_code(context):
        score += 30

    if _get_context_value(context, ("Tolerance",)):
        score += 15

    if _get_context_value(context, ("Voltage", "V")):
        score += 10

    if _get_context_value(context, ("Power", "Wattage", "W", "P")):
        score += 10

    return score


def _classify_supplier_matchability(
    *,
    context: dict[str, str],
    supplier_id: str,
    supplier_identifier_fields: list[str],
    include_debug: bool,
) -> tuple[str, str, str]:
    """Classify supplier-anchor readiness (SPN first, then MPN candidate)."""
    sid = (supplier_id or "").strip().lower()
    if not sid:
        return (
            _PROJECT_SUPPLIER_NOT_REQUESTED,
            _PROJECT_SUPPLIER_BASIS_NOT_REQUESTED,
            "supplier_debug: supplier pass disabled" if include_debug else "",
        )

    supplier_spn_field = _resolve_supplier_identifier_field(
        context,
        supplier_identifier_fields=supplier_identifier_fields,
    )
    if supplier_spn_field:
        return (
            _PROJECT_SUPPLIER_EXACT_SPN,
            _PROJECT_SUPPLIER_BASIS_SPN,
            ("supplier_debug:" f" supplier_id={sid}, spn_field={supplier_spn_field}")
            if include_debug
            else "",
        )

    mpn_value = _get_context_value(context, ("MFGPN", "MPN"))
    if mpn_value:
        manufacturer = _get_context_value(context, ("Manufacturer", "MFR", "Brand"))
        if manufacturer:
            return (
                _PROJECT_SUPPLIER_MPN_CANDIDATE,
                _PROJECT_SUPPLIER_BASIS_MPN,
                (
                    "supplier_debug:"
                    f" supplier_id={sid}, mpn={mpn_value}, manufacturer={manufacturer}"
                )
                if include_debug
                else "",
            )
        return (
            _PROJECT_SUPPLIER_MPN_CANDIDATE,
            _PROJECT_SUPPLIER_BASIS_MPN,
            (f"supplier_debug: supplier_id={sid}, mpn={mpn_value}, manufacturer=")
            if include_debug
            else "",
        )

    return (
        _PROJECT_SUPPLIER_NEEDS_CLUE,
        _PROJECT_SUPPLIER_BASIS_NEEDS_CLUE,
        f"supplier_debug: supplier_id={sid}, no_spn_or_mpn" if include_debug else "",
    )


def _resolve_supplier_identifier_field(
    context: dict[str, str],
    *,
    supplier_identifier_fields: list[str],
) -> str:
    """Return supplier SPN field name when supplier alias fields are present."""
    return _find_context_value(context, supplier_identifier_fields)


def _resolve_supplier_identifier_fields(supplier_id: str) -> list[str]:
    """Return candidate property names that represent supplier-specific identifiers."""
    sid = (supplier_id or "").strip().lower()
    if not sid:
        return []
    try:
        from jbom.config.suppliers import resolve_supplier_by_id

        supplier = resolve_supplier_by_id(sid)
    except Exception:
        supplier = None
    if supplier is None:
        return []
    fields: list[str] = [supplier.inventory_column]
    fields.extend(supplier.inventory_column_synonyms)
    seen: set[str] = set()
    deduped: list[str] = []
    for field_name in fields:
        normalized = field_name.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(field_name)
    return deduped


def _find_context_value(
    context: dict[str, str], field_names: tuple[str, ...] | list[str]
) -> str:
    """Find first present context key among *field_names* and return its key name."""
    normalized_context: dict[str, str] = {
        str(key or "").strip().lower(): str(value or "").strip()
        for key, value in context.items()
    }
    for field_name in field_names:
        normalized_name = field_name.strip().lower()
        if not normalized_name:
            continue
        value = normalized_context.get(normalized_name, "")
        if _is_meaningful_match_value(value):
            return field_name
    return ""


def _get_context_value(
    context: dict[str, str],
    field_names: tuple[str, ...] | list[str],
) -> str:
    """Return the first meaningful context value for any of the provided aliases."""
    normalized_context: dict[str, str] = {
        str(key or "").strip().lower(): str(value or "").strip()
        for key, value in context.items()
    }
    for field_name in field_names:
        normalized_name = field_name.strip().lower()
        if not normalized_name:
            continue
        value = normalized_context.get(normalized_name, "")
        if _is_meaningful_match_value(value):
            return value
    return ""


def _is_meaningful_match_value(value: str) -> bool:
    """Return True when a value is useful as a matching clue."""
    normalized = str(value or "").strip()
    if not normalized:
        return False
    return normalized.upper() not in {"~", _PROJECT_MISSING_VALUE}


def _resolve_led_wavelength_from_context(context: dict[str, str]) -> str:
    """Infer LED wavelength range from color cues in Value/Type/Description."""
    search_blob = " ".join(
        [
            str(context.get("Value", "")).strip(),
            str(context.get("Type", "")).strip(),
            str(context.get("Description", "")).strip(),
        ]
    ).upper()
    if not search_blob:
        return ""
    tokens = {token for token in re.split(r"[^A-Z0-9]+", search_blob) if token}
    for required_tokens, wavelength in _PROJECT_LED_NAMED_COLOR_WAVELENGTH_RULES:
        if required_tokens.issubset(tokens):
            return wavelength
    for color_tokens, wavelength in _PROJECT_LED_COLOR_WAVELENGTH_RULES:
        if tokens.intersection(color_tokens):
            return wavelength
    return ""


def _extract_context_package_code(context: dict[str, str]) -> str:
    """Extract a normalized package code from component context fields."""
    footprint = (context.get("Footprint") or "").strip()
    package_from_footprint = extract_package_from_footprint(footprint)
    if package_from_footprint:
        return package_from_footprint.upper()

    raw_package = (context.get("Package") or "").strip()
    if not raw_package:
        return ""
    if raw_package.isdigit() and len(raw_package) == 3:
        return f"0{raw_package}"
    return raw_package.upper()


def _collect_project_component_contexts(
    project_paths: list[Path],
) -> dict[tuple[str, str, str, str], dict[str, str]]:
    """Collect per-component context values for project couplet output."""
    contexts: dict[tuple[str, str, str, str], dict[str, str]] = {}
    reader = SchematicReader()

    for project_path in project_paths:
        try:
            resolved_pro, schematic_files = _resolve_project_for_cli(project_path)
        except (FileNotFoundError, ValueError):
            # Context enrichment is best-effort; unresolved paths should not
            # block report generation from already-computed audit rows.
            continue
        pro_str = str(resolved_pro)
        for schematic_file in schematic_files:
            raw_components = reader.load_components(schematic_file)
            components = apply_component_filters(
                raw_components,
                {
                    "exclude_dnp": True,
                    "include_only_bom": True,
                    "include_virtual_symbols": False,
                },
            )
            for comp in components:
                category = (
                    get_component_type(comp.lib_id, comp.footprint, comp.reference)
                    or ""
                )
                props = comp.properties or {}
                key = (pro_str, comp.reference, comp.uuid, category)
                context_values: dict[str, str] = {
                    "Value": comp.value or "",
                    "Footprint": comp.footprint or "",
                    "Package": (props.get("Package") or "").strip(),
                    "Description": (props.get("Description") or "").strip(),
                }
                for prop_name, prop_value in props.items():
                    normalized_name = str(prop_name or "").strip()
                    normalized_value = str(prop_value or "").strip()
                    if not normalized_name or not normalized_value:
                        continue
                    context_values[normalized_name] = normalized_value
                contexts[key] = context_values

    return contexts


def _write_csv_rows(
    handle: io.TextIOBase | io.StringIO,
    fieldnames: list[str],
    rows: list[dict[str, str]],
) -> None:
    """Write CSV rows using QUOTE_ALL for spreadsheet-safe text rendering."""
    writer = csv.DictWriter(handle, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)


def _count_visible_project_findings(
    report_rows: list[AuditRow],
    *,
    component_context: dict[tuple[str, str, str, str], dict[str, str]],
    supplier_id: str,
) -> tuple[int, int, int]:
    """Count severities for findings that are rendered in project couplet output."""
    defaults = get_defaults()
    error_count = 0
    warn_count = 0
    info_count = 0
    grouped_best_practice: OrderedDict[
        tuple[str, str, str, str], dict[str, Any]
    ] = OrderedDict()
    for row in report_rows:
        if row.check_type == CheckType.QUALITY_ISSUE:
            field_name = (row.field or "").strip()
            if not field_name or field_name in _PROJECT_SUPPLY_CHAIN_FIELDS:
                continue
            if field_name in _PROJECT_REQUIRED_FIELDS:
                if row.severity == Severity.ERROR:
                    error_count += 1
                elif row.severity == Severity.WARN:
                    warn_count += 1
                else:
                    info_count += 1
                continue
            key = (row.project_path, row.ref_des, row.uuid, row.category)
            group = grouped_best_practice.setdefault(
                key,
                {
                    "missing_fields": [],
                },
            )
            if field_name not in group["missing_fields"]:
                group["missing_fields"].append(field_name)
            continue
        elif row.check_type != CheckType.MERGE_MISMATCH:
            continue

        if row.severity == Severity.ERROR:
            error_count += 1
        elif row.severity == Severity.WARN:
            warn_count += 1
        else:
            info_count += 1
    for (project_path, ref_des, uuid, category), group in grouped_best_practice.items():
        context = component_context.get((project_path, ref_des, uuid, category), {})
        suggested_row: dict[str, str] = {}
        for field_name in group["missing_fields"]:
            suggested_row[field_name] = _resolve_project_default_suggestion(
                category=category,
                field_name=field_name,
                context=context,
                defaults=defaults,
            )
        for field_name in group["missing_fields"]:
            suggestion = str(suggested_row.get(field_name, "")).strip()
            if _is_meaningful_match_value(suggestion):
                info_count += 1
            else:
                warn_count += 1

    return error_count, warn_count, info_count


def _print_summary(
    report,
    *,
    counts_override: tuple[int, int, int] | None = None,
) -> None:
    """Print a one-line count summary to stderr."""
    if counts_override is None:
        error_count = report.error_count
        warn_count = report.warn_count
        info_count = report.info_count
    else:
        error_count, warn_count, info_count = counts_override

    total = error_count + warn_count + info_count
    if total == 0:
        print("Audit complete: no issues found.", file=sys.stderr)
    else:
        parts = []
        if error_count:
            parts.append(f"{error_count} error(s)")
        if warn_count:
            parts.append(f"{warn_count} warning(s)")
        if info_count:
            parts.append(f"{info_count} info(s)")
        print(f"Audit complete: {', '.join(parts)}.", file=sys.stderr)
