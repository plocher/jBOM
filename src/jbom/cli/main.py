"""Simplified main CLI - direct command registration without plugin registry."""

import argparse
import sys
from typing import List, Optional

from jbom import __version__
from jbom.cli import (
    annotate,
    audit,
    bom,
    fabrication,
    gerbers,
    inventory,
    pos,
    parts,
    search,
)
from jbom.config.defaults import (
    get_active_defaults_profile,
    set_active_defaults_profile,
)


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
    audit.register_command(subparsers)
    bom.register_command(subparsers)
    annotate.register_command(subparsers)
    fabrication.register_command(subparsers)
    gerbers.register_command(subparsers)
    inventory.register_command(subparsers)
    pos.register_command(subparsers)
    parts.register_command(subparsers)
    search.register_command(subparsers)
    _add_defaults_argument_to_subcommands(subparsers)

    return parser


def _add_defaults_argument_to_subcommands(
    subparsers: argparse._SubParsersAction,  # type: ignore[type-arg]
) -> None:
    """Add a shared defaults-profile selector to every subcommand parser."""

    for command_parser in subparsers.choices.values():
        command_parser.add_argument(
            "--defaults",
            metavar="PROFILE",
            type=lambda value: str(value).strip().lower(),
            default="generic",
            help=(
                "Defaults profile name for configurable behavior " "(default: generic)"
            ),
        )


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
        selected_profile = getattr(args, "defaults", "generic")
        previous_profile = get_active_defaults_profile()
        set_active_defaults_profile(selected_profile)
        try:
            return args.handler(args)
        finally:
            set_active_defaults_profile(previous_profile)

    # This shouldn't happen with proper command registration
    print(f"Error: No handler for command '{args.command}'", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
