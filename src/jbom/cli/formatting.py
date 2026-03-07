"""Shared console formatting utilities for CLI pretty printing.

Avoids DRY across bom/pos/inventory commands.

This module also provides a small generalized table formatter used by multiple
commands.
"""

from __future__ import annotations

import csv
import shutil
import sys
import textwrap
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
)


def get_terminal_width() -> int:
    """Return current terminal column width with a sensible fallback."""
    return shutil.get_terminal_size(fallback=(120, 24)).columns


@dataclass(frozen=True)
class Column:
    """Column definition for console tables."""

    header: str
    key: str
    preferred_width: Optional[int] = None
    wrap: bool = False
    fixed: bool = False
    align: str = "left"  # "left" or "right"


def _format_cell(text: str, *, width: int, align: str) -> str:
    if align == "right":
        return text.rjust(width)
    return text.ljust(width)


def _wrap_text(text: str, *, width: int) -> list[str]:
    if width <= 0:
        return [""]

    if not text:
        return [""]

    # Split on explicit newlines first so that "(Optional)\nIPN" renders as
    # two separate lines rather than being collapsed to "(Optional) IPN".
    result: list[str] = []
    for segment in text.split("\n"):
        if segment:
            result.extend(
                textwrap.wrap(
                    segment,
                    width=width,
                    break_long_words=True,
                    break_on_hyphens=False,
                    drop_whitespace=True,
                )
            )
        else:
            result.append("")
    return result or [""]


def _truncate(text: str, *, width: int, align: str) -> str:
    if width <= 0:
        return ""

    if len(text) <= width:
        return text

    # If we must truncate, prefer keeping the side nearest the alignment.
    if align == "right":
        return text[-width:]
    return text[:width]


def _column_min_width(col: Column) -> int:
    # Non-fixed columns must be allowed to shrink below header length.
    # Tests rely on preserving fixed-width numeric columns when shrinking.
    return 3


def _desired_width(col: Column, rows: Sequence[Mapping[str, Any]]) -> int:
    if col.preferred_width is not None:
        return max(1, col.preferred_width)

    # If no preferred width, size to header/data (bounded for sanity).
    max_data = 0
    for r in rows:
        v = str(r.get(col.key, ""))
        max_data = max(max_data, len(v))

    return max(1, min(max(len(col.header), max_data), 50))


def _compute_widths(
    *,
    columns: Sequence[Column],
    rows: Sequence[Mapping[str, Any]],
    terminal_width: Optional[int],
) -> list[int]:
    widths = [max(1, _desired_width(c, rows)) for c in columns]

    # Ensure fixed columns are at least their header width.
    for i, c in enumerate(columns):
        widths[i] = max(widths[i], len(c.header))

    if terminal_width is None:
        return widths

    if not columns:
        return []

    sep_width = 3 * (len(columns) - 1)  # " | " between columns
    max_cols_width = max(0, terminal_width - sep_width)

    # Fast path: already fits.
    if sum(widths) <= max_cols_width:
        return widths

    # Shrink only non-fixed columns first.
    min_widths = [
        (_column_min_width(c) if not c.fixed else widths[i])
        for i, c in enumerate(columns)
    ]

    # As a last resort, allow fixed columns to shrink too (down to header width)
    # if the terminal is extremely small.
    for i, c in enumerate(columns):
        if c.fixed:
            min_widths[i] = max(1, len(c.header))

    def total() -> int:
        return sum(widths)

    # 1) Shrink non-fixed columns as much as needed (down to min_widths).
    while total() > max_cols_width and any(
        (not c.fixed and widths[i] > min_widths[i]) for i, c in enumerate(columns)
    ):
        for i, c in enumerate(columns):
            if c.fixed:
                continue
            if widths[i] > min_widths[i] and total() > max_cols_width:
                widths[i] -= 1

    # 2) If still too wide, shrink fixed columns too (rare; extremely small terminal).
    while total() > max_cols_width and any(
        widths[i] > min_widths[i] for i in range(len(columns))
    ):
        for i in range(len(columns)):
            if widths[i] > min_widths[i] and total() > max_cols_width:
                widths[i] -= 1

    return widths


