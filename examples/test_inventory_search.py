#!/usr/bin/env python3
"""
Test search functionality with entire inventory - Python API version.

Iterates through every item in the example inventory and uses search_parts()
to find the 3 best Mouser parts for each item. This exposes both:
1. Inventory data quality issues
2. Search algorithm limitations
"""

import os
import sys
import time
from pathlib import Path

# Add jBOM src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jbom.api import search_parts  # noqa: E402
from jbom.loaders.inventory import InventoryLoader  # noqa: E402


def build_search_query(item):
    """Build search query from inventory item data."""
    terms = []

    # Use existing MPN if available (best case)
    mpn = getattr(item, "mfgpn", "")
    if mpn and mpn not in ["", "N/A"]:
        return mpn, "mpn"

    # Build from component data
    if item.value and item.value not in ["", "N/A"]:
        # Skip obvious non-components
        if not any(bad in item.value.upper() for bad in ["BRD_", "DCPower", "EDG-104"]):
            terms.append(item.value)

    if item.package and item.package not in ["", "N/A"]:
        # Add common package types
        if any(
            pkg in item.package.upper()
            for pkg in ["0603", "0805", "1206", "SOT", "SOP", "SOIC"]
        ):
            terms.append(item.package)

    # Add category-specific terms
    category_terms = {
        "RES": "resistor",
        "CAP": "capacitor",
        "LED": "LED",
        "IC": "integrated circuit",
        "Q": "transistor",
        "DIO": "diode",
        "REG": "voltage regulator",
        "MCU": "microcontroller",
    }
    if item.category in category_terms:
        terms.append(category_terms[item.category])

    return " ".join(terms) if terms else "", "constructed"


def main():
    """Run the inventory search test."""
    print("🔍 jBOM Inventory Search Test - Python API")
    print("=" * 50)

    # Check API key
    api_key = os.getenv("MOUSER_API_KEY")
    if not api_key:
        print("❌ MOUSER_API_KEY environment variable required")
        print("   Set it with: export MOUSER_API_KEY=your_key")
        return 1

    # Load inventory
    inventory_path = Path(__file__).parent / "example-INVENTORY.numbers"
    try:
        loader = InventoryLoader(inventory_path)
        items, _ = loader.load()
        print(f"✅ Loaded {len(items)} inventory items")
    except Exception as e:
        print(f"❌ Error loading inventory: {e}")
        return 1

    # Test every item
    print(f"\n🎯 Testing search_parts() API for all {len(items)} items...")

    stats = {
        "total": len(items),
        "searched": 0,
        "successful": 0,
        "good_results": 0,
        "no_query": 0,
        "no_results": 0,
        "errors": 0,
    }

    category_stats = {}

    for i, item in enumerate(items, 1):
        print(f"\n--- {i}/{len(items)}: {item.ipn} ({item.category}) ---")

        # Track by category
        if item.category not in category_stats:
            category_stats[item.category] = {"total": 0, "successful": 0, "good": 0}
        category_stats[item.category]["total"] += 1

        # Build query
        query, strategy = build_search_query(item)
        if not query:
            print("⚠️  No searchable data")
            stats["no_query"] += 1
            continue

        print(f"Query: '{query}' ({strategy})")
        stats["searched"] += 1

        try:
            # Search for 3 best parts - this is the core test!
            results = search_parts(
                query=query, provider="mouser", limit=3, api_key=api_key
            )

            if not results:
                print("❌ No results")
                stats["no_results"] += 1
            else:
                stats["successful"] += 1
                category_stats[item.category]["successful"] += 1

                print(f"✅ Found {len(results)} results:")
                for j, result in enumerate(results, 1):
                    print(
                        f"  {j}. {result.manufacturer} {result.mpn} - ${result.price or 'N/A'}"
                    )

                if len(results) >= 3:
                    stats["good_results"] += 1
                    category_stats[item.category]["good"] += 1

        except Exception as e:
            print(f"❌ Search failed: {e}")
            stats["errors"] += 1

        # Rate limiting
        time.sleep(0.5)

    # Results summary
    print("\n" + "=" * 60)
    print("📊 PYTHON API TEST RESULTS")
    print("=" * 60)

    print(f"Total items: {stats['total']}")
    print(f"Items searched: {stats['searched']}")
    print(f"Successful searches: {stats['successful']}")
    print(f"Good results (3+ parts): {stats['good_results']}")
    print(f"No searchable data: {stats['no_query']}")
    print(f"No results found: {stats['no_results']}")
    print(f"Search errors: {stats['errors']}")

    if stats["searched"] > 0:
        success_rate = stats["successful"] / stats["searched"] * 100
        good_rate = stats["good_results"] / stats["searched"] * 100
        print(f"\nSuccess rate: {success_rate:.1f}%")
        print(f"Good results rate: {good_rate:.1f}%")

    # Category breakdown
    print("\n📈 RESULTS BY CATEGORY:")
    for cat, cat_stats in sorted(category_stats.items()):
        if cat_stats["total"] > 0:
            success_pct = cat_stats["successful"] / cat_stats["total"] * 100
            good_pct = cat_stats["good"] / cat_stats["total"] * 100
            print(
                f"{cat:4} ({cat_stats['total']:2}): {success_pct:5.1f}% success, {good_pct:5.1f}% good"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
