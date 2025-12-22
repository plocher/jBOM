#!/usr/bin/env python3
"""
Cache Preloader for jBOM Inventory Search Validation

This script pre-populates the search cache with generic component searches
to reduce API calls during validation and provide realistic cached data.
"""

import time
from pathlib import Path
import sys
import os

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from jbom.loaders.inventory import InventoryLoader
from jbom.search.mouser import MouserProvider
from enhanced_search_validation import SearchCache


def analyze_inventory_for_generic_searches(inventory_file: str) -> list:
    """Analyze inventory to determine useful generic searches."""

    # Load inventory
    inventory_path = Path(inventory_file)
    if not inventory_path.exists():
        print(f"ERROR: Inventory file not found: {inventory_path}")
        return []

    loader = InventoryLoader(inventory_path)
    inventory_items, field_names = loader.load()

    # Analyze component patterns
    component_patterns = {}

    for item in inventory_items:
        if not item.category or not item.value:
            continue

        # Check for DNP (Do Not Populate) field - best practice
        if (
            hasattr(item, "dnp")
            and item.dnp
            and str(item.dnp).upper() in ["TRUE", "1", "YES", "DNP"]
        ):
            continue
        if (
            hasattr(item, "exclude_from_bom")
            and item.exclude_from_bom
            and str(item.exclude_from_bom).upper() in ["TRUE", "1", "YES"]
        ):
            continue

        category = item.category.upper()
        # Expanded searchable categories
        searchable_categories = {
            "RES",
            "CAP",
            "IND",
            "LED",
            "DIO",
            "IC",
            "Q",
            "REG",
            "CON",
            "MCU",
            "RLY",
            "SWI",
        }
        if category not in searchable_categories:
            continue

        # Track packages for each category
        if category not in component_patterns:
            component_patterns[category] = {
                "packages": set(),
                "common_values": set(),
                "count": 0,
            }

        component_patterns[category]["count"] += 1

        if item.package:
            component_patterns[category]["packages"].add(item.package.strip())

        # Extract common patterns from values
        value = str(item.value).strip()
        if category == "RES" and (
            "k" in value.lower() or "ohm" in value.lower() or "Ω" in value
        ):
            # Common resistor values
            if "1k" in value or "1.0k" in value:
                component_patterns[category]["common_values"].add("1k")
            elif "10k" in value:
                component_patterns[category]["common_values"].add("10k")
            elif "100" in value and "k" not in value:
                component_patterns[category]["common_values"].add("100")
        elif category == "CAP" and ("uF" in value or "nF" in value or "pF" in value):
            # Common capacitor values
            if "0.1uF" in value or "100nF" in value:
                component_patterns[category]["common_values"].add("0.1uF")
            elif "1uF" in value:
                component_patterns[category]["common_values"].add("1uF")
            elif "10uF" in value:
                component_patterns[category]["common_values"].add("10uF")

    return component_patterns


def generate_cache_queries(component_patterns: dict) -> list:
    """Generate list of useful cache queries based on inventory analysis."""

    queries = []

    # Basic component type searches
    type_map = {
        "RES": "resistor",
        "CAP": "capacitor",
        "IND": "inductor",
        "LED": "led",
        "DIO": "diode",
        "IC": "ic",
        "Q": "transistor",
        "REG": "regulator",
        "CON": "connector",
        "MCU": "microcontroller",
        "RLY": "relay",
        "SWI": "switch",
    }

    for category, data in component_patterns.items():
        if data["count"] == 0:
            continue

        component_type = type_map.get(category, category.lower())

        # Generic type search
        queries.append(f"{component_type}")

        # Type + common packages
        for package in sorted(data["packages"]):
            if package and len(package) <= 8:  # Reasonable package names
                queries.append(f"{component_type} {package}")

        # Type + common values + packages
        for value in data["common_values"]:
            queries.append(f"{value} {component_type}")
            for package in sorted(list(data["packages"])[:2]):  # Top 2 packages
                if package and len(package) <= 8:
                    queries.append(f"{value} {component_type} {package}")

    # Remove duplicates and sort
    queries = sorted(list(set(queries)))

    print(f"Generated {len(queries)} cache queries:")
    for i, query in enumerate(queries, 1):
        print(f"  {i:2d}. '{query}'")

    return queries


