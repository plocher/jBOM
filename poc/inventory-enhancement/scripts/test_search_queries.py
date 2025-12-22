#!/usr/bin/env python3
"""
Test script to validate improved search query building logic
"""

import sys
from pathlib import Path

# Add jBOM to path
sys.path.insert(0, "/Users/jplocher/Dropbox/KiCad/jBOM/src")

from jbom.loaders.inventory import InventoryLoader
from enhanced_search_validation import build_enhanced_search_query


def test_search_query_building():
    """Test the improved search query building on sample inventory items."""

    # Load inventory
    inventory_path = Path("examples/example-INVENTORY.csv")
    loader = InventoryLoader(inventory_path)
    inventory_items, field_names = loader.load()

    # Test specific problematic items
    test_items = [
        ("SWI_EDG-104", "Should use description or smart DIP switch detection"),
        ("SWI_6x6x6mm_PTH", "Should use description for tactile switch"),
        ("CON_TC2030-NL", "Should use description for Tag Connect"),
        ("CAP_0.01uF_0603", "Should use traditional value-based approach"),
    ]

    print("SEARCH QUERY BUILDING TEST")
    print("=" * 80)

    for target_ipn, expected_behavior in test_items:
        # Find the item
        item = None
        for inv_item in inventory_items:
            if inv_item.ipn == target_ipn:
                item = inv_item
                break

        if not item:
            print(f"⚠️  Could not find item: {target_ipn}")
            continue

        print(f"\n📋 Item: {item.ipn}")
        print(f"   Category: {item.category}")
        print(f"   Value: '{item.value}'")
        print(f"   Type: '{getattr(item, 'type', 'N/A')}'")
        print(f"   Description: '{getattr(item, 'description', 'N/A')}'")
        print(
            f"   MPN: {getattr(item, 'manufacturer', '?')} {getattr(item, 'mfgpn', 'N/A')}"
        )

        # Build queries
        primary_query, fallback_query = build_enhanced_search_query(item)

        print(f"   🔍 Primary Query (MPN): '{primary_query}'")
        print(f"   🔍 Fallback Query: '{fallback_query}'")
        print(f"   📝 Expected: {expected_behavior}")

        # Validate improvement
        if target_ipn == "SWI_EDG-104":
            if (
                "4 Position DIP Switch" in fallback_query
                or "SPST x4 DIP Switch" in fallback_query
            ):
                print(f"   ✅ IMPROVED: Query now descriptive")
            else:
                print(f"   ❌ NEEDS WORK: Query not descriptive enough")
        elif target_ipn == "SWI_6x6x6mm_PTH":
            if "Tactile Switch" in fallback_query or "Momentary" in fallback_query:
                print(f"   ✅ IMPROVED: Query identifies tactile switch")
            else:
                print(f"   ❌ NEEDS WORK: Query doesn't identify switch type")
        elif target_ipn == "CON_TC2030-NL":
            if "Tag Connect" in fallback_query or "6-pin" in fallback_query:
                print(f"   ✅ IMPROVED: Query uses descriptive text")
            else:
                print(f"   ❌ NEEDS WORK: Query not descriptive enough")


if __name__ == "__main__":
    test_search_query_building()
