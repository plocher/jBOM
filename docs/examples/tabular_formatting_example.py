#!/usr/bin/env python3
"""
Example demonstrating how to use the generalized tabular data formatting system.

This shows how any plugin can easily create nicely formatted console tables
without duplicating formatting logic.
"""

from jbom.cli.formatting import Column, print_tabular_data


class Component:
    """Example component data structure."""

    def __init__(self, reference, value, package, quantity):
        self.reference = reference
        self.value = value
        self.package = package
        self.quantity = quantity


def demo_basic_table():
    """Demonstrate basic table formatting with data transformation."""
    print("=== Basic Table Example ===")

    # Sample component data
    components = [
        Component("R1", "10K", "0805", 1),
        Component("R2", "10K", "0805", 1),
        Component("C1", "100nF", "0603", 1),
        Component("U1", "ATmega328P", "TQFP-32", 1),
    ]

    # Define columns for display
    columns = [
        Column("Reference", "ref", wrap=False, preferred_width=10, align="left"),
        Column("Value", "value", wrap=True, preferred_width=15, align="left"),
        Column("Package", "pkg", wrap=False, preferred_width=10, align="left"),
        Column("Qty", "qty", wrap=False, preferred_width=5, align="right"),
    ]

    # Transform component objects to row mappings
    def component_to_row(comp):
        return {
            "ref": comp.reference,
            "value": comp.value,
            "pkg": comp.package,
            "qty": str(comp.quantity),
        }

    # Print formatted table
    print_tabular_data(
        data=components,
        columns=columns,
        row_transformer=component_to_row,
        sort_key=lambda c: c.reference,
        title="Component List",
        summary_line=f"Total: {len(components)} unique components",
    )


def demo_aggregated_table():
    """Demonstrate aggregated data with custom formatting."""
    print("=== Aggregated Table Example ===")

    # Sample BOM-style aggregated data
    bom_data = [
        {"refs": ["R1", "R2", "R3"], "value": "10K", "package": "0805", "qty": 3},
        {"refs": ["C1"], "value": "100nF", "package": "0603", "qty": 1},
        {"refs": ["U1"], "value": "ATmega328P", "package": "TQFP-32", "qty": 1},
    ]

    # Define columns for BOM display
    columns = [
        Column("References", "refs", wrap=True, preferred_width=20, align="left"),
        Column("Value", "value", wrap=True, preferred_width=15, align="left"),
        Column("Package", "pkg", wrap=False, preferred_width=10, align="left"),
        Column("Qty", "qty", wrap=False, preferred_width=5, align="right"),
    ]

    # Transform aggregated data to row mappings
    def bom_to_row(item):
        refs_str = ", ".join(item["refs"])
        return {
            "refs": refs_str,
            "value": item["value"],
            "pkg": item["package"],
            "qty": str(item["qty"]),
        }

    # Print formatted table
    print_tabular_data(
        data=bom_data,
        columns=columns,
        row_transformer=bom_to_row,
        sort_key=lambda item: len(item["refs"]),  # Sort by number of refs
        title="Bill of Materials",
        summary_line=f"Total line items: {len(bom_data)}",
    )


if __name__ == "__main__":
    demo_basic_table()
    print()
    demo_aggregated_table()