def preload_search_cache(queries: list, limit: int = 10, delay: float = 1.5) -> dict:
    """Pre-load the search cache with the specified queries."""

    provider = MouserProvider()
    cache = SearchCache()

    stats = {
        "total_queries": len(queries),
        "successful": 0,
        "failed": 0,
        "total_results": 0,
        "api_calls": 0,
    }

    print(f"\nPreloading search cache with {len(queries)} queries...")
    print(f"Search limit per query: {limit}")
    print(f"API delay: {delay}s between calls")
    print("=" * 80)

    for i, query in enumerate(queries, 1):
        print(f"[{i:2d}/{len(queries)}] Searching: '{query}'", end=" ... ")

        # Check if already cached
        cached_results = cache.get(query, limit)
        if cached_results:
            print(f"ALREADY CACHED ({len(cached_results)} results)")
            continue

        try:
            # Perform search
            results = provider.search(query, limit=limit)
            stats["api_calls"] += 1

            if results:
                # Cache the results
                cache.put(query, limit, results)
                stats["successful"] += 1
                stats["total_results"] += len(results)
                print(f"✅ {len(results)} results cached")
            else:
                stats["failed"] += 1
                print(f"❌ No results")

        except Exception as e:
            stats["failed"] += 1
            print(f"🚨 ERROR: {e}")

        # Rate limiting
        if i < len(queries):  # Don't delay after last query
            time.sleep(delay)

    print("=" * 80)
    print("CACHE PRELOADING COMPLETE")
    print("=" * 80)
    print(f"Total queries processed: {stats['total_queries']}")
    print(f"Successful: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    print(f"Total results cached: {stats['total_results']}")
    print(f"API calls made: {stats['api_calls']}")

    if stats["successful"] > 0:
        avg_results = stats["total_results"] / stats["successful"]
        print(f"Average results per successful query: {avg_results:.1f}")

    # Explicitly save the cache
    cache.save_cache()

    return stats


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Pre-populate search cache for inventory validation"
    )
    parser.add_argument("inventory_file", help="Path to inventory file")
    parser.add_argument(
        "--limit", type=int, default=10, help="Search results per query (default: 10)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Delay between API calls in seconds (default: 1.5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show queries that would be cached without making API calls",
    )

    args = parser.parse_args()

    print("jBOM SEARCH CACHE PRELOADER")
    print("=" * 80)
    print(f"Inventory File: {args.inventory_file}")
    print(f"Search Limit: {args.limit}")
    print(f"API Delay: {args.delay}s")
    print(f"Dry Run: {args.dry_run}")
    print("")

    # Analyze inventory
    print("Analyzing inventory for cache-worthy searches...")
    component_patterns = analyze_inventory_for_generic_searches(args.inventory_file)

    if not component_patterns:
        print("No suitable components found for caching.")
        return

    print("\nComponent Analysis:")
    for category, data in component_patterns.items():
        print(
            f"  {category}: {data['count']} items, {len(data['packages'])} packages, {len(data['common_values'])} common values"
        )

    # Generate queries
    queries = generate_cache_queries(component_patterns)

    if args.dry_run:
        print(f"\nDRY RUN: Would cache {len(queries)} queries")
        print("Use --no-dry-run to actually populate the cache")
        return

    # Preload cache
    stats = preload_search_cache(queries, args.limit, args.delay)

    # Show cache status
    cache = SearchCache()
    print(f"\nFinal cache status:")
    print(f"Cache file: {cache.cache_file}")
    if cache.cache_file.exists():
        print(f"Cache file size: {cache.cache_file.stat().st_size} bytes")
    print(f"Ready for enhanced validation with pre-loaded cache!")


if __name__ == "__main__":
    main()
