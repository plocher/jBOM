"""jBOM CLI with argparse subparsers.

Refactored v3.0 CLI using Command pattern for cleaner architecture.
"""
from __future__ import annotations
import sys
import argparse
from typing import List

from jbom.cli.bom_command import BOMCommand
from jbom.cli.pos_command import POSCommand


def main(argv: List[str] | None = None) -> int:
    """Main CLI entry point with subparsers.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Create main parser
    parser = argparse.ArgumentParser(
        prog="jbom",
        description="KiCad Bill of Materials and Placement File Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  jbom bom project/ -i inventory.csv                    # Generate BOM
  jbom bom project/ -i inventory.csv -o console         # Show formatted table
  jbom bom project/ -i inventory.csv --jlc              # JLCPCB format
  jbom pos board.kicad_pcb                              # Generate placement file
  jbom pos board.kicad_pcb -o console                   # Show formatted table
  jbom pos board.kicad_pcb --outdir build/              # Custom output directory

For detailed help on each command:
  jbom bom --help
  jbom pos --help""",
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

    # Register commands
    commands = {
        "bom": BOMCommand(),
        "pos": POSCommand(),
    }

    for cmd_name, cmd_instance in commands.items():
        cmd_parser = subparsers.add_parser(
            cmd_name,
            help=cmd_instance.__doc__,
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
