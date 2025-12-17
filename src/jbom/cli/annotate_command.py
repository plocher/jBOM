"""Annotate command implementation."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from typing import Dict

from jbom.cli.commands import Command
from jbom.loaders.inventory import InventoryLoader
from jbom.processors.annotator import SchematicAnnotator
from jbom.generators.bom import BOMGenerator
from jbom.common.generator import GeneratorOptions
from jbom.processors.inventory_matcher import InventoryMatcher


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

        # 1. Discover Schematic
        # We can reuse BOMGenerator logic to find the input file
        # Hack: instantiate dummy generator
        matcher = InventoryMatcher(None)
        generator = BOMGenerator(matcher, GeneratorOptions())
        try:
            schematic_path = generator.discover_input(Path(args.project))
        except Exception as e:
            print(f"Error finding schematic: {e}", file=sys.stderr)
            return 1

        if schematic_path.suffix != ".kicad_sch":
            print(
                f"Error: Back-annotation only supports .kicad_sch files. Found: {schematic_path}",
                file=sys.stderr,
            )
            return 1

        print(f"Annotating schematic: {schematic_path}")

        # 2. Load Inventory
        try:
            loader = InventoryLoader(Path(args.inventory))
            items, fields = loader.load()
        except Exception as e:
            print(f"Error loading inventory: {e}", file=sys.stderr)
            return 1

        if not items:
            print("Inventory is empty.", file=sys.stderr)
            return 1

        # 3. Load Annotator
        annotator = SchematicAnnotator(schematic_path)
        try:
            annotator.load()
        except Exception as e:
            print(f"Error loading schematic structure: {e}", file=sys.stderr)
            return 1

        # 4. Iterate and Update
        component_count = 0

        for item in items:
            if not item.uuid:
                continue

            # Prepare updates
            updates: Dict[str, str] = {}

            # Map Inventory Fields -> Schematic Properties
            # We want to push back: Value, Footprint, LCSC, Manufacturer, MFGPN
            if item.value:
                updates["Value"] = item.value
            if item.package:
                updates[
                    "Footprint"
                ] = (
                    item.package
                )  # Caution: Inventory Package might be simplified "0603". Schematic expects full footprint.
                # If user simplified it in CSV, we might break footprint link.
                # Use caution. Maybe skip Footprint unless explicitly requested?
                # For now, let's assume user knows what they are doing if they changed it.
                # Or maybe mapped: I:Package -> Footprint
                pass

            if item.lcsc:
                updates["LCSC"] = item.lcsc
            if item.manufacturer:
                updates["Manufacturer"] = item.manufacturer
            if item.mfgpn:
                updates["MFGPN"] = item.mfgpn

            if not updates:
                continue

            # Split UUIDs (comma separated)
            uuids = [u.strip() for u in item.uuid.split(",") if u.strip()]

            for uuid in uuids:
                if annotator.update_component(uuid, updates):
                    component_count += 1
                    if args.dry_run:
                        print(f"[Dry Run] Update {uuid}: {updates}")

        # 5. Save
        if annotator.modified:
            if not args.dry_run:
                print(f"Updated {component_count} components.")
                print("Saving changes...")
                annotator.save()
                print("Done. Please open KiCad to verify and formatting.")
            else:
                print(
                    f"Dry run complete. {component_count} components would be updated."
                )
        else:
            print("No matching components found to update.")

        return 0
