"""
Search filtering logic.
"""
import re
from typing import List
from jbom.search import SearchResult
from jbom.common.values import parse_res_to_ohms


class SearchFilter:
    """Client-side filtering for search results."""

    @staticmethod
    def filter_by_query(results: List[SearchResult], query: str) -> List[SearchResult]:
        """Filter results based on query terms matching parametric attributes."""
        filtered = []

        # 1. Parse query for key parametric values
        # Resistance
        target_ohms = parse_res_to_ohms(query)

        # Tolerance (e.g., "1%", "5%")
        target_tol = None
        tol_match = re.search(r"(\d+(?:\.\d+)?)%", query)
        if tol_match:
            try:
                target_tol = float(tol_match.group(1))
            except ValueError:
                pass

        for r in results:
            if not r.attributes:
                # Keep if no attributes to check against (fail open)
                filtered.append(r)
                continue

            keep = True

            # 2. Check Resistance
            if target_ohms is not None:
                # Look for "Resistance" attribute
                res_attr = r.attributes.get("Resistance", "")
                if res_attr:
                    # Parse attribute value (e.g. "10 kOhms")
                    attr_ohms = parse_res_to_ohms(res_attr)
                    # Allow small floating point variance
                    if attr_ohms is not None and abs(attr_ohms - target_ohms) > (
                        target_ohms * 0.001
                    ):
                        keep = False

            # 3. Check Tolerance
            if keep and target_tol is not None:
                tol_attr = r.attributes.get("Tolerance", "")
                if tol_attr:
                    # Clean up attribute: "1 %", "+/- 1%"
                    clean_tol = tol_attr.replace("%", "").replace("+/-", "").strip()
                    try:
                        attr_tol = float(clean_tol)
                        # Exact match for tolerance (strict filtering)
                        if attr_tol != target_tol:
                            keep = False
                    except ValueError:
                        pass

            if keep:
                filtered.append(r)

        return filtered

    @staticmethod
    def filter_by_stock(
        results: List[SearchResult], min_quantity: int
    ) -> List[SearchResult]:
        """Filter results based on minimum stock quantity."""
        return [r for r in results if r.stock_quantity >= min_quantity]


class SearchSorter:
    """Sorting logic for search results."""

    @staticmethod
    def rank(results: List[SearchResult]) -> List[SearchResult]:
        """Rank results by Availability (desc) then Price (asc)."""
        # Sort key: (-stock, price_value)
        # Note: Price is string "$0.10", we need to parse it for proper sorting
        # For simplicity in this iteration, we trust the primary stock sort and secondary string sort
        # or implement a simple parser.

        def sort_key(r: SearchResult):
            stock = r.stock_quantity
            try:
                # Remove currency symbol and parse
                price_clean = (
                    r.price.replace("$", "").replace("€", "").replace("£", "").strip()
                )
                price = float(price_clean)
            except ValueError:
                price = float("inf")  # Push unknown prices to end
            return (-stock, price)

        return sorted(results, key=sort_key)
