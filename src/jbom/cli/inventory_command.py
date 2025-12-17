"""Inventory command implementation."""
from __future__ import annotations
import argparse
import csv
import sys
from pathlib import Path

from jbom.cli.commands import Command, OutputMode
from jbom.common.output import resolve_output_path
from jbom.generators.bom import BOMGenerator
from jbom.processors.inventory_matcher import InventoryMatcher
from jbom.loaders.project_inventory import ProjectInventoryLoader


class InventoryCommand(Command):
    """Generate inventory file from KiCad project components"""

    def setup_parser(self, parser: argparse.ArgumentParser) -> None:
        """Setup inventory-specific arguments"""
        parser.description = (
            "Generate an initial inventory file from KiCad schematic components"
        )
        parser.formatter_class = argparse.RawDescriptionHelpFormatter
        parser.epilog = """Examples:
  jbom inventory project/                               # Generate inventory to project/inventory.csv
  jbom inventory project/ -o my_inventory.csv           # Generate to specific file
  jbom inventory project/ -o console                    # Show inventory in console
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

    def execute(self, args: argparse.Namespace) -> int:
        """Execute inventory generation"""

        # We use BOMGenerator to handle input discovery and loading
        # Pass None as matcher since we don't have an inventory yet
        matcher = InventoryMatcher(None)
        # Use a minimal options object
        from jbom.common.generator import GeneratorOptions

        generator = BOMGenerator(matcher, GeneratorOptions())

        # Load components
        try:
            input_path = generator.discover_input(Path(args.project))
            components = generator.load_input(input_path)
        except Exception as e:
            print(f"Error loading project: {e}", file=sys.stderr)
            return 1

        if not components:
            print("No components found in project.", file=sys.stderr)
            return 1

        # Generate inventory from components
        loader = ProjectInventoryLoader(components)
        items, fields = loader.load()

        # Handle output
        output_mode, output_path = self.determine_output_mode(args.output)

        if output_mode == OutputMode.CONSOLE:
            # Print simple table
            print(
                f"Generated {len(items)} inventory items from {len(components)} components:"
            )
            print("-" * 80)
            print(f"{'IPN':<20} | {'Value':<15} | {'Package':<15} | {'Category':<10}")
            print("-" * 80)
            for item in items:
                print(
                    f"{item.ipn:<20} | {item.value:<15} | {item.package:<15} | {item.category:<10}"
                )
            print("-" * 80)

        else:
            # Determine file path
            if output_mode == OutputMode.STDOUT:
                f = sys.stdout
            else:
                if output_path:
                    out = output_path
                else:
                    out = resolve_output_path(
                        Path(args.project), args.output, args.outdir, "_inventory.csv"
                    )
                out.parent.mkdir(parents=True, exist_ok=True)
                f = open(out, "w", newline="", encoding="utf-8")

            try:
                writer = csv.writer(f)

                # Write header
                # We want standard fields first, then any extra properties
                standard_fields = [
                    "IPN",
                    "Category",
                    "Value",
                    "Package",
                    "Description",
                    "Keywords",
                    "Manufacturer",
                    "MFGPN",
                    "Datasheet",
                    "LCSC",
                    "Tolerance",
                    "Voltage",
                    "Amperage",
                    "Wattage",
                    "Type",
                    "SMD",
                    "UUID",
                ]

                # Filter fields to only those present in the generated items + standard ones
                # fields list from loader contains all found fields

                # Combine standard fields with any extras found (properties)
                # Avoid duplicates
                header = [f for f in standard_fields if f in fields]
                extra_fields = [f for f in fields if f not in standard_fields]
                header.extend(sorted(extra_fields))

                writer.writerow(header)

                # Write rows
                for item in items:
                    row = []
                    for field in header:
                        # Get value from item attribute or raw_data
                        val = ""
                        field_lower = field.lower()
                        if hasattr(item, field_lower):
                            val = getattr(item, field_lower)
                        elif field in item.raw_data:
                            val = item.raw_data[field]
                        elif field == "UUID":
                            val = item.uuid
                        row.append(val)
                    writer.writerow(row)

                if output_mode != OutputMode.STDOUT:
                    print(f"Successfully wrote {len(items)} inventory items to {out}")

            finally:
                if output_mode != OutputMode.STDOUT:
                    f.close()

        return 0
