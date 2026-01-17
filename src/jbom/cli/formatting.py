"""CLI formatting utilities for console output.

Provides functions to format BOM and POS data as console tables.
"""
from __future__ import annotations
import shutil
from typing import List

from jbom.common.types import BOMEntry

__all__ = [
    "print_bom_table",
]


def print_bom_table(
    bom_entries: List[BOMEntry],
    fields: List[str] = None,
    generator=None,
    verbose: bool = False,
    include_mfg: bool = False,
):
    """Print BOM entries as a formatted console table with word wrapping and URL shortening.

    Args:
        bom_entries: List of BOM entries to display
        fields: Optional list of field names to display (uses same format as CSV output)
        generator: Optional BOM generator for field value extraction
        verbose: Include verbose columns (deprecated if fields provided)
        include_mfg: Include manufacturer columns (deprecated if fields provided)
    """
    if not bom_entries:
        print("No BOM entries to display.")
        return

    # Get terminal width for intelligent column sizing
    terminal_width = shutil.get_terminal_size(fallback=(120, 24)).columns

    # Determine columns to display
    if fields and generator:
        # Use fabricator-aware field mapping
        from jbom.generators.bom import field_to_header

        # Get column mapping from fabricator (if available)
        column_map = {}
        if generator.fabricator:
            for fab_header, field in generator.fabricator.get_bom_columns().items():
                column_map[field] = fab_header

        # Convert fields to headers
        headers = []
        normalized_fields = []
        for field in fields:
            if field in column_map:
                headers.append(column_map[field])
            elif field == "fabricator_part_number" and generator.fabricator:
                headers.append(generator.fabricator.config.part_number_header)
            else:
                headers.append(field_to_header(field))
            normalized_fields.append(field)
    else:
        # Legacy behavior
        headers = ["Reference", "Qty", "Value", "Footprint", "LCSC"]
        if include_mfg:
            headers.extend(["Manufacturer", "MFGPN"])
        headers.extend(["Datasheet", "SMD"])
        if verbose:
            headers.extend(["Match_Quality", "Priority"])
        normalized_fields = None

    # Check if any entries have notes (only for legacy mode)
    if normalized_fields is None:
        any_notes = any((e.notes or "").strip() for e in bom_entries)
        if any_notes:
            headers.append("Notes")

    # Set preferred column widths for wrapping guidance
    # These will be adjusted based on terminal width
    preferred_widths = {
        "Reference": 60,  # Allow long reference lists
        "Qty": 5,
        "Value": 12,
        "Footprint": 20,
        "LCSC": 10,
        "Manufacturer": 15,
        "MFGPN": 18,
        "Datasheet": 35,  # URLs get special handling
        "SMD": 5,
        "Match_Quality": 13,
        "Priority": 8,
        "Notes": 50,
    }

    # Calculate total preferred width including separators (" | ")
    separator_width = len(" | ") * (len(headers) - 1)
    total_preferred = (
        sum(preferred_widths.get(h, 20) for h in headers) + separator_width
    )

    # If preferred width exceeds terminal, scale down proportionally for flexible columns
    max_widths = preferred_widths.copy()
    if total_preferred > terminal_width:
        # Fixed-width columns that shouldn't shrink
        fixed_columns = {"Qty", "SMD", "LCSC", "Priority"}
        fixed_total = sum(
            preferred_widths.get(h, 20) for h in headers if h in fixed_columns
        )

        # Available width for flexible columns
        available = (
            terminal_width - fixed_total - separator_width - 10
        )  # -10 for safety margin
        flexible_total = sum(
            preferred_widths.get(h, 20) for h in headers if h not in fixed_columns
        )

        if available > 0 and flexible_total > 0:
            scale_factor = available / flexible_total
            for h in headers:
                if h not in fixed_columns:
                    max_widths[h] = max(
                        10, int(preferred_widths.get(h, 20) * scale_factor)
                    )

    def wrap_text(text: str, width: int) -> List[str]:
        """Wrap text to fit within width, breaking on whitespace."""
        if not text or len(text) <= width:
            return [text] if text else [""]
        lines = []
        words = text.split()
        current_line = words[0]
        for word in words[1:]:
            if len(current_line) + 1 + len(word) <= width:
                current_line += " " + word
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines

    def shorten_url(url: str, max_width: int) -> str:
        """Shorten URL by removing protocol and truncating if needed."""
        if not url:
            return ""
        # Remove http:// or https://
        shortened = url.replace("https://", "").replace("http://", "")
        if len(shortened) > max_width:
            # Keep start and end, use ... in middle
            keep_chars = (max_width - 3) // 2
            shortened = shortened[:keep_chars] + "..." + shortened[-keep_chars:]
        return shortened

    def format_value(entry: BOMEntry, field: str) -> str:
        """Extract and format value for given field.

        Args:
            entry: BOM entry
            field: Normalized field name (snake_case)
        """
        if fields and generator and normalized_fields:
            # Use generator's field extraction (fabricator-aware)
            # Find component and inventory item for this entry
            first_ref = entry.reference.replace("ALT: ", "").split(", ")[0]
            component = None
            inventory_item = None

            for comp in generator.components:
                if comp.reference == first_ref:
                    component = comp
                    break

            if entry.lcsc:
                for item in generator.matcher.inventory:
                    if item.lcsc == entry.lcsc:
                        inventory_item = item
                        break

            if component:
                value = generator._get_field_value(
                    field, entry, component, inventory_item
                )
                # Special handling for datasheet URLs
                if "datasheet" in field.lower() and value:
                    return shorten_url(value, max_widths.get(field, 35))
                return value or ""
            return ""
        else:
            # Legacy hardcoded behavior
            if field == "Reference":
                return entry.reference
            elif field == "Qty":
                return str(entry.quantity)
            elif field == "Value":
                return entry.value or ""
            elif field == "Footprint":
                return entry.footprint or ""
            elif field == "LCSC":
                return entry.lcsc or ""
            elif field == "Manufacturer":
                return entry.manufacturer or ""
            elif field == "MFGPN":
                return entry.mfgpn or ""
            elif field == "Datasheet":
                url = entry.datasheet or ""
                return shorten_url(url, max_widths.get("Datasheet", 35))
            elif field == "SMD":
                return "Yes" if entry.smd else "No"
            elif field == "Match_Quality":
                return entry.match_quality if entry.match_quality else ""
            elif field == "Priority":
                return str(entry.priority) if entry.priority else ""
            elif field == "Notes":
                return entry.notes or ""
            return ""

    # Build rows with wrapped text
    table_rows = []
    for entry in bom_entries:
        # Create a row dict with wrapped lines for each column
        row_data = {}
        max_lines = 1
        for idx, header in enumerate(headers):
            # Use normalized field if available, otherwise use header for legacy mode
            field = normalized_fields[idx] if normalized_fields else header
            value = format_value(entry, field)
            width = max_widths.get(header, 20)
            lines = wrap_text(value, width)
            row_data[header] = lines
            max_lines = max(max_lines, len(lines))
        table_rows.append((row_data, max_lines))

    # Calculate actual column widths based on content
    # Use actual content width even if it exceeds max_widths suggestion
    # (max_widths is for wrapping guidance, not hard caps on column width)
    col_widths = {}
    for header in headers:
        max_width = len(header)  # At least as wide as header
        for row_data, _ in table_rows:
            for line in row_data[header]:
                max_width = max(max_width, len(line))
        # Use actual max width (don't cap if content can't be wrapped smaller)
        col_widths[header] = max_width

    # Print header
    header_line = " | ".join(h.ljust(col_widths[h]) for h in headers)
    print(header_line)
    print("-" * len(header_line))

    # Print rows
    for row_data, max_lines in table_rows:
        for line_idx in range(max_lines):
            line_parts = []
            for header in headers:
                lines = row_data[header]
                if line_idx < len(lines):
                    line_parts.append(lines[line_idx].ljust(col_widths[header]))
                else:
                    line_parts.append(" " * col_widths[header])
            print(" | ".join(line_parts))
