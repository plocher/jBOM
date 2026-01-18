"""Reusable console table formatting utilities.

Features:
- Dynamic column sizing based on content
- Optional terminal width awareness
- Per-column word wrapping
- Clean ASCII header and separator with aligned columns

This module is intentionally lightweight so plugins (e.g. POS, BOM) can
render consistent human-readable tables without duplicating logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence
import shutil


@dataclass(frozen=True)
class Column:
    """Column definition for console table rendering.

    name: header label to display
    key: value key in each row mapping
    wrap: if True, wrap on whitespace to fit width; otherwise do not wrap
    preferred_width: hint for target width when terminal_width is set
    fixed: if True, avoid shrinking when fitting to terminal width
    align: "left" or "right" alignment
    """

    name: str
    key: str
    wrap: bool = False
    preferred_width: int = 20
    fixed: bool = False
    align: str = "left"


def _wrap_text(text: str, width: int) -> List[str]:
    if width <= 0:
        return [text]
    t = text or ""
    if len(t) <= width:
        return [t]

    # Tokenize on spaces but support tokens longer than width
    tokens = t.split(" ")
    lines: List[str] = []
    current = ""

    for tok in tokens:
        token = tok
        while token:
            if not current:
                if len(token) <= width:
                    current = token
                    token = ""
                else:
                    # Break long unbreakable token into chunks
                    lines.append(token[:width])
                    token = token[width:]
            else:
                if len(current) + 1 + len(token) <= width:
                    current = current + " " + token
                    token = ""
                else:
                    # Emit current line and continue trying to place token
                    lines.append(current)
                    current = ""

    if current:
        lines.append(current)

    return lines


def print_table(
    rows: Iterable[Mapping[str, str]],
    columns: Sequence[Column],
    *,
    terminal_width: Optional[int] = None,
    title: Optional[str] = None,
) -> None:
    """Print a formatted table.

    Args:
        rows: Iterable of row mappings. Keys correspond to Column.key
        columns: Ordered sequence of Column definitions
        terminal_width: Optional terminal width to guide sizing. If None,
                        the table expands to content width
        title: Optional title printed above the table with an underline
    """
    cols = list(columns)
    data = list(rows)

    # Compute content widths per column (minimum is header width)
    col_widths: Dict[str, int] = {}
    for c in cols:
        header_w = len(c.name)
        max_w = header_w
        for r in data:
            v = str(r.get(c.key, ""))
            # If wrapping is enabled, measure unwrapped length but allow later wrap
            for line in v.splitlines() if "\n" in v else [v]:
                if len(line) > max_w:
                    max_w = len(line)
        col_widths[c.key] = max_w

    # Optionally fit to terminal width using preferred widths as guidance
    if terminal_width is None:
        try:
            terminal_width = shutil.get_terminal_size(fallback=(120, 24)).columns
        except Exception:
            terminal_width = 120

    # Build initial target widths = min(actual content, preferred when provided)
    target: Dict[str, int] = {}
    for c in cols:
        target[c.key] = max(
            len(c.name), min(col_widths[c.key], max(5, c.preferred_width))
        )

    # Compute total with separators
    def total_with_sep(widths: Mapping[str, int]) -> int:
        total = sum(widths[c.key] for c in cols)
        total += 3 * (len(cols) - 1)  # " | " between columns
        return total

    # If too wide, shrink non-fixed wrapped columns proportionally, but not below header width
    max_allowed = terminal_width
    if total_with_sep(target) > max_allowed:
        flexible_keys = [c.key for c in cols if not c.fixed]
        if flexible_keys:
            flex_total = sum(target[k] for k in flexible_keys)
            # Leave at least header width for each, and 10 char safety margin overall
            available = max_allowed - (total_with_sep(target) - flex_total) - 10
            if available > 0 and flex_total > 0:
                scale = available / flex_total
                for k in flexible_keys:
                    new_w = max(
                        len(next(c for c in cols if c.key == k).name),
                        int(target[k] * scale),
                    )
                    target[k] = max(5, new_w)

    # Prepare wrapped rows based on final widths
    wrapped_rows: List[List[List[str]]] = []  # rows -> columns -> lines
    max_lines_per_row: List[int] = []
    for r in data:
        col_lines: List[List[str]] = []
        max_lines = 1
        for c in cols:
            v = str(r.get(c.key, ""))
            width = target[c.key]
            if c.wrap:
                # Preserve existing newlines, wrap each paragraph
                paragraphs = v.splitlines() or [""]
                lines: List[str] = []
                for p in paragraphs:
                    lines.extend(_wrap_text(p, width))
                if not lines:
                    lines = [""]
            else:
                lines = [v]
            col_lines.append(lines)
            if len(lines) > max_lines:
                max_lines = len(lines)
        wrapped_rows.append(col_lines)
        max_lines_per_row.append(max_lines)

    # Header and separator
    header = " | ".join(
        (
            c.name.ljust(target[c.key])
            if c.align == "left"
            else c.name.rjust(target[c.key])
        )
        for c in cols
    )
    separator = "-+-".join("-" * target[c.key] for c in cols)

    # Title if provided
    if title:
        print(title)
        print("=" * min(len(title), max(20, len(header))))

    print(header)
    print(separator)

    # Print rows
    for col_lines, max_lines in zip(wrapped_rows, max_lines_per_row):
        for i in range(max_lines):
            parts: List[str] = []
            for c, lines in zip(cols, col_lines):
                s = lines[i] if i < len(lines) else ""
                if c.align == "right":
                    parts.append(s.rjust(target[c.key]))
                else:
                    parts.append(s.ljust(target[c.key]))
            print(" | ".join(parts))


def print_tabular_data(
    data: Iterable[Any],
    columns: Sequence[Column],
    *,
    row_transformer: Optional[Callable[[Any], Mapping[str, str]]] = None,
    sort_key: Optional[Callable[[Any], Any]] = None,
    title: Optional[str] = None,
    summary_line: Optional[str] = None,
    terminal_width: Optional[int] = None,
) -> None:
    """Print tabular data with configurable transformation and formatting.

    This is a higher-level wrapper around print_table() that handles:
    - Data transformation via row_transformer
    - Optional sorting
    - Summary line printing

    Args:
        data: Iterable of data objects to display
        columns: Column definitions for the table
        row_transformer: Function to convert data object to row mapping.
                        If None, assumes data objects are already mappings.
        sort_key: Optional function to sort data before display
        title: Optional table title
        summary_line: Optional summary line printed after the table
        terminal_width: Optional terminal width constraint
    """
    # Convert to list and optionally sort
    data_list = list(data)
    if sort_key:
        data_list.sort(key=sort_key)

    # Transform data to row mappings
    if row_transformer:
        rows = [row_transformer(item) for item in data_list]
    else:
        rows = data_list  # Assume already mappings

    # Print with spacing
    print()
    print_table(rows, columns, title=title, terminal_width=terminal_width)
    print()

    # Optional summary line
    if summary_line:
        print(summary_line)
