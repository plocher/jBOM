"""Simplified main CLI - direct command registration without plugin registry."""

import argparse
import sys
from typing import List, Optional

from jbom import __version__
from jbom.cli import bom, inventory, pos, parts


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
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress diagnostic guidance output",
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        help="available commands",
    )

    # Direct command registration - no registry needed!
    bom.register_command(subparsers)
    inventory.register_command(subparsers)
    pos.register_command(subparsers)
    parts.register_command(subparsers)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for simplified jBOM CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # Apply quiet flag globally via environment for downstream components
    if getattr(args, "quiet", False):
        import os as _os

        _os.environ["JBOM_QUIET"] = "1"

    # No command specified
    if not args.command:
        parser.print_help()
        return 1

    # Execute command handler (already set by register_command)
    if hasattr(args, "handler"):
        return args.handler(args)

    # This shouldn't happen with proper command registration
    print(f"Error: No handler for command '{args.command}'", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
