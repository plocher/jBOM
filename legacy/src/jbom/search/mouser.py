"""
Mouser Search API Provider.
"""
import os
import requests
import logging
from typing import List, Dict, Any, Optional
from jbom.search import SearchProvider, SearchResult
from jbom.search.filter import SearchSorter

logger = logging.getLogger(__name__)


class MouserProvider(SearchProvider):
    """Mouser Search API integration."""

    BASE_URL = "https://api.mouser.com/api/v1/search"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key (defaults to MOUSER_API_KEY env var)."""
        self.api_key = api_key or os.environ.get("MOUSER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Mouser API Key is required. Set MOUSER_API_KEY or pass to constructor."
            )

    @property
    def name(self) -> str:
        return "Mouser"

    def search(self, query: str, limit: int = 50) -> List[SearchResult]:
        """Search Mouser API for parts.

        Note: We request more results than limit to allow for client-side filtering.
        """
        url = f"{self.BASE_URL}/keyword"

        # Mouser API Request Body
        payload = {
            "SearchByKeywordRequest": {
                "keyword": query,
                "records": limit * 2,  # Fetch more to allow for filtering
                "startingRecord": 0,
                "searchOptions": "None",
                "searchWithYourSignUpLanguage": "English",
            }
        }

        params = {"apiKey": self.api_key}

        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        try:
            response = requests.post(
                url, params=params, json=payload, headers=headers, timeout=10
            )
            response.raise_for_status()
            data = response.json()

            # Check for API errors in response body (Mouser style)
            if "Errors" in data and data["Errors"]:
                error_msgs = [e.get("Message", "Unknown Error") for e in data["Errors"]]
                logger.error(f"Mouser API Error: {', '.join(error_msgs)}")
                return []

            results = self._parse_results(data)

            # Apply default filters (In Stock, Active)
            filtered = self._apply_default_filters(results)

            return filtered[:limit]

        except requests.RequestException as e:
            logger.error(f"Mouser API Request failed: {e}")
            return []

    def _apply_default_filters(self, results: List[SearchResult]) -> List[SearchResult]:
        """Apply default availability and lifecycle filters."""
        filtered = []
        for r in results:
            # 1. Must be in stock
            if r.stock_quantity <= 0:
                continue

            # 2. Must be Active or New Design (avoid Obsolete/NRND)
            status = str(r.lifecycle_status).lower()
            if "obsolete" in status or "not recommended" in status:
                continue

            # 3. Must be Normally Stocked (avoid Factory Order if possible)
            # Mouser availability string usually contains "In Stock" or "Factory Order"
            if "factory order" in str(r.availability).lower():
                continue

            filtered.append(r)

        # Sort using centralized sorter
        return SearchSorter.rank(filtered)

    def _parse_results(self, data: Dict[str, Any]) -> List[SearchResult]:
        """Parse raw API response into SearchResults."""
        results = []

        # Mouser response structure is usually inside SearchResults -> Parts
        search_results = data.get("SearchResults", {})
        parts = search_results.get("Parts", [])

        for part in parts:
            try:
                # Extract Availability
                availability = part.get("Availability", "Unknown")
                stock_qty = 0
                # Try to parse numeric stock from "6609 In Stock" or raw fields
                # Mouser often provides "SearchResultsCount" or similar, but per-part availability
                # is in the Availability string or sometimes explicit fields depending on API version.
                # Here we try to parse the leading number from the string.
                if availability:
                    try:
                        stock_parts = availability.split()
                        if stock_parts and stock_parts[0].replace(",", "").isdigit():
                            stock_qty = int(stock_parts[0].replace(",", ""))
                    except (ValueError, IndexError):
                        pass

                # Extract Price (simple - taking first available)
                price = "N/A"
                price_breaks = part.get("PriceBreaks", [])
                if price_breaks:
                    price = price_breaks[0].get("Price", "N/A")

                # Extract Attributes
                attributes = {}
                for attr in part.get("ProductAttributes", []):
                    name = attr.get("AttributeName", "")
                    value = attr.get("AttributeValue", "")
                    if name and value:
                        attributes[name] = value

                # Extract Lifecycle and Min Order
                lifecycle = part.get("LifecycleStatus", "Unknown")
                min_order = part.get("Min", "1")
                try:
                    min_order_int = int(min_order)
                except ValueError:
                    min_order_int = 1

                item = SearchResult(
                    manufacturer=part.get("Manufacturer", ""),
                    mpn=part.get("ManufacturerPartNumber", ""),
                    description=part.get("Description", ""),
                    datasheet=part.get("DataSheetUrl", ""),
                    distributor="Mouser",
                    distributor_part_number=part.get("MouserPartNumber", ""),
                    availability=availability,
                    price=price,
                    details_url=part.get("ProductDetailUrl", ""),
                    raw_data=part,
                    # Enhanced fields
                    lifecycle_status=lifecycle,
                    min_order_qty=min_order_int,
                    category=part.get("Category", ""),
                    attributes=attributes,
                    stock_quantity=stock_qty,
                )
                results.append(item)
            except Exception as e:
                logger.warning(f"Failed to parse Mouser result item: {e}")
                continue

        return results
