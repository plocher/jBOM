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

    # No command specified
    if not args.command:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
