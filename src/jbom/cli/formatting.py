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
    bom_entries: List[BOMEntry], verbose: bool = False, include_mfg: bool = False
):
    """Print BOM entries as a formatted console table with word wrapping and URL shortening."""
    if not bom_entries:
        print("No BOM entries to display.")
        return

    # Get terminal width for intelligent column sizing
    terminal_width = shutil.get_terminal_size(fallback=(120, 24)).columns

    # Determine columns to display
    headers = ["Reference", "Qty", "Value", "Footprint", "LCSC"]
    if include_mfg:
        headers.extend(["Manufacturer", "MFGPN"])
    headers.extend(["Datasheet", "SMD"])
    if verbose:
        headers.extend(["Match_Quality", "Priority"])

    # Check if any entries have notes
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

    def format_value(entry: BOMEntry, header: str) -> str:
        """Extract and format value for given header."""
        if header == "Reference":
            return entry.reference
        elif header == "Qty":
            return str(entry.quantity)
        elif header == "Value":
            return entry.value or ""
        elif header == "Footprint":
            return entry.footprint or ""
        elif header == "LCSC":
            return entry.lcsc or ""
        elif header == "Manufacturer":
            return entry.manufacturer or ""
        elif header == "MFGPN":
            return entry.mfgpn or ""
        elif header == "Datasheet":
            url = entry.datasheet or ""
            return shorten_url(url, max_widths.get("Datasheet", 35))
        elif header == "SMD":
            return "Yes" if entry.smd else "No"
        elif header == "Match_Quality":
            return entry.match_quality if entry.match_quality else ""
        elif header == "Priority":
            return str(entry.priority) if entry.priority else ""
        elif header == "Notes":
            return entry.notes or ""
        return ""

    # Build rows with wrapped text
    table_rows = []
    for entry in bom_entries:
        # Create a row dict with wrapped lines for each column
        row_data = {}
        max_lines = 1
        for header in headers:
            value = format_value(entry, header)
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
