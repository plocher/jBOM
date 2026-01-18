"""Main CLI entry point for jBOM."""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from jbom import __version__
from jbom.core.plugin_loader import PluginLoader


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(
        prog="jbom",
        description="KiCad Bill of Materials and Placement File Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"jbom {__version__}",
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        help="available commands",
    )

    # Add plugin command
    plugin_parser = subparsers.add_parser(
        "plugin",
        help="manage plugins",
    )
    plugin_parser.add_argument(
        "--list",
        action="store_true",
        help="list installed plugins",
    )

    # Add pos command
    pos_parser = subparsers.add_parser(
        "pos",
        help="generate placement (POS/CPL) data",
    )
    pos_parser.add_argument(
        "pcb",
        nargs="?",
        help="Path to .kicad_pcb (optional; if omitted, discover in current directory)",
    )
    pos_parser.add_argument(
        "-o",
        "--output",
        help="Output target: 'console' or a file path (default: <project>.pos.csv)",
        default=None,
    )
    pos_parser.add_argument(
        "--stdout",
        action="store_true",
        help="Write CSV to stdout (equivalent to -o -)",
    )
    pos_parser.add_argument(
        "--layer",
        choices=["TOP", "BOTTOM"],
        help="Filter to only components on specified layer",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for jBOM CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    from jbom.cli.discovery import find_project_and_pcb, default_output_name
    from jbom.workflows.registry import get as get_workflow

    # Ensure POS workflow registered (side-effect import)
    from jbom.plugins.pos.workflows import generate_pos  # noqa: F401

    # Handle plugin command
    if args.command == "plugin":
        if args.list:
            # Discover plugins
            plugins_dir = Path(__file__).parent.parent / "plugins"
            loader = PluginLoader(plugins_dir)
            plugins = loader.discover_plugins()

            if not plugins:
                print("No core plugins found")
            else:
                print("Core plugins:")
                for plugin in plugins:
                    print(f"  {plugin.name} ({plugin.version})")
                    if plugin.description:
                        print(f"    {plugin.description}")
            return 0
        else:
            # No action specified for plugin command
            parser.parse_args([args.command, "--help"])
            return 1

    if args.command == "pos":
        # Resolve PCB path or discover
        if args.pcb:
            pcb_path = Path(args.pcb)
            if not pcb_path.exists():
                print(f"Error: PCB file not found: {pcb_path}", file=sys.stderr)
                return 2
            project = None
            cwd = pcb_path.parent
        else:
            cwd = Path.cwd()
            project, pcb_path = find_project_and_pcb(cwd)
            if not pcb_path:
                print(
                    "Error: No .kicad_pcb file found in current directory",
                    file=sys.stderr,
                )
                return 2
        # Determine output
        output = args.output
        if args.stdout:
            output = "-"
        if output is None:
            output = str(default_output_name(cwd, project, pcb_path, "pos.csv"))
        # Call workflow
        try:
            wf = get_workflow("pos.generate")
            wf(pcb_file=pcb_path, output=output, layer=args.layer)
            return 0
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    # No command specified
    if not args.command:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
