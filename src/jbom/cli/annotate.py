"""Annotate command - back-annotate inventory values into schematic properties."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from jbom.services.annotation_service import annotate_schematic, triage_inventory
from jbom.services.project_file_resolver import ProjectFileResolver


def register_command(subparsers) -> None:
    """Register annotate command with argument parser."""

    parser = subparsers.add_parser(
        "annotate",
        help="Back-annotate inventory fields to schematic by UUID",
        description="Back-annotate inventory fields to schematic by UUID",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=".",
        help="Path to .kicad_sch file or project directory (default: current directory)",
    )
    parser.add_argument(
        "-i",
        "--inventory",
        required=True,
        type=Path,
        help="Path to inventory CSV used for annotation",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Show proposed changes without writing the schematic",
    )
    parser.add_argument(
        "--triage",
        action="store_true",
        help="Report rows missing required fields (Value, Package)",
    )
    parser.set_defaults(handler=handle_annotate)


def handle_annotate(args: argparse.Namespace) -> int:
    """Handle annotate command execution."""

    try:
        resolver = ProjectFileResolver(prefer_pcb=False, target_file_type="schematic")
        resolved = resolver.resolve_input(args.input)
        schematic_path = resolved.resolved_path

        if args.triage:
            report = triage_inventory(args.inventory)
            return _print_triage_report(report)

        result = annotate_schematic(
            schematic_path=schematic_path,
            inventory_path=args.inventory,
            dry_run=args.dry_run,
        )
        return _print_annotation_result(result, schematic_path)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _print_triage_report(report) -> int:
    """Print triage report and return command exit code."""

    if not report.rows_with_required_blanks:
        print(
            f"Triage complete: no required blanks found in {report.total_data_rows} rows."
        )
        return 0

    print("Triage report (required blank fields: Value, Package):")
    for issue in report.rows_with_required_blanks:
        missing = ", ".join(issue.missing_required_fields)
        print(
            f"  row {issue.row_number} UUID {issue.uuid or '<blank>'}: missing {missing}"
        )

    print(
        f"Rows with required blanks: {len(report.rows_with_required_blanks)}/{report.total_data_rows}"
    )
    return 0


def _print_annotation_result(result, schematic_path: Path) -> int:
    """Print annotation execution summary."""

    for warning in result.warnings:
        print(f"Warning: {warning}", file=sys.stderr)

    if result.dry_run:
        print(
            f"Dry run complete. {result.updated_components} component(s) would be updated."
        )
    else:
        print(
            f"Annotation complete. Updated {result.updated_components} component(s) in {schematic_path}."
        )

    for change in result.changes:
        print(
            f"  row {change.row_number} UUID {change.uuid}: {change.field}: "
            f"'{change.before}' -> '{change.after}'"
        )

    return 0
