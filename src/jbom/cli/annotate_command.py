"""Annotate command implementation."""
from __future__ import annotations
import argparse
import sys

from jbom.cli.commands import Command
from jbom.api import back_annotate


class AnnotateCommand(Command):
    """Back-annotate inventory data to KiCad schematic."""

    def setup_parser(self, parser: argparse.ArgumentParser) -> None:
        """Setup annotate-specific arguments"""
        parser.description = (
            "Back-annotate inventory data (Value, Footprint, LCSC, etc.) "
            "to KiCad schematic symbols using UUID matching."
        )
        parser.epilog = """Examples:
  jbom annotate project/ -i updated_inventory.csv       # Update schematic from inventory
  jbom annotate project/ -i updated_inventory.csv -n    # Dry run (show changes only)
"""

        # Positional arguments
        parser.add_argument(
            "project", help="Path to KiCad project directory or .kicad_sch file"
        )
        parser.add_argument(
            "-i",
            "--inventory",
            required=True,
            metavar="FILE",
            help="Inventory file containing updated component data",
        )
        parser.add_argument(
            "-n",
            "--dry-run",
            action="store_true",
            help="Show what would be updated without modifying files",
        )

    def execute(self, args: argparse.Namespace) -> int:
        """Execute back-annotation"""

        result = back_annotate(
            project=args.project, inventory=args.inventory, dry_run=args.dry_run
        )

        if not result["success"]:
            print(result["error"], file=sys.stderr)
            return 1

        component_count = result["updated_count"]

        # Print update details if in dry-run or if desired
        if args.dry_run:
            for update in result["updates"]:
                print(f"[Dry Run] Update {update['uuid']}: {update['updates']}")

        if result["modified"]:
            if not args.dry_run:
                print(f"Annotating schematic: {result['schematic_path']}")
                print(f"Updated {component_count} components.")
                print("Saving changes...")
                print("Done. Please open KiCad to verify and formatting.")
            else:
                print(
                    f"Dry run complete. {component_count} components would be updated."
                )
        else:
            print("No matching components found to update.")

        return 0
