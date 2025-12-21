#!/usr/bin/env python3
"""
Real-world test workflow for jBOM search functionality.

Tests the search_parts API with components from the example inventory to:
1. Validate that search functionality works with real components
2. Identify gaps in search algorithms or inventory data quality
3. Find the "best" 3 Mouser parts for each inventory item
"""

import os
import sys
from pathlib import Path

# Add jBOM src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jbom.api import search_parts  # noqa: E402
from jbom.loaders.inventory import InventoryLoader  # noqa: E402


def test_search_workflow():
    """Test search functionality with real inventory components."""

    # Check for API key
    api_key = os.getenv("MOUSER_API_KEY")
    if not api_key:
        print("❌ MOUSER_API_KEY environment variable is required for this test")
        print("   Set it with: export MOUSER_API_KEY=your_api_key_here")
        return False

    # Load inventory
    inventory_path = Path(__file__).parent / "example-INVENTORY.numbers"
    print(f"📋 Loading inventory from: {inventory_path}")

    try:
        loader = InventoryLoader(inventory_path)
        items, field_names = loader.load()
        print(f"✅ Loaded {len(items)} inventory items")
    except Exception as e:
        print(f"❌ Error loading inventory: {e}")
        return False

    # Select representative components for testing
    # Focus on categories that should have good search results
    test_categories = ["RES", "CAP", "LED", "IC", "Q", "DIO"]
    test_components = []

    for category in test_categories:
        category_items = [item for item in items if item.category == category]
        if category_items:
            # Take first 2-3 items from each category
            test_components.extend(category_items[:2])

    print(f"\n🔍 Testing search for {len(test_components)} components:")

    results_summary = {
        "total_tested": 0,
        "successful_searches": 0,
        "failed_searches": 0,
        "empty_results": 0,
        "good_results": 0,  # Results with 3+ candidates
    }

    detailed_results = []

    for i, component in enumerate(test_components, 1):
        print(f"\n--- {i}/{len(test_components)}: {component.ipn} ---")
        print(f"Category: {component.category}")
        print(f"Value: {component.value}")
        print(f"Package: {component.package}")
        print(f"Existing MPN: {getattr(component, 'mfgpn', 'N/A')}")

        # Create search query
        # Try to build a good search query from available data
        search_terms = []
        if component.value and component.value not in ["", "N/A"]:
            search_terms.append(component.value)
        if component.package and component.package not in ["", "N/A"]:
            search_terms.append(component.package)

        # Add category-specific terms
        if component.category == "RES":
            search_terms.append("resistor")
        elif component.category == "CAP":
            search_terms.append("capacitor")
        elif component.category == "LED":
            search_terms.append("LED")
        elif component.category == "IC":
            search_terms.append("IC")

        query = " ".join(search_terms)
        if not query.strip():
            print("⚠️  Skipping - insufficient data for search query")
            continue

        print(f"Search Query: '{query}'")

        results_summary["total_tested"] += 1

        try:
            # Search for 3 best parts
            search_results = search_parts(
                query=query,
                provider="mouser",
                limit=3,
                api_key=api_key,
                filter_parametric=True,
            )

            results_summary["successful_searches"] += 1

            if not search_results:
                print("❌ No results found")
                results_summary["empty_results"] += 1
            else:
                print(f"✅ Found {len(search_results)} results:")
                if len(search_results) >= 3:
                    results_summary["good_results"] += 1

                for j, result in enumerate(search_results, 1):
                    print(f"  {j}. {result.manufacturer} {result.mpn}")
                    print(f"     Description: {result.description}")
                    print(f"     Price: ${result.price if result.price else 'N/A'}")
                    print(
                        f"     Stock: {result.stock_quantity if hasattr(result, 'stock_quantity') else 'N/A'}"
                    )
                    print(f"     Mouser P/N: {result.distributor_part_number}")

                # Store detailed result for analysis
                detailed_results.append(
                    {
                        "component": component,
                        "query": query,
                        "results_count": len(search_results),
                        "results": search_results,
                    }
                )

        except Exception as e:
            print(f"❌ Search failed: {e}")
            results_summary["failed_searches"] += 1

        # Add delay to be respectful of API limits
        import time

        time.sleep(1)

    # Print summary
    print("\n" + "=" * 60)
    print("🎯 SEARCH WORKFLOW RESULTS SUMMARY")
    print("=" * 60)
    print(f"Total components tested: {results_summary['total_tested']}")
    print(f"Successful searches: {results_summary['successful_searches']}")
    print(f"Failed searches: {results_summary['failed_searches']}")
    print(f"Empty results: {results_summary['empty_results']}")
    print(f"Good results (3+ parts): {results_summary['good_results']}")

    if results_summary["total_tested"] > 0:
        success_rate = (
            results_summary["successful_searches"] / results_summary["total_tested"]
        ) * 100
        good_rate = (
            results_summary["good_results"] / results_summary["total_tested"]
        ) * 100
        print(f"\nSuccess rate: {success_rate:.1f}%")
        print(f"Good results rate: {good_rate:.1f}%")

        # Identify potential improvements
        print("\n🔧 POTENTIAL IMPROVEMENTS:")

        if results_summary["empty_results"] > 0:
            print(f"- {results_summary['empty_results']} searches returned no results")
            print("  → Consider improving search query generation")
            print("  → Some inventory items may need better component data")

        if results_summary["failed_searches"] > 0:
            print(f"- {results_summary['failed_searches']} searches failed")
            print("  → Check API connectivity and rate limits")

        poor_results = (
            results_summary["successful_searches"] - results_summary["good_results"]
        )
        if poor_results > 0:
            print(f"- {poor_results} searches found fewer than 3 results")
            print("  → Search queries may be too specific")
            print("  → Consider broader search terms or better fallback queries")

    return True


if __name__ == "__main__":
    print("🚀 jBOM Search Functionality Real-World Test")
    print("=" * 50)

    if test_search_workflow():
        print("\n✅ Test workflow completed successfully!")
    else:
        print("\n❌ Test workflow failed!")
        sys.exit(1)
