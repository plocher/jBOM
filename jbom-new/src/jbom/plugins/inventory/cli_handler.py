"""Inventory plugin CLI command handler."""
from __future__ import annotations

import argparse
import sys

from jbom.cli.discovery import resolve_project, default_output_name
from jbom.cli.plugin_registry import register_command
from jbom.workflows.registry import get as get_workflow

# Ensure workflow is registered on import
from jbom.plugins.inventory.workflows import generate_inventory  # noqa: F401


def configure_inventory_parser(parser: argparse.ArgumentParser) -> None:
    """Configure argument parser for inventory command."""
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
        help="Output target: 'console' for table, file path, or omit for <project>.inventory.csv",
    )
    output_group.add_argument(
        "--stdout", action="store_true", help="Write CSV to stdout"
    )

    # Fabricator options
    fab_group = parser.add_argument_group("fabricator options")
    fab_group.add_argument(
        "--fabricator",
        help="Fabricator ID for inventory processing (e.g., 'generic', 'jlc')",
    )

    # Inventory management options
    inventory_group = parser.add_argument_group("inventory management")
    inventory_group.add_argument(
        "--append",
        metavar="FILE",
        help="Append to existing inventory file instead of creating new one",
    )

    # Search enhancement options
    search_group = parser.add_argument_group("search enhancement")
    search_group.add_argument(
        "--search",
        action="store_true",
        help="Enable automatic part searching from distributors",
    )
    search_group.add_argument(
        "--provider",
        choices=["mouser"],
        default="mouser",
        help="Search provider to use (default: mouser)",
    )
    search_group.add_argument(
        "--api-key",
        metavar="KEY",
        help="API key for search provider (overrides environment variables)",
    )
    search_group.add_argument(
        "--limit",
        type=str,
        default="1",
        help="Maximum search results per component (default: 1, use 'none' for all results)",
    )
    search_group.add_argument(
        "--interactive",
        action="store_true",
        help="Enable interactive candidate selection (when multiple results found)",
    )


def handle_inventory_command(args: argparse.Namespace) -> int:
    """Handle the inventory command with parsed arguments."""
    try:
        # Resolve PROJECT to files
        project_files = resolve_project(args.project)

        if not project_files.schematic_files:
            print("Error: No .kicad_sch file found", file=sys.stderr)
            return 2

        # Determine output path
        output = None
        if args.stdout:
            output = "-"
        elif args.output == "stdout":
            output = "-"
        elif args.output:
            output = args.output
        elif args.append:
            # When appending, use the append file as output
            output = args.append
        else:
            # Default: <project>.inventory.csv
            output = str(
                default_output_name(
                    project_files.directory,
                    project_files.project_file,
                    project_files.schematic_files[0],  # Use first schematic
                    ".inventory.csv",
                )
            )

        # Parse limit argument (handle 'none' special case)
        limit = args.limit
        if limit.lower() == "none":
            limit_value = None
        else:
            try:
                limit_value = int(limit)
                if limit_value < 1:
                    print(
                        "Error: --limit must be a positive integer or 'none'",
                        file=sys.stderr,
                    )
                    return 1
            except ValueError:
                print(
                    "Error: --limit must be a positive integer or 'none'",
                    file=sys.stderr,
                )
                return 1

        # Handle fabricator - default to generic if not specified
        fabricator_id = args.fabricator or "generic"

        # Execute workflow
        workflow = get_workflow("inventory.generate")
        workflow(
            schematic_file=project_files.schematic_files[0],  # Use first schematic
            output=output,
            fabricator_id=fabricator_id,
            append_file=args.append,
            search_enabled=args.search,
            search_provider=args.provider if args.search else None,
            search_api_key=args.api_key if args.search else None,
            search_limit=limit_value if args.search else None,
            search_interactive=args.interactive if args.search else False,
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
    name="inventory",
    help="generate inventory files from KiCad schematic components",
    handler=handle_inventory_command,
    configure_parser=configure_inventory_parser,
)
