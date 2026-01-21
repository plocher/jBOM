"""Shared console formatting utilities for CLI pretty printing.

Avoids DRY across bom/pos/inventory commands.
"""
from __future__ import annotations

import csv
import sys
from typing import Iterable, List

from jbom.services.bom_generator import BOMData


def print_bom_table(bom_data: BOMData) -> None:
    """Pretty-print BOM as a formatted table to stdout."""
    print(f"\n{bom_data.project_name} - Bill of Materials")
    print("=" * 60)

    if not bom_data.entries:
        print("No components found.")
        return

    print(f"{'References':<15} {'Value':<12} {'Footprint':<20} {'Qty':<4}")
    print("-" * 60)

    for entry in bom_data.entries:
        refs = entry.references_string
        if len(refs) > 14:
            refs = refs[:14] + "..."
        value = entry.value
        if len(value) > 11:
            value = value[:11] + "..."
        footprint = entry.footprint
        if len(footprint) > 19:
            footprint = footprint[:19] + "..."
        print(f"{refs:<15} {value:<12} {footprint:<20} {entry.quantity:<4}")

    print(
        f"\nTotal: {bom_data.total_components} components, {bom_data.total_line_items} unique items"
    )

    if "matched_entries" in bom_data.metadata:
        matched = bom_data.metadata["matched_entries"]
        print(
            f"Inventory enhanced: {matched}/{bom_data.total_line_items} items matched"
        )


def print_pos_table(pos_data: List[dict], units: str) -> None:
    """Pretty-print POS data as a formatted table to stdout."""
    print(f"\nComponent Placement Data ({len(pos_data)} components)")
    print("=" * 80)

    if not pos_data:
        print("No components found.")
        return

    unit_label = "mm" if units == "mm" else "in"
    print(
        f"{'Ref':<10} {'X(' + unit_label + ')':<12} {'Y(' + unit_label + ')':<12} {'Rot':<6} {'Side':<6} {'Package':<15}"
    )
    print("-" * 80)

    for e in pos_data:
        x = f"{e['x_mm']:.3f}" if units == "mm" else f"{e['x_mm']/25.4:.4f}"
        y = f"{e['y_mm']:.3f}" if units == "mm" else f"{e['y_mm']/25.4:.4f}"
        ref = e["reference"]
        if len(ref) > 9:
            ref = ref[:9] + "..."
        pkg = e["package"]
        if len(pkg) > 14:
            pkg = pkg[:14] + "..."
        print(
            f"{ref:<10} {x:<12} {y:<12} {e['rotation']:<6.1f} {e['side']:<6} {pkg:<15}"
        )

    print(f"\nTotal: {len(pos_data)} components")


def print_inventory_table(items: Iterable[dict], fieldnames: List[str]) -> None:
    """Pretty-print inventory rows as a compact table to stdout.

    Shows a curated subset if available; otherwise falls back to CSV to stdout.
    """
    subset = [
        f
        for f in ("IPN", "Category", "Value", "Description", "Package")
        if f in fieldnames
    ]
    if not subset:
        # Fall back to CSV to stdout
        writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
        writer.writeheader()
        for row in items:
            writer.writerow(row)
        return

    print(
        f"\nInventory: {sum(1 for _ in items)} items"
    )  # consume generator? ensure list first
    items = list(items)
    print("=" * 100)
    # Header row
    h1 = subset[0]
    h2 = subset[1] if len(subset) > 1 else ""
    h3 = subset[2] if len(subset) > 2 else ""
    h4 = subset[3] if len(subset) > 3 else ""
    print(f"{h1:<20} {h2:<15} {h3:<15} {h4:<40}")
    print("-" * 100)
    for row in items:
        cols = [str(row.get(k, "")) for k in subset]
        # Truncate description for display
        if len(cols) >= 4 and len(cols[3]) > 39:
            cols[3] = cols[3][:39] + "..."
        c1 = cols[0]
        c2 = cols[1] if len(cols) > 1 else ""
        c3 = cols[2] if len(cols) > 2 else ""
        c4 = cols[3] if len(cols) > 3 else ""
        print(f"{c1:<20} {c2:<15} {c3:<15} {c4:<40}")
