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
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any
from jbom.common.component_classification import get_component_type
from jbom.common.component_filters import apply_component_filters
from jbom.common.package_matching import extract_package_from_footprint
from jbom.config.defaults import DefaultsConfig, get_defaults

from jbom.services.audit_service import AuditRow, AuditService, CheckType
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
]

_PROJECT_REPORT_TRAILING_COLUMNS: list[str] = [
    "Action",
    "Notes",
]
_PROJECT_SUPPLY_CHAIN_FIELDS: set[str] = {
    "Manufacturer",
    "MFGPN",
}
_PROJECT_ACTION_GUIDANCE = (
    "SKIP=no change to kicad project, SET=update with new attribute values"
)
_PROJECT_MISSING_VALUE = "MISSING"
_PROJECT_RES_CATEGORY = "RES"
_PROJECT_CAP_CATEGORY = "CAP"


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
        nargs="+",
        metavar="PATH",
        help=(
            "One or more KiCad project directories (project mode) "
            "or inventory CSV files (inventory mode)"
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
        metavar="REPORT_CSV",
        type=Path,
        default=None,
        help="Write report to this CSV file (default: stdout)",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with non-zero status when WARN-severity rows exist (default: only on ERROR)",
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
    _write_project_report(args, report, component_context=component_context)
    _print_summary(report)

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
) -> None:
    """Write project-mode report as wide CURRENT/SUGGESTED couplets."""
    fieldnames, rows = _build_project_couplet_rows(
        report.rows, component_context=component_context
    )
    output_path: Path | None = getattr(args, "output", None)

    if output_path is not None:
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            _write_csv_rows(handle, fieldnames, rows)
        print(f"Audit report written to {output_path}", file=sys.stderr)
        return

    buf = io.StringIO()
    _write_csv_rows(buf, fieldnames, rows)
    print(buf.getvalue(), end="")


def _write_inventory_report(args: argparse.Namespace, report: Any) -> None:
    """Write inventory-mode report using the stable audit CSV schema."""
    output_path: Path | None = getattr(args, "output", None)

    if output_path is not None:
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            report.write_csv(handle)
        print(f"Audit report written to {output_path}", file=sys.stderr)
        return

    buf = io.StringIO()
    report.write_csv(buf)
    print(buf.getvalue(), end="")


def _build_project_couplet_rows(
    report_rows: list[AuditRow],
    *,
    component_context: dict[tuple[str, str, str, str], dict[str, str]],
) -> tuple[list[str], list[dict[str, str]]]:
    """Build wide CURRENT/SUGGESTED rows from tall QUALITY_ISSUE findings."""
    defaults = get_defaults()
    grouped: OrderedDict[tuple[str, str, str, str], dict[str, Any]] = OrderedDict()
    field_order: list[str] = []

    for row in report_rows:
        if row.check_type != CheckType.QUALITY_ISSUE:
            continue

        field_name = (row.field or "").strip()
        if not field_name or field_name in _PROJECT_SUPPLY_CHAIN_FIELDS:
            continue

        key = (row.project_path, row.ref_des, row.uuid, row.category)
        group = grouped.setdefault(
            key,
            {
                "current": {},
                "suggested": {},
                "missing_fields": [],
            },
        )

        if field_name not in field_order:
            field_order.append(field_name)
        if field_name not in group["missing_fields"]:
            group["missing_fields"].append(field_name)

        current_value = (row.current_value or "").strip()
        if field_name not in group["current"] and current_value:
            group["current"][field_name] = current_value
        group["suggested"][field_name] = _PROJECT_MISSING_VALUE

    fieldnames = (
        _PROJECT_REPORT_BASE_COLUMNS
        + _PROJECT_REPORT_CONTEXT_COLUMNS
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
                suggested_row[field_name] = _resolve_project_default_suggestion(
                    category=category,
                    field_name=field_name,
                    context=context,
                    defaults=defaults,
                )
            else:
                suggested_row[field_name] = raw_suggested
        if group["missing_fields"]:
            missing_fields = ", ".join(group["missing_fields"])
            current_row["Notes"] = f"{ref_des}: Missing attributes: {missing_fields}"
        suggested_row["Notes"] = _PROJECT_ACTION_GUIDANCE
        current_row["Action"] = "SKIP"
        suggested_row["Action"] = "SKIP"

        output_rows.extend([current_row, suggested_row])

    return fieldnames, output_rows


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

    return _PROJECT_MISSING_VALUE


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
                contexts[key] = {
                    "Value": comp.value or "",
                    "Footprint": comp.footprint or "",
                    "Package": (props.get("Package") or "").strip(),
                    "Description": (props.get("Description") or "").strip(),
                }

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


def _print_summary(report) -> None:
    """Print a one-line count summary to stderr."""
    total = len(report.rows)
    if total == 0:
        print("Audit complete: no issues found.", file=sys.stderr)
    else:
        parts = []
        if report.error_count:
            parts.append(f"{report.error_count} error(s)")
        if report.warn_count:
            parts.append(f"{report.warn_count} warning(s)")
        if report.info_count:
            parts.append(f"{report.info_count} info(s)")
        print(f"Audit complete: {', '.join(parts)}.", file=sys.stderr)
