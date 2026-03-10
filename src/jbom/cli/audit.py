"""audit command — field quality checks and inventory coverage analysis.

Usage
-----
Project mode (positionals resolve to KiCad project directories or schematics)::

    jbom audit <proj> [<proj> ...]  \\
        [--inventory cat.csv]       \\
        [-o report.csv]             \\
        [--strict]

Inventory mode (positionals are ``.csv`` files)::

    jbom audit <cat.csv> [<cat.csv> ...]  \\
        [--requirements req.csv]           \\
        [-o report.csv]                    \\
        [--strict]

Mode is detected automatically: if every positional argument ends with
``.csv`` the command operates in inventory mode; otherwise it operates in
project mode.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from jbom.services.audit_service import AuditService
from jbom.services.search.inventory_search_service import InventorySearchService


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
        else:
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

    _write_report(args, report)
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

    _write_report(args, report)
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


def _write_report(args: argparse.Namespace, report) -> None:
    """Write the audit report to the configured output destination."""
    import io

    output_path: Path | None = getattr(args, "output", None)

    if output_path is not None:
        with output_path.open("w", encoding="utf-8", newline="") as f:
            report.write_csv(f)
        print(f"Audit report written to {output_path}", file=sys.stderr)
    else:
        # Write CSV to stdout.
        buf = io.StringIO()
        report.write_csv(buf)
        print(buf.getvalue(), end="")


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
