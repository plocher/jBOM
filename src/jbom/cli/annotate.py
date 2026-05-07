"""Annotate command — apply audit repairs and normalize schematic properties.

Usage
-----
Apply audit repairs to a KiCad project::

    jbom annotate <proj> --repairs report.csv [--dry-run]

Normalize property aliases (V->Voltage, Wattage->Power, etc.) in a schematic::

    jbom annotate <proj> --normalize [--dry-run]

Both flags may be used together; ``--normalize`` always runs before ``--repairs``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from jbom.services.annotation_service import (
    RepairsAnnotationResult,
    annotate_from_repairs,
    normalize_schematic_properties,
)
from jbom.common.kicad_runtime import check_write_permitted
from jbom.services.project_file_resolver import ProjectFileResolver


def register_command(subparsers) -> None:
    """Register annotate command with argument parser."""

    parser = subparsers.add_parser(
        "annotate",
        help="Apply audit repairs and/or normalize schematic properties",
        description=(
            "Apply Action=SET rows from an audit report.csv to schematic symbols,\n"
            "and/or normalize property aliases to canonical names.\n\n"
            "REPAIRS MODE  — use after 'jbom audit ... -o report.csv'; fill in\n"
            "  ApprovedValue and set Action=SET in the report, then run:\n"
            "    jbom annotate <proj> --repairs report.csv\n\n"
            "NORMALIZE MODE — rename alias properties (V->Voltage, Wattage->Power ...):\n"
            "    jbom annotate <proj> --normalize"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=".",
        help="Path to .kicad_sch file or project directory (default: current directory)",
    )
    parser.add_argument(
        "--repairs",
        metavar="REPORT_CSV",
        type=Path,
        default=None,
        help=(
            "Path to audit report.csv.  Rows with Action=SET are applied: "
            "the schematic property named Field is set to ApprovedValue."
        ),
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Show proposed changes without writing the schematic",
    )
    parser.add_argument(
        "--normalize",
        action="store_true",
        help=(
            "Normalize schematic property aliases to canonical names "
            "(V->Voltage, A/Amperage->Current, W/Wattage->Power)"
        ),
    )
    parser.set_defaults(handler=handle_annotate)


def handle_annotate(args: argparse.Namespace) -> int:
    """Handle annotate command execution."""

    if not args.repairs and not args.normalize:
        print(
            "Error: annotate requires at least one of --repairs or --normalize",
            file=sys.stderr,
        )
        return 1

    try:
        resolver = ProjectFileResolver(prefer_pcb=False, target_file_type="schematic")
        resolved = resolver.resolve_input(args.input)
        schematic_files = resolved.get_hierarchical_files()

        # Refuse (or warn on --dry-run) if KiCad has the project open.
        if resolved.project_context:
            check_write_permitted(resolved.project_context, dry_run=args.dry_run)

        exit_code = 0

        # --normalize runs first (field renaming is a prerequisite for repairs).
        if args.normalize:
            result = normalize_schematic_properties(
                schematic_files, dry_run=args.dry_run
            )
            _print_normalization_result(result)
            if result.conflicts:
                return 1

        # --repairs applies audit SET rows.
        if args.repairs is not None:
            repairs_result = annotate_from_repairs(
                repairs_path=args.repairs,
                schematic_files=schematic_files,
                dry_run=args.dry_run,
            )
            _print_repairs_result(repairs_result)
            if repairs_result.failed:
                exit_code = 1

        return exit_code

    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except PermissionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# Private output helpers
# ---------------------------------------------------------------------------


def _print_normalization_result(result) -> None:
    """Print normalize execution summary and any detected conflicts."""

    if result.conflicts:
        print(
            "Normalization aborted due to conflicting alias/canonical values:",
            file=sys.stderr,
        )
        for conflict in result.conflicts:
            fields = ", ".join(conflict.source_fields)
            values = ", ".join(repr(v) for v in conflict.source_values)
            print(
                f"  file={conflict.source_file} uuid={conflict.uuid} "
                f"target={conflict.target_field} aliases=[{fields}] values=[{values}]",
                file=sys.stderr,
            )
        return

    mode_label = "would normalize" if result.dry_run else "normalized"
    print(
        f"Normalization complete: {mode_label} {result.updated_components} component(s)."
    )
    for change in result.changes:
        print(
            f"  {change.source_file} UUID {change.uuid}: "
            f"{change.source_field} -> {change.target_field} ({change.value!r})"
        )


def _print_repairs_result(result: RepairsAnnotationResult) -> None:
    """Print repairs execution summary."""

    for warning in result.warnings:
        print(warning)

    for error in result.errors:
        print(f"Error: {error}", file=sys.stderr)

    mode_label = "would apply" if result.dry_run else "applied"
    print(
        f"Repairs complete: {mode_label} {result.applied} change(s), "
        f"skipped {result.skipped}, failed {result.failed}."
    )

    for change in result.changes:
        print(
            f"  UUID {change.uuid}: {change.field}: "
            f"'{change.before}' -> '{change.after}'"
        )
