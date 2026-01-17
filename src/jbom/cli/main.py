"""jBOM CLI with argparse subparsers.

Refactored v3.0 CLI using Command pattern with plugin auto-discovery.
"""
from __future__ import annotations
import sys
import argparse
from typing import List

from jbom.cli.commands import CommandRegistry, discover_commands


def main(argv: List[str] | None = None) -> int:
    """Main CLI entry point with subparsers.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Discover and register built-in command plugins
    discover_commands("jbom.cli.commands.builtin")

    # Create main parser
    parser = argparse.ArgumentParser(
        prog="jbom",
        description="KiCad Bill of Materials and Placement File Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  jbom bom project/ -i inventory.csv                    # Generate BOM
  jbom pos board.kicad_pcb                              # Generate placement file
  jbom inventory project/                               # Generate inventory from project
  jbom annotate project/ -i inventory.csv               # Back-annotate schema from inventory
  jbom search "0603 10k"                                # Search distributors
  jbom inventory-search inventory.csv --output enhanced.csv  # Enhance inventory with distributor search

For details, try
  jbom <command> --help""",
    )

    # Add version flag
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version="%(prog)s {version}".format(version=_get_version()),
        help="Show version information",
    )

    # Create subparsers
    subparsers = parser.add_subparsers(
        title="commands",
        description="Available commands",
        dest="command",
        required=True,
        help="Command to execute",
    )

    # Register all discovered commands from the registry
    for cmd_name in CommandRegistry.list_commands():
        cmd_class = CommandRegistry.get(cmd_name)
        cmd_instance = cmd_class()

        # Use metadata for help text, fallback to docstring
        help_text = cmd_class.metadata.help_text or cmd_class.__doc__

        cmd_parser = subparsers.add_parser(
            cmd_name,
            help=help_text,
        )
        cmd_instance.setup_parser(cmd_parser)
        # Store command instance for later execution
        cmd_parser.set_defaults(command_instance=cmd_instance)

    # Parse arguments
    args = parser.parse_args(argv)

    # Execute command with error handling
    return args.command_instance.handle_errors(args)


def _get_version() -> str:
    """Get jBOM version string."""
    try:
        from jbom.__version__ import __version__

        return __version__
    except ImportError:
        return "unknown"


if __name__ == "__main__":
    sys.exit(main())
