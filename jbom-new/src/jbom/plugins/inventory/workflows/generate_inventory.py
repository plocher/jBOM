"""Workflow for generating inventory from KiCad projects."""

from pathlib import Path
from typing import Optional

from jbom.workflows.registry import register
from jbom.sch_api.kicad_sch import SchematicLoader
from jbom.plugins.inventory.services.component_converter import (
    ComponentToInventoryConverter,
)
import csv
import sys


def generate_inventory(
    schematic_file: Path,
    output: str,
    fabricator_id: str,
    append_file: Optional[str] = None,
    search_enabled: bool = False,
    search_provider: Optional[str] = None,
    search_api_key: Optional[str] = None,
    search_limit: Optional[int] = None,
    search_interactive: bool = False,
) -> None:
    """Generate inventory from KiCad schematic.

    Args:
        schematic_file: Path to KiCad schematic file
        output: Output target (file path, 'console', or '-' for stdout)
        fabricator_id: Fabricator ID for processing (e.g., 'generic', 'jlc')
        append_file: Optional path to existing inventory file to append to
        search_enabled: Whether to enable search enhancement
        search_provider: Search provider if search enabled
        search_api_key: API key for search provider
        search_limit: Search result limit
        search_interactive: Enable interactive mode for search
    """
    # 1. Load components from schematic
    loader = SchematicLoader()
    components = loader.load_components(schematic_file)

    component_count = len(components)

    # 2. Generate inventory items using plugin's ComponentToInventoryConverter
    converter = ComponentToInventoryConverter()
    inventory_items = converter.convert_components(components)

    # Define standard inventory field names
    field_names = [
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
        "UUID",
    ]

    inventory_count = len(inventory_items)

    # 3. Handle output based on format (following mature API pattern)
    if output == "-":
        # Write CSV to stdout
        writer = csv.writer(sys.stdout)
        writer.writerow(field_names)
        for item in inventory_items:
            row = []
            for field_name in field_names:
                # Get value from item attribute
                field_lower = field_name.lower()
                if hasattr(item, field_lower):
                    val = getattr(item, field_lower)
                elif field_name == "UUID":
                    val = getattr(item, "uuid", "")
                else:
                    val = ""
                row.append(str(val) if val is not None else "")
            writer.writerow(row)
    elif output == "console":
        # Print formatted table
        if not inventory_items:
            print("Generated 0 inventory items")
        else:
            print(f"Generated {inventory_count} inventory items:")
            print("-" * 80)
            # Print header
            display_fields = ["IPN", "Category", "Value", "Package", "Manufacturer"]
            available_fields = [f for f in display_fields if f in field_names]
            header = " | ".join(f"{field:<15}" for field in available_fields)
            print(header)
            print("-" * len(header))

            # Print rows (limit to 20 for console)
            for item in inventory_items[:20]:
                values = []
                for field_name in available_fields:
                    field_lower = field_name.lower()
                    if hasattr(item, field_lower):
                        val = getattr(item, field_lower)
                    else:
                        val = ""
                    val_str = str(val) if val else ""
                    if len(val_str) > 14:
                        val_str = val_str[:12] + ".."
                    values.append(val_str)
                row = " | ".join(f"{val:<15}" for val in values)
                print(row)

            if len(inventory_items) > 20:
                print(f"... and {len(inventory_items) - 20} more items")
    else:
        # Write to file
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(field_names)
            for item in inventory_items:
                row = []
                for field_name in field_names:
                    field_lower = field_name.lower()
                    if hasattr(item, field_lower):
                        val = getattr(item, field_lower)
                    elif field_name == "UUID":
                        val = getattr(item, "uuid", "")
                    else:
                        val = ""
                    row.append(str(val) if val is not None else "")
                writer.writerow(row)

        print(
            f"Successfully generated {inventory_count} inventory items from {component_count} components"
        )
        print(f"Output written to: {output_path}")


# Register the workflow
register("inventory.generate", generate_inventory)
