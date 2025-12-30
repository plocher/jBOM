"""Inventory command implementation."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

from jbom.cli.commands import Command, OutputMode
from jbom.common.output import resolve_output_path
from jbom.api import generate_enriched_inventory, InventoryOptions


class InventoryCommand(Command):
    """Generate inventory file from KiCad project components"""

    def setup_parser(self, parser: argparse.ArgumentParser) -> None:
        """Setup inventory-specific arguments"""
        parser.description = "Generate inventory file from KiCad schematic components with optional search enrichment"
        parser.formatter_class = argparse.RawDescriptionHelpFormatter
        parser.epilog = """Examples:
  jbom inventory project/                               # Generate basic inventory to project/inventory.csv
  jbom inventory project/ -o my_inventory.csv           # Generate to specific file
  jbom inventory project/ -o console                    # Show inventory in console
  jbom inventory project/ --search                      # Search-enhanced inventory with best matches
  jbom inventory project/ --search --limit=3            # Multiple candidates per component
  jbom inventory project/ --search --provider=mouser --api-key=KEY  # Custom provider settings
"""

        # Positional arguments
        parser.add_argument(
            "project", help="Path to KiCad project directory or .kicad_sch file"
        )

        # Output arguments
        self.add_common_output_args(parser)
        parser.add_argument(
            "--outdir",
            metavar="DIR",
            help="Output directory for generated files (only used if -o not specified)",
        )

        # Search enhancement arguments
        search_group = parser.add_argument_group(
            "Search Enhancement", "Options for automated part search integration"
        )
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

    def execute(self, args: argparse.Namespace) -> int:
        """Execute inventory generation with optional search enrichment"""

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

        # Create inventory options
        options = InventoryOptions(
            search=args.search,
            provider=args.provider,
            api_key=args.api_key,
            limit=limit_value,
            interactive=args.interactive,
        )

        # Determine output path
        output_mode, output_path = self.determine_output_mode(args.output)

        if output_mode == OutputMode.CONSOLE:
            api_output = "console"
        elif output_mode == OutputMode.STDOUT:
            api_output = "stdout"
        else:
            # File output - resolve path
            if output_path:
                api_output = output_path
            else:
                api_output = resolve_output_path(
                    Path(args.project), args.output, args.outdir, "_inventory.csv"
                )

        # Call the API function
        result = generate_enriched_inventory(
            input=args.project, output=api_output, options=options
        )

        if not result["success"]:
            print(f"Error: {result['error']}", file=sys.stderr)
            return 1

        # Print summary information
        if output_mode != OutputMode.CONSOLE:  # Console output already printed
            component_count = result["component_count"]
            inventory_count = len(result["inventory_items"])

            if args.search:
                search_stats = result["search_stats"]
                print(
                    f"Successfully generated {inventory_count} inventory items from {component_count} components"
                )
                print("Search statistics:")
                print(f"  Provider: {search_stats.get('provider', 'N/A')}")
                print(
                    f"  Searches performed: {search_stats.get('searches_performed', 0)}"
                )
                print(f"  Successful: {search_stats.get('successful_searches', 0)}")
                print(f"  Failed: {search_stats.get('failed_searches', 0)}")
                if output_mode != OutputMode.STDOUT:
                    print(f"  Output written to: {api_output}")
            else:
                print(
                    f"Successfully generated {inventory_count} inventory items from {component_count} components"
                )
                if output_mode != OutputMode.STDOUT:
                    print(f"Output written to: {api_output}")

        return 0
