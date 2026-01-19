"""
Service for formatting inventory output in various formats.

Supports CSV files, stdout CSV, and console table display.
"""

import csv
import io
from pathlib import Path
from jbom.common.types import InventoryItem


class InventoryFormatter:
    """Handles formatting inventory data for different output formats."""

    def __init__(self):
        """Initialize formatter."""
        # Standard column order for inventory CSV
        self.standard_columns = [
            "IPN",
            "Name",
            "Keywords",
            "Category",
            "SMD",
            "Value",
            "Type",
            "Description",
            "Package",
            "Form",
            "Pins",
            "Pitch",
            "Tolerance",
            "V",
            "A",
            "W",
            "Angle",
            "Wavelength",
            "mcd",
            "Frequency",
            "Distributor",
            "DPN",
            "DPNLink",
            "Priority",
            "Status",
            "Manufacturer",
            "MPN",
            "Symbol",
            "Footprint",
            "Datasheet",
        ]

    def write_csv_file(self, items: List[InventoryItem], output_file: Path) -> None:
        """Write inventory items to CSV file.

        Args:
            items: List of InventoryItem objects
            output_file: Path to output CSV file
        """
        # Determine all columns that have data
        columns = self._determine_columns(items)

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()

            for item in items:
                row = self._item_to_row(item, columns)
                writer.writerow(row)

    def format_csv_stdout(self, items: List[InventoryItem]) -> str:
        """Format inventory items as CSV string for stdout.

        Args:
            items: List of InventoryItem objects

        Returns:
            CSV formatted string
        """
        if not items:
            # Return just headers for empty inventory
            return ",".join(self._get_basic_columns()) + "\n"

        # Determine columns and format as CSV
        columns = self._determine_columns(items)

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()

        for item in items:
            row = self._item_to_row(item, columns)
            writer.writerow(row)

        return output.getvalue()

    def format_console_table(self, items: List[InventoryItem]) -> str:
        """Format inventory items as console table.

        Args:
            items: List of InventoryItem objects

        Returns:
            Formatted table string
        """
        if not items:
            return f"Generated 0 inventory items\n"

        # Use basic columns for console display to keep table manageable
        display_columns = ["IPN", "Category", "Value", "Package", "Manufacturer"]

        # Calculate column widths
        col_widths = {}
        for col in display_columns:
            col_widths[col] = len(col)  # Start with header width

        # Check item widths
        for item in items:
            row = self._item_to_row(item, display_columns)
            for col in display_columns:
                value_len = len(str(row.get(col, "")))
                col_widths[col] = max(col_widths[col], value_len)

        # Build table
        lines = []

        # Header
        header_parts = []
        separator_parts = []
        for col in display_columns:
            width = col_widths[col]
            header_parts.append(col.ljust(width))
            separator_parts.append("-" * width)

        lines.append(" | ".join(header_parts))
        lines.append("-|-".join(separator_parts))

        # Data rows
        for item in items:
            row = self._item_to_row(item, display_columns)
            row_parts = []
            for col in display_columns:
                width = col_widths[col]
                value = str(row.get(col, ""))
                row_parts.append(value.ljust(width))
            lines.append(" | ".join(row_parts))

        # Add summary
        summary = f"\nGenerated {len(items)} inventory items"

        return "\n".join(lines) + summary + "\n"

    def _determine_columns(self, items: List[InventoryItem]) -> List[str]:
        """Determine which columns to include based on data.

        Args:
            items: List of InventoryItem objects

        Returns:
            List of column names to include
        """
        if not items:
            return self._get_basic_columns()

        # Start with basic required columns
        columns = self._get_basic_columns()

        # Add columns that have data in at least one item
        additional_fields = set()

        for item in items:
            # Check standard fields that might have data
            if item.tolerance:
                additional_fields.add("Tolerance")
            if item.voltage:
                additional_fields.add("V")
            if item.amperage:
                additional_fields.add("A")
            if item.wattage:
                additional_fields.add("W")
            if item.distributor:
                additional_fields.add("Distributor")
            if item.distributor_part_number:
                additional_fields.add("DPN")
            if item.priority != 99:  # If priority is not default
                additional_fields.add("Priority")
            if item.lcsc:
                additional_fields.add("LCSC")

            # Check raw_data for additional properties
            if hasattr(item, "raw_data") and item.raw_data:
                original_props = item.raw_data.get("original_properties", {})
                for key in original_props:
                    if key not in [
                        "Tolerance",
                        "Voltage",
                        "V",
                        "Amperage",
                        "A",
                        "Wattage",
                        "W",
                    ]:
                        # Add custom property columns
                        additional_fields.add(key)

        # Add additional fields in a reasonable order
        for field in ["Tolerance", "V", "A", "W", "Distributor", "DPN", "Priority"]:
            if field in additional_fields:
                columns.append(field)
                additional_fields.remove(field)

        # Add remaining custom fields
        columns.extend(sorted(additional_fields))

        return columns

    def _get_basic_columns(self) -> List[str]:
        """Get basic required columns for inventory.

        Returns:
            List of basic column names
        """
        return [
            "IPN",
            "Category",
            "Value",
            "Package",
            "Description",
            "Manufacturer",
            "MPN",
            "Datasheet",
        ]

    def _item_to_row(self, item: InventoryItem, columns: List[str]) -> Dict[str, str]:
        """Convert InventoryItem to dictionary row for CSV output.

        Args:
            item: InventoryItem object
            columns: List of column names to include

        Returns:
            Dictionary mapping column names to values
        """
        # Map InventoryItem fields to CSV column names
        field_mapping = {
            "IPN": item.ipn,
            "Name": item.ipn,  # Use IPN as Name for now
            "Keywords": item.keywords,
            "Category": item.category,
            "SMD": item.smd,
            "Value": item.value,
            "Type": item.type,
            "Description": item.description,
            "Package": item.package,
            "Form": "",  # Not currently used
            "Pins": "",  # Not currently used
            "Pitch": "",  # Not currently used
            "Tolerance": item.tolerance,
            "V": item.voltage,
            "A": item.amperage,
            "W": item.wattage,
            "Angle": "",  # Not currently used
            "Wavelength": "",  # Not currently used
            "mcd": "",  # Not currently used
            "Frequency": "",  # Not currently used
            "Distributor": item.distributor,
            "DPN": item.distributor_part_number,
            "DPNLink": "",  # Not currently used
            "Priority": str(item.priority) if item.priority != 99 else "",
            "Status": "",  # Not currently used
            "Manufacturer": item.manufacturer,
            "MPN": item.mfgpn,
            "MFGPN": item.mfgpn,  # Alternative name
            "Symbol": "",  # Not currently used
            "Footprint": "",  # Could be populated from raw_data
            "Datasheet": item.datasheet,
            "LCSC": item.lcsc,
        }

        # Add custom fields from raw_data
        if hasattr(item, "raw_data") and item.raw_data:
            original_props = item.raw_data.get("original_properties", {})
            for key, value in original_props.items():
                if key not in field_mapping:
                    field_mapping[key] = value

        # Build row with only requested columns
        row = {}
        for col in columns:
            value = field_mapping.get(col, "")
            # Ensure value is string and clean it
            row[col] = str(value).strip() if value else ""

        return row
