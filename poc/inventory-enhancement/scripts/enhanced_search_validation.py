#!/usr/bin/env python3
"""
Enhanced Search Validation with MPN Priority and Bulk Pricing

Improved validation that:
1. Uses existing Manufacturer/MFGPN data when available
2. Focuses on bulk pricing (reel/thousand quantities)
3. Validates that existing parts appear in search results
"""

import sys
import time
import json
import hashlib
from pathlib import Path

# Add jBOM to path
sys.path.insert(0, "/Users/jplocher/Dropbox/KiCad/jBOM/src")

from jbom.loaders.inventory import InventoryLoader
from jbom.search.mouser import MouserProvider
from jbom.processors.search_result_scorer import SearchResultScorer


class SearchCache:
    """Intelligent search cache to reduce API calls."""

    def __init__(self, cache_file: str = "search_cache.json"):
        self.cache_file = Path(cache_file)
        self.cache = {}
        self.load_cache()
        self.hits = 0
        self.misses = 0

    def load_cache(self):
        """Load existing cache from file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    self.cache = json.load(f)
                print(
                    f"Loaded {len(self.cache)} cached searches from {self.cache_file}"
                )
            except Exception as e:
                print(f"Warning: Could not load cache: {e}")
                self.cache = {}

    def save_cache(self):
        """Save cache to file."""
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.cache, f, indent=2)
            print(f"Saved {len(self.cache)} searches to cache")
        except Exception as e:
            print(f"Warning: Could not save cache: {e}")

    def __del__(self):
        """Auto-save cache when object is destroyed."""
        if hasattr(self, "cache") and self.cache:
            self.save_cache()

    def _make_key(self, query: str, limit: int) -> str:
        """Create cache key from query and limit."""
        # Normalize query for better cache hits
        normalized_query = query.strip().lower()
        return hashlib.md5(f"{normalized_query}:{limit}".encode()).hexdigest()

    def get(self, query: str, limit: int) -> list:
        """Get cached search results."""
        key = self._make_key(query, limit)
        if key in self.cache:
            self.hits += 1
            print(f"    💾 Cache HIT: '{query}'")
            # Convert back to SearchResult-like objects
            return self._deserialize_results(self.cache[key])
        else:
            self.misses += 1
            return None

    def put(self, query: str, limit: int, results: list):
        """Store search results in cache."""
        key = self._make_key(query, limit)
        self.cache[key] = self._serialize_results(results)
        print(f"    💾 Cached: '{query}' ({len(results)} results)")

    def _serialize_results(self, results: list) -> list:
        """Convert SearchResult objects to serializable format."""
        serialized = []
        for result in results:
            serialized.append(
                {
                    "manufacturer": result.manufacturer,
                    "mpn": result.mpn,
                    "description": result.description,
                    "datasheet": result.datasheet,
                    "distributor": result.distributor,
                    "distributor_part_number": result.distributor_part_number,
                    "availability": result.availability,
                    "price": result.price,
                    "details_url": result.details_url,
                    "raw_data": result.raw_data,
                    "lifecycle_status": result.lifecycle_status,
                    "min_order_qty": result.min_order_qty,
                    "category": result.category,
                    "attributes": result.attributes,
                    "stock_quantity": result.stock_quantity,
                }
            )
        return serialized

    def _deserialize_results(self, serialized: list) -> list:
        """Convert serialized format back to SearchResult objects."""
        # Import here to avoid circular imports
        from jbom.search import SearchResult

        results = []
        for data in serialized:
            result = SearchResult(
                manufacturer=data.get("manufacturer", ""),
                mpn=data.get("mpn", ""),
                description=data.get("description", ""),
                datasheet=data.get("datasheet", ""),
                distributor=data.get("distributor", ""),
                distributor_part_number=data.get("distributor_part_number", ""),
                availability=data.get("availability", ""),
                price=data.get("price", ""),
                details_url=data.get("details_url", ""),
                raw_data=data.get("raw_data", {}),
                lifecycle_status=data.get("lifecycle_status", ""),
                min_order_qty=data.get("min_order_qty", 1),
                category=data.get("category", ""),
                attributes=data.get("attributes", {}),
                stock_quantity=data.get("stock_quantity", 0),
            )
            results.append(result)
        return results

    def get_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "total_entries": len(self.cache),
            "cache_hits": self.hits,
            "cache_misses": self.misses,
            "hit_rate": self.hits / (self.hits + self.misses) * 100
            if (self.hits + self.misses) > 0
            else 0,
        }


def normalize_value(value: str) -> str:
    """Normalize component values to ASCII equivalents."""
    if not value:
        return ""

    # Replace Unicode symbols with ASCII equivalents
    normalized = value.replace("Ω", "").replace("ω", "")
    normalized = normalized.replace("µF", "uF").replace("μF", "uF")
    normalized = normalized.replace("pF", "pF").replace("nF", "nF")

    return normalized.strip()


def sanitize_search_query(query: str) -> str:
    """Sanitize search query to prevent API 400 errors."""
    if not query:
        return ""

    # Remove problematic characters that cause Mouser API 400 errors
    sanitized = query

    # Remove Unicode trademark symbols that cause issues
    for ch in ["™", "®", "©"]:
        sanitized = sanitized.replace(ch, "")

    # Strip quotes and exotic punctuation
    for ch in ['"', "'", "“", "”", "’", "‘"]:
        sanitized = sanitized.replace(ch, "")

    # Replace multiple spaces with single space
    sanitized = " ".join(sanitized.split())

    # Limit length to prevent overly long queries
    if len(sanitized) > 100:
        sanitized = sanitized[:97] + "..."

    return sanitized.strip()


def analyze_inventory_item_issues(item) -> dict:
    """Analyze inventory item for potential distributor compatibility issues."""
    issues = {
        "specialty_supplier": False,
        "regional_supplier": False,
        "development_tool": False,
        "recommendations": [],
    }

    # Check for specialty suppliers that aren't available through major distributors
    if hasattr(item, "manufacturer") and item.manufacturer:
        mfg = item.manufacturer.strip().upper()
        if "TAG CONNECT" in mfg:
            issues["specialty_supplier"] = True
            issues["recommendations"].append(
                "Tag-Connect: Purchase directly from tag-connect.com"
            )
        elif "HANXIA" in mfg or "CAL-CHIP" in mfg:
            issues["regional_supplier"] = True
            issues["recommendations"].append(
                "LCSC/JLC part - may need equivalent from US distributor"
            )

    # Check for development tools vs production components
    if hasattr(item, "description") and item.description:
        desc = item.description.upper()
        if "PROGRAMMING" in desc or "DEBUG" in desc or "DEVELOPMENT" in desc:
            issues["development_tool"] = True
            issues["recommendations"].append(
                "Development tool - may not need production sourcing"
            )

    # Check for DNP items that shouldn't be searched
    if (
        hasattr(item, "dnp")
        and item.dnp
        and str(item.dnp).upper() in ["TRUE", "1", "YES", "DNP"]
    ):
        issues["recommendations"].append("DNP component - should not be sourced")

    return issues


def build_enhanced_search_query(item) -> tuple[str, str]:
    """Build enhanced search query with MPN priority.

    Returns:
        Tuple of (primary_query, fallback_query)
    """
    # Primary: Use MPN if available
    if item.mfgpn and item.mfgpn.strip():
        primary_query = item.mfgpn.strip()

        # Add manufacturer for disambiguation if available
        if item.manufacturer and item.manufacturer.strip():
            primary_query = f"{item.manufacturer.strip()} {primary_query}"
    else:
        primary_query = None

    # Fallback: Build from component characteristics with enhanced logic
    parts = []

    # Use Description field if available (preferred for better search results)
    if hasattr(item, "description") and item.description and item.description.strip():
        desc = item.description.strip()
        # For specific component types, use description directly if it's detailed
        if item.category and item.category.upper() in ["SWI", "CON", "RLY", "MCU"]:
            # Clean up description for search and truncate if too long
            cleaned_desc = desc.replace("PTH", "").replace("SMD", "").strip()

            # Special handling for known specialty suppliers
            if "Tag Connect" in cleaned_desc:
                # Tag Connect is specialty supplier - simplify search
                if "No Legs" in cleaned_desc:
                    cleaned_desc = "6-pin pogo pin connector no legs"
                elif "With Legs" in cleaned_desc:
                    cleaned_desc = "6-pin pogo pin connector with legs"
                else:
                    cleaned_desc = "pogo pin programming connector"

            # Intelligent truncation for overly detailed descriptions
            if len(cleaned_desc) > 80:  # Too verbose for search APIs
                # Extract key terms for switches
                if item.category.upper() == "SWI":
                    key_terms = []
                    if "6mm" in cleaned_desc:
                        key_terms.append("6mm")
                    if "Tactile" in cleaned_desc:
                        key_terms.append("Tactile")
                    if "Momentary" in cleaned_desc or "Push" in cleaned_desc:
                        key_terms.append("Momentary")
                    if "DIP" in cleaned_desc:
                        key_terms.append("DIP")
                    if "SPST" in cleaned_desc:
                        key_terms.append("SPST")
                    key_terms.append("Switch")
                    cleaned_desc = " ".join(key_terms)
                else:
                    # Generic truncation - keep first meaningful part
                    cleaned_desc = cleaned_desc[:60].rsplit(" ", 1)[0]

            if len(cleaned_desc) > 10:  # Still detailed enough
                fallback_query = sanitize_search_query(cleaned_desc)
                return primary_query, fallback_query

    # Standard component characteristic approach
    if item.value:
        value = normalize_value(item.value)
        # For switches, don't use cryptic part numbers as values
        if item.category and item.category.upper() == "SWI":
            if hasattr(item, "type") and item.type:
                parts.append(item.type)  # Use Type field instead of Value for switches
        else:
            parts.append(value)

    # Add component type with enhanced mapping
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
            "CON": "connector",
            "MCU": "microcontroller",
            "RLY": "relay",
            "SWI": "switch",
        }
        if item.category.upper() in type_keywords:
            component_type = type_keywords[item.category.upper()]

            # For switches, be more specific
            if item.category.upper() == "SWI":
                if hasattr(item, "type") and "DIP" in str(item.type).upper():
                    if "4" in str(item.type) or "x4" in str(item.type):
                        parts.append("4 Position DIP Switch")
                    else:
                        parts.append("DIP Switch")
                elif hasattr(item, "type") and "Momentary" in str(item.type):
                    parts.append("Tactile Switch")
                else:
                    parts.append(component_type)
            else:
                parts.append(component_type)

    # Add package info (but not for switches using DIP description)
    if item.package and not (
        item.category
        and item.category.upper() == "SWI"
        and "DIP Switch" in " ".join(parts)
    ):
        parts.append(item.package)

    if item.tolerance and item.tolerance not in ["", "N/A"]:
        parts.append(item.tolerance)

    fallback_query = sanitize_search_query(" ".join(parts))

    return primary_query, fallback_query


def extract_bulk_pricing(search_result) -> dict:
    """Extract bulk pricing information from search result."""
    pricing_info = {
        "unit_price": "N/A",
        "bulk_price": "N/A",
        "bulk_qty": "N/A",
        "pricing_tiers": [],
    }

    # Try to get pricing from raw_data if available
    if hasattr(search_result, "raw_data") and search_result.raw_data:
        price_breaks = search_result.raw_data.get("PriceBreaks", [])

        if price_breaks:
            # Helper to safely convert quantity to int
            def get_qty_int(break_entry):
                qty = break_entry.get("Quantity", "1")
                if isinstance(qty, int):
                    return qty
                elif isinstance(qty, str):
                    return int(qty.replace(",", ""))
                else:
                    return 1

            # Sort by quantity to find unit and bulk prices
            sorted_breaks = sorted(price_breaks, key=get_qty_int)

            # Unit price (lowest quantity)
            if sorted_breaks:
                pricing_info["unit_price"] = sorted_breaks[0].get("Price", "N/A")

            # Find bulk pricing (qty >= 1000 or highest tier)
            bulk_breaks = [b for b in sorted_breaks if get_qty_int(b) >= 1000]
            if bulk_breaks:
                bulk_break = bulk_breaks[0]  # First tier >= 1000
                pricing_info["bulk_price"] = bulk_break.get("Price", "N/A")
                pricing_info["bulk_qty"] = bulk_break.get("Quantity", "N/A")
            elif len(sorted_breaks) > 1:
                # Use highest tier if no 1000+ tier
                bulk_break = sorted_breaks[-1]
                pricing_info["bulk_price"] = bulk_break.get("Price", "N/A")
                pricing_info["bulk_qty"] = bulk_break.get("Quantity", "N/A")

            # Store all pricing tiers
            pricing_info["pricing_tiers"] = [
                f"{b.get('Quantity', '?')}: {b.get('Price', '?')}"
                for b in sorted_breaks
            ]

    # Fallback to simple price if detailed pricing not available
    if pricing_info["unit_price"] == "N/A":
        pricing_info["unit_price"] = getattr(search_result, "price", "N/A")

    return pricing_info


def validate_mpn_match(item, search_results) -> dict:
    """Check if the inventory MPN appears in search results."""
    if not item.mfgpn:
        return {"has_mpn": False, "found_in_results": False, "position": None}

    target_mpn = item.mfgpn.strip().upper()

    for i, result in enumerate(search_results):
        if result.mpn and result.mpn.strip().upper() == target_mpn:
            return {
                "has_mpn": True,
                "found_in_results": True,
                "position": i + 1,
                "result": result,
            }

    return {"has_mpn": True, "found_in_results": False, "position": None}


def cached_search(
    cache: SearchCache,
    provider: MouserProvider,
    query: str,
    limit: int,
    cache_strategy: str = "auto",
) -> list:
    """Perform search with intelligent caching.

    Args:
        cache: SearchCache instance
        provider: Search provider
        query: Search query
        limit: Result limit
        cache_strategy: "always", "generic_only", "mpn_only", "never", "auto"
    """
    # Determine if we should use cache based on strategy
    should_cache = False

    if cache_strategy == "always":
        should_cache = True
    elif cache_strategy == "generic_only":
        # Cache generic searches (contain component type words)
        generic_terms = [
            "resistor",
            "capacitor",
            "inductor",
            "led",
            "diode",
            "ic",
            "transistor",
            "regulator",
            "connector",
            "microcontroller",
            "relay",
            "switch",
        ]
        should_cache = any(term in query.lower() for term in generic_terms)
    elif cache_strategy == "mpn_only":
        # Only cache specific MPN searches (no generic component terms)
        generic_terms = [
            "resistor",
            "capacitor",
            "inductor",
            "led",
            "diode",
            "ic",
            "transistor",
            "regulator",
            "connector",
            "microcontroller",
            "relay",
            "switch",
        ]
        should_cache = not any(term in query.lower() for term in generic_terms)
    elif cache_strategy == "auto":
        # Smart caching: cache generic searches but not specific MPNs
        generic_terms = [
            "resistor",
            "capacitor",
            "inductor",
            "led",
            "diode",
            "ic",
            "transistor",
            "regulator",
            "connector",
            "microcontroller",
            "relay",
            "switch",
        ]
        should_cache = any(term in query.lower() for term in generic_terms)
    elif cache_strategy == "never":
        should_cache = False

    # Try cache first if caching is enabled
    if should_cache:
        cached_results = cache.get(query, limit)
        if cached_results:
            return cached_results

    # Perform actual search
    try:
        results = provider.search(query, limit=limit)

        # Cache the results if caching is enabled
        if should_cache and results:
            cache.put(query, limit, results)

        return results

    except Exception as e:
        print(f"    🚨 Search API Error: {e}")
        return []


def generate_enhanced_validation_report(
    inventory_file: str, limit: int = 5, cache_strategy: str = "auto"
):
    """Generate enhanced validation report with MPN and bulk pricing analysis."""

    print("=" * 100)
    print("ENHANCED INVENTORY SEARCH VALIDATION REPORT WITH CACHING")
    print("=" * 100)
    print(f"Inventory File: {inventory_file}")
    print(f"Search Limit: {limit} results per item")
    print(f"Cache Strategy: {cache_strategy}")
    print(f"Focus: MPN Priority + Bulk Pricing Analysis")
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

    # Filter searchable items and categorize by MPN availability
    searchable_items = []
    items_with_mpn = []
    items_without_mpn = []

    for item in inventory_items:
        # Basic filtering
        if not item.value or not item.category:
            continue
        if len(str(item.value).strip()) < 2:
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

        # Category-based filtering (expanded list)
        if item.category and item.category.upper() in ["SLK", "BOARD", "DOC", "MECH"]:
            continue

        # Searchable electronic component categories
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
        if not (item.category and item.category.upper() in searchable_categories):
            continue

        searchable_items.append(item)

        if item.mfgpn and item.mfgpn.strip():
            items_with_mpn.append(item)
        else:
            items_without_mpn.append(item)

    print(f"Searchable electronic components: {len(searchable_items)}")
    print(f"  - With MPN data: {len(items_with_mpn)}")
    print(f"  - Without MPN data: {len(items_without_mpn)}")
    print("")

    # Initialize search provider and cache
    try:
        search_provider = MouserProvider()
        search_cache = SearchCache()
        print(f"Search Provider: {search_provider.name}")
        print(f"Cache Strategy: {cache_strategy}")
    except ValueError as e:
        print(f"ERROR: Could not initialize search provider: {e}")
        return

    # Initialize scorer
    scorer = SearchResultScorer()

    # Track cache statistics
    cache_hits = 0
    cache_misses = 0

    print("=" * 100)
    print("ENHANCED SEARCH ANALYSIS")
    print("=" * 100)

    success_count = 0
    mpn_found_count = 0
    mpn_total_count = 0

    # Focus on items with MPN data first (most critical validation)
    test_items = (
        items_with_mpn[:5]
        if len(items_with_mpn) >= 5
        else items_with_mpn + items_without_mpn[: 5 - len(items_with_mpn)]
    )

    for i, item in enumerate(test_items, 1):
        print(f"\n[{i}] IPN: {item.ipn}")
        print(f"    Category: {item.category}")
        print(f"    Original Value: '{item.value}'")
        print(f"    Package: {item.package or 'N/A'}")
        print(f"    Tolerance: {item.tolerance or 'N/A'}")
        print(f"    📋 Inventory MPN: {item.manufacturer or '?'} {item.mfgpn or 'N/A'}")

        # Analyze for distributor compatibility issues
        issues = analyze_inventory_item_issues(item)
        if issues["recommendations"]:
            print(f"    ⚠️  Issues Detected:")
            for rec in issues["recommendations"]:
                print(f"        - {rec}")

        # Build search queries
        primary_query, fallback_query = build_enhanced_search_query(item)

        search_results = []
        query_used = None

        # Try primary query (MPN-based) first
        if primary_query:
            print(f"    🔍 Primary Query (MPN): '{primary_query}'")
            # Count cache hits/misses
            cached_results = search_cache.get(primary_query, limit)
            if cached_results:
                cache_hits += 1
                print(f"    💾 Cache HIT")
            else:
                cache_misses += 1

            search_results = cached_search(
                search_cache, search_provider, primary_query, limit, cache_strategy
            )
            query_used = primary_query
            if not search_results:
                print(f"    ⚠️ No results from MPN search, trying fallback...")
                time.sleep(1.0)

        # Try fallback query if needed
        if not search_results and fallback_query:
            print(f"    🔍 Fallback Query: '{fallback_query}'")
            # Count cache hits/misses
            cached_results = search_cache.get(fallback_query, limit)
            if cached_results:
                cache_hits += 1
                print(f"    💾 Cache HIT")
            else:
                cache_misses += 1

            search_results = cached_search(
                search_cache, search_provider, fallback_query, limit, cache_strategy
            )
            query_used = fallback_query

        # Analyze results
        if search_results:
            success_count += 1
            print(f"    ✅ Found {len(search_results)} results using: {query_used}")

            # Validate MPN match if applicable
            mpn_analysis = validate_mpn_match(item, search_results)
            if mpn_analysis["has_mpn"]:
                mpn_total_count += 1
                if mpn_analysis["found_in_results"]:
                    mpn_found_count += 1
                    print(
                        f"    🎯 ✅ Inventory MPN found at position #{mpn_analysis['position']}"
                    )
                else:
                    print(f"    🎯 ❌ Inventory MPN NOT found in search results")
                    print(f"        Expected: {item.mfgpn}")
                    print(f"        Found MPNs: {[r.mpn for r in search_results[:3]]}")

            # Show enhanced results with bulk pricing
            mock_component = type(
                "MockComponent",
                (),
                {
                    "value": item.value or "",
                    "footprint": item.package or "",
                    "lib_id": f"{item.category or 'UNKNOWN'}:{item.ipn or 'UNKNOWN'}",
                    "properties": {
                        "Tolerance": item.tolerance or "",
                        "Voltage": item.voltage or "",
                        "Power": item.wattage or "",
                        "Type": item.type or "",
                    },
                },
            )()

            for j, result in enumerate(search_results, 1):
                priority = scorer.calculate_priority(mock_component, result)
                pricing = extract_bulk_pricing(result)

                # Highlight if this matches inventory MPN
                highlight = (
                    "🎯"
                    if (
                        item.mfgpn
                        and result.mpn
                        and result.mpn.strip().upper() == item.mfgpn.strip().upper()
                    )
                    else "  "
                )

                print(f"    {highlight}[{j}] {result.manufacturer} {result.mpn}")
                print(f"        Distributor PN: {result.distributor_part_number}")
                print(
                    f"        Unit Price: {pricing['unit_price']} | Bulk Price: {pricing['bulk_price']} @ {pricing['bulk_qty']}"
                )
                print(f"        Availability: {result.availability}")
                print(f"        Priority Score: {priority}")

                if pricing["pricing_tiers"]:
                    print(
                        f"        Price Tiers: {' | '.join(pricing['pricing_tiers'])}"
                    )
        else:
            print(f"    ❌ No results found")

        # Rate limiting
        time.sleep(1.0)

    # Enhanced Summary
    print("\n" + "=" * 100)
    print("ENHANCED VALIDATION SUMMARY")
    print("=" * 100)
    print(f"Total items tested: {len(test_items)}")
    print(f"Successful searches: {success_count}")
    print(f"Success rate: {100 * success_count / len(test_items):.1f}%")
    print("")
    print(f"CACHE PERFORMANCE:")
    total_searches = cache_hits + cache_misses
    if total_searches > 0:
        print(f"  Total searches: {total_searches}")
        print(f"  Cache hits: {cache_hits}")
        print(f"  Cache misses: {cache_misses}")
        print(f"  Cache hit rate: {100 * cache_hits / total_searches:.1f}%")
        print(f"  API calls saved: {cache_hits}")
    else:
        print(f"  No cache statistics available")
    print("")

    print(f"MPN VALIDATION:")
    print(f"  Items with MPN data: {mpn_total_count}")
    print(f"  MPNs found in search results: {mpn_found_count}")
    if mpn_total_count > 0:
        print(f"  MPN match rate: {100 * mpn_found_count / mpn_total_count:.1f}%")
    print("")

    print(f"METHODOLOGY IMPROVEMENTS IDENTIFIED:")
    print(f"✅ Enhanced search strategy:")
    print(f"   - Primary: Search by existing MPN when available")
    print(f"   - Fallback: Search by component characteristics")
    print(f"✅ Bulk pricing analysis:")
    print(f"   - Unit pricing: qty=1 for comparison")
    print(f"   - Bulk pricing: qty=1000+ for fab-realistic costs")
    print(f"✅ MPN validation:")
    print(f"   - Verify existing inventory parts appear in results")
    print(f"   - Flag when specified parts are missing from search")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate enhanced search validation with MPN priority"
    )
    parser.add_argument("inventory_file", help="Path to inventory file")
    parser.add_argument(
        "--limit", type=int, default=5, help="Search results per item (default: 5)"
    )

    args = parser.parse_args()

    generate_enhanced_validation_report(args.inventory_file, args.limit)


if __name__ == "__main__":
    main()
