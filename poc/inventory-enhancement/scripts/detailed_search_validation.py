#!/usr/bin/env python3
"""
Detailed Search Validation Report

Generates a line-by-line report of inventory items, search terms used,
and search results to identify methodology issues and validate search quality.
"""

import sys
import time
from pathlib import Path

# Add jBOM to path
sys.path.insert(0, "/Users/jplocher/Dropbox/KiCad/jBOM/src")

from jbom.loaders.inventory import InventoryLoader
from jbom.search.mouser import MouserProvider
from jbom.processors.search_result_scorer import SearchResultScorer


def normalize_value(value: str) -> str:
    """Normalize component values to ASCII equivalents."""
    if not value:
        return ""

    # Replace Unicode symbols with ASCII equivalents
    normalized = value.replace("Ω", "").replace("ω", "")
    normalized = normalized.replace("µF", "uF").replace("μF", "uF")
    normalized = normalized.replace("pF", "pF").replace("nF", "nF")

    # Clean up extra whitespace
    return normalized.strip()


def build_search_query(item) -> str:
    """Build search query from inventory item."""
    parts = []

    # Normalize value - convert Unicode symbols to ASCII
    if item.value:
        value = normalize_value(item.value)
        parts.append(value)

    # Add component type keyword
    if item.category:
        type_keywords = {
            "RES": "resistor",
            "CAP": "capacitor",
            "IND": "inductor",
            "LED": "LED",
            "DIO": "diode",
            "IC": "IC",
            "Q": "transistor",
            "REG": "regulator",
        }
        if item.category.upper() in type_keywords:
            parts.append(type_keywords[item.category.upper()])

    # Add package info
    if item.package:
        parts.append(item.package)

    # Add tolerance if meaningful
    if item.tolerance and item.tolerance not in ["", "N/A"]:
        parts.append(item.tolerance)

    return " ".join(parts)


def filter_searchable_items(items):
    """Filter for searchable items."""
    searchable = []
    searchable_categories = {
        "RES",
        "CAP",
        "IND",
        "LED",
        "DIO",
        "IC",
        "Q",
        "REG",
        "OSC",
        "FER",
        "CONN",
    }

    for item in items:
        # Skip items without meaningful search criteria
        if not item.value or not item.category:
            continue

        # Skip empty or very short values
        if len(str(item.value).strip()) < 2:
            continue

        # Skip silkscreen, board outlines, etc.
        if item.category and item.category.upper() in ["SLK", "BOARD", "DOC", "MECH"]:
            continue

        # Include if category matches target
        if item.category and item.category.upper() in searchable_categories:
            searchable.append(item)

    return searchable