def print_table(
    rows: Sequence[Mapping[str, Any]],
    columns: Sequence[Column],
    *,
    terminal_width: Optional[int] = None,
    title: Optional[str] = None,
) -> None:
    """Print a list of row mappings as a formatted console table."""

    rows_list = list(rows)
    col_list = list(columns)

    widths = _compute_widths(
        columns=col_list, rows=rows_list, terminal_width=terminal_width
    )

    header_parts = [
        _format_cell(_truncate(c.header, width=w, align="left"), width=w, align="left")
        for c, w in zip(col_list, widths)
    ]
    header_line = " | ".join(header_parts)

    if title:
        underline_len = min(len(title), max(20, len(header_line)))
        print(title)
        print("=" * underline_len)

    print(header_line)

    if len(col_list) == 1:
        print("-" * widths[0])
    else:
        sep_parts = ["-" * w for w in widths]
        print("-+-".join(sep_parts))

    if len(col_list) == 1:
        row_sep = "-" * widths[0]
    else:
        row_sep = "-+-".join("-" * w for w in widths)

    for row in rows_list:
        # Build per-column wrapped cell lines.
        per_col_lines: list[list[str]] = []
        for c, w in zip(col_list, widths):
            raw = str(row.get(c.key, ""))
            if c.wrap:
                lines = _wrap_text(raw, width=w)
            else:
                lines = [_truncate(raw, width=w, align=c.align)]
            per_col_lines.append(lines)

        row_height = max((len(lines) for lines in per_col_lines), default=1)

        for line_idx in range(row_height):
            parts: list[str] = []
            for c, w, lines in zip(col_list, widths, per_col_lines):
                cell_text = lines[line_idx] if line_idx < len(lines) else ""
                parts.append(_format_cell(cell_text, width=w, align=c.align))
            print(" | ".join(parts))

        print(row_sep)


def print_tabular_data(
    data: Sequence[Any],
    columns: Sequence[Column],
    *,
    row_transformer: Optional[Callable[[Any], Mapping[str, Any]]] = None,
    sort_key: Optional[Callable[[Any], Any]] = None,
    terminal_width: Optional[int] = None,
    title: Optional[str] = None,
    summary_line: Optional[str] = None,
) -> None:
    """Print arbitrary tabular data with optional transformation and sorting."""

    items = list(data)
    if sort_key is not None:
        items.sort(key=sort_key)

    if row_transformer is None:
        rows = [
            (item if isinstance(item, Mapping) else {"value": str(item)})
            for item in items
        ]
    else:
        rows = [row_transformer(item) for item in items]

    print("")
    print_table(rows, columns, terminal_width=terminal_width, title=title)
    print("")

    if summary_line:
        print(summary_line)


# (preferred_width, wrap) hints for inventory console display.
# Path/ID fields are kept narrow and non-wrapping so they truncate cleanly;
# content fields wrap so descriptions/values are fully visible.
_INVENTORY_FIELD_WIDTHS: dict[str, tuple[int, bool]] = {
    "RowType": (10, False),
    "ComponentID": (28, False),
    "Project": (25, False),
    "ProjectName": (15, False),
    "UUID": (20, False),
    "SourceFile": (25, False),
    "Reference": (10, False),
    "Category": (10, False),
    "IPN": (20, False),
    "Value": (15, True),
    "Description": (35, True),
    "Inductance": (12, False),
    "Resistance": (12, False),
    "Capacitance": (12, False),
    "Package": (14, True),
    "Color": (10, False),
    "Tolerance": (10, False),
    "W": (8, False),
    "A": (8, False),
    "V": (8, False),
    "Temperature Coefficient": (22, False),
    "Voltage": (10, False),
    "Wavelength": (12, False),
    "mcd": (8, False),
    "Symbol": (20, False),
    "Footprint": (25, False),
    "Manufacturer": (16, True),
    "MFGPN": (16, False),
    "LCSC": (10, False),
    "Datasheet": (20, False),
}


def print_inventory_table(items: Iterable[dict], fieldnames: List[str]) -> None:
    """Pretty-print inventory rows as a formatted table to stdout.

    Renders every field in *fieldnames* order; terminal width constrains
    column widths automatically.  Falls back to raw CSV if fieldnames is empty.
    """

    items_list = list(items)

    if not fieldnames:
        writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
        writer.writeheader()
        for row in items_list:
            writer.writerow(row)
        return

    cols = [
        Column(
            header=f,
            key=f,
            preferred_width=_INVENTORY_FIELD_WIDTHS.get(f, (15, True))[0],
            wrap=_INVENTORY_FIELD_WIDTHS.get(f, (15, True))[1],
        )
        for f in fieldnames
    ]

    print(f"\nInventory: {len(items_list)} items")
    print_table(items_list, cols, terminal_width=get_terminal_width())


__all__ = [
    "Column",
    "get_terminal_width",
    "print_table",
    "print_tabular_data",
    "print_inventory_table",
]
