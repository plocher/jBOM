"""BOM plugin CLI command handler."""
from __future__ import annotations

import argparse
import sys

from jbom.cli.discovery import resolve_project, default_output_name
from jbom.cli.plugin_registry import register_command
from jbom.workflows.registry import get as get_workflow

# Ensure workflow is registered on import
from jbom.plugins.bom.workflows import generate_bom  # noqa: F401


def configure_bom_parser(parser: argparse.ArgumentParser) -> None:
    """Configure argument parser for BOM command."""
    parser.add_argument(
        "project",
        nargs="?",
        help=(
            "PROJECT can be: directory with .kicad_pro, "
            "basename of .kicad_pro, or specific .kicad_sch file. "
            "If omitted, uses current directory."
        ),
    )

    # Output options
    output_group = parser.add_argument_group("output options")
    output_group.add_argument(
        "-o",
        "--output",
        help="Output target: 'console' for table, file path, or omit for <project>.bom.csv",
    )
    output_group.add_argument(
        "--stdout", action="store_true", help="Write CSV to stdout"
    )

    # Filtering options
    filter_group = parser.add_argument_group("filtering options")
    filter_group.add_argument(
        "--include-dnp",
        action="store_true",
        help="Include 'do not populate' components (excluded by default)",
    )
    filter_group.add_argument(
        "--include-excluded",
        action="store_true",
        help="Include components marked 'exclude from BOM' (excluded by default)",
    )

    # Fabricator options
    fab_group = parser.add_argument_group("fabricator options")
    fab_group.add_argument(
        "--fabricator", help="Fabricator ID for format presets (e.g., 'jlc')"
    )
    fab_group.add_argument(
        "--jlc", action="store_true", help="Shorthand for --fabricator jlc"
    )
    fab_group.add_argument(
        "--fields",
        help="Comma-separated field list (e.g., 'references,value,footprint,quantity')",
    )


def handle_bom_command(args: argparse.Namespace) -> int:
    """Handle the BOM command with parsed arguments."""
    try:
        # Resolve PROJECT to files
        project_files = resolve_project(args.project)

        if not project_files.schematic_files:
            print("Error: No .kicad_sch files found", file=sys.stderr)
            return 2

        # Determine output path
        output = None
        if args.stdout:
            output = "-"
        elif args.output:
            output = args.output
        else:
            # Default: <project>.bom.csv
            output = str(
                default_output_name(
                    project_files.directory,
                    project_files.project_file,
                    project_files.schematic_files[0],  # Use first schematic as fallback
                    "bom.csv",
                )
            )

        # Build filtering options
        filters = {}
        # Default: exclude DNP and excluded components unless override flags used
        filters["exclude_dnp"] = not args.include_dnp
        filters["exclude_from_bom"] = not args.include_excluded

        # Handle fabricator
        fabricator_id = args.fabricator
        if args.jlc:
            fabricator_id = "jlc"

        # Parse fields
        fields = None
        if args.fields:
            fields = [f.strip() for f in args.fields.split(",")]

        # Execute workflow
        workflow = get_workflow("bom.generate")
        workflow(
            project_files=project_files,
            output=output,
            fabricator_id=fabricator_id,
            fields=fields,
            filters=filters,
        )

        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


# Register the command at import time
register_command(
    name="bom",
    help="generate bill of materials (BOM) from KiCad schematic",
    handler=handle_bom_command,
    configure_parser=configure_bom_parser,
)