def generate_validation_report(inventory_file: str, limit: int = 5):
    """Generate detailed validation report."""

    print("=" * 100)
    print("DETAILED INVENTORY SEARCH VALIDATION REPORT")
    print("=" * 100)
    print(f"Inventory File: {inventory_file}")
    print(f"Search Limit: {limit} results per item")
    print(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("")

    # Load inventory
    inventory_path = Path(inventory_file)
    if not inventory_path.exists():
        print(f"ERROR: Inventory file not found: {inventory_path}")
        return

    loader = InventoryLoader(inventory_path)
    inventory_items, field_names = loader.load()
    print(f"Total inventory items loaded: {len(inventory_items)}")

    # Filter searchable items
    searchable_items = filter_searchable_items(inventory_items)
    print(f"Searchable electronic components: {len(searchable_items)}")
    print("")

    # Initialize search provider
    try:
        search_provider = MouserProvider()
        print(f"Search Provider: {search_provider.name}")
    except ValueError as e:
        print(f"ERROR: Could not initialize search provider: {e}")
        return

    # Initialize scorer
    scorer = SearchResultScorer()

    # Process each item with detailed reporting
    print("=" * 100)
    print("LINE-BY-LINE SEARCH ANALYSIS")
    print("=" * 100)

    success_count = 0
    total_count = 0

    # Group by category for better organization
    by_category = {}
    for item in searchable_items:
        cat = item.category.upper()
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(item)

    for category in sorted(by_category.keys()):
        items = by_category[category]
        print(f"\n📂 CATEGORY: {category} ({len(items)} items)")
        print("-" * 80)

        for i, item in enumerate(items, 1):
            total_count += 1
            print(f"\n[{total_count}] IPN: {item.ipn}")
            print(f"    Original Value: '{item.value}'")
            print(f"    Package: {item.package or 'N/A'}")
            print(f"    Tolerance: {item.tolerance or 'N/A'}")
            print(f"    Description: {item.description or 'N/A'}")

            # Build search query
            query = build_search_query(item)
            print(f"    🔍 Search Query: '{query}'")

            # Perform search
            try:
                search_results = search_provider.search(query, limit=limit)

                if search_results:
                    success_count += 1
                    print(f"    ✅ Found {len(search_results)} results")

                    # Mock component for scoring
                    class MockComponent:
                        def __init__(self, item):
                            self.value = item.value or ""
                            self.footprint = item.package or ""
                            self.lib_id = (
                                f"{item.category or 'UNKNOWN'}:{item.ipn or 'UNKNOWN'}"
                            )
                            self.properties = {
                                "Tolerance": item.tolerance or "",
                                "Voltage": item.voltage or "",
                                "Power": item.wattage or "",
                                "Type": item.type or "",
                            }

                    mock_component = MockComponent(item)

                    # Score and display results
                    for j, result in enumerate(search_results, 1):
                        priority = scorer.calculate_priority(mock_component, result)
                        print(f"        [{j}] {result.manufacturer} {result.mpn}")
                        print(
                            f"            Distributor PN: {result.distributor_part_number}"
                        )
                        print(f"            Price: {result.price}")
                        print(f"            Availability: {result.availability}")
                        print(f"            Description: {result.description}")
                        print(f"            Priority Score: {priority}")

                        # Show key attributes if available
                        key_attrs = [
                            "Resistance",
                            "Capacitance",
                            "Voltage",
                            "Tolerance",
                            "Package",
                        ]
                        attrs = []
                        for attr in key_attrs:
                            if attr in result.attributes:
                                attrs.append(f"{attr}: {result.attributes[attr]}")
                        if attrs:
                            print(f"            Attributes: {', '.join(attrs)}")
                else:
                    print(f"    ❌ No results found")
                    print(f"    💡 Possible issues:")

                    # Analyze potential issues
                    issues = []
                    if any(ord(c) > 127 for c in query):
                        issues.append("Query contains Unicode characters")
                    if not item.package:
                        issues.append("Missing package information")
                    if not item.tolerance:
                        issues.append("Missing tolerance information")
                    if len(item.value.strip()) < 3:
                        issues.append("Very short/generic value")

                    for issue in issues:
                        print(f"        - {issue}")

                    if not issues:
                        print("        - Search terms may be too specific or uncommon")
                        print(
                            "        - Component may not be available from this distributor"
                        )

            except Exception as e:
                print(f"    🚨 Search Error: {e}")

            # Rate limiting
            time.sleep(1.0)

    # Summary
    print("\n" + "=" * 100)
    print("VALIDATION SUMMARY")
    print("=" * 100)
    print(f"Total searchable items: {total_count}")
    print(f"Successful searches: {success_count}")
    print(f"Failed searches: {total_count - success_count}")
    print(f"Success rate: {100 * success_count / total_count:.1f}%")

    # Analysis by category
    print(f"\nBY CATEGORY:")
    category_stats = {}
    for category in sorted(by_category.keys()):
        items = by_category[category]
        category_stats[category] = {
            "total": len(items),
            "searched": len(items),  # All were searched in this analysis
        }
        print(f"  {category}: {len(items)} items")

    print(f"\nRECOMMENDations:")
    print("- Items with 0 results may need more specific search terms")
    print("- Items with many results indicate good search term quality")
    print("- Check Unicode characters in failed searches")
    print("- Verify package and tolerance information completeness")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate detailed search validation report"
    )
    parser.add_argument("inventory_file", help="Path to inventory file")
    parser.add_argument(
        "--limit", type=int, default=3, help="Search results per item (default: 3)"
    )
    parser.add_argument(
        "--categories",
        help="Comma-separated list of categories to test (e.g., 'RES,CAP')",
    )

    args = parser.parse_args()

    generate_validation_report(args.inventory_file, args.limit)


if __name__ == "__main__":
    main()
