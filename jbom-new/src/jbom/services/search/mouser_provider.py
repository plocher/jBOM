"""Mouser Search API provider."""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from jbom.services.search.cache import SearchCache, SearchCacheKey
from jbom.services.search.models import SearchResult
from jbom.services.search.provider import SearchProvider

logger = logging.getLogger(__name__)

try:
    import requests  # type: ignore
except ImportError:  # pragma: no cover
    requests = None  # type: ignore


class MouserProvider(SearchProvider):
    """Mouser keyword search API integration."""

    BASE_URL = "https://api.mouser.com/api/v1/search"

    def __init__(
        self, *, api_key: Optional[str] = None, cache: Optional[SearchCache] = None
    ):
        """Create a provider.

        Args:
            api_key: Mouser API key. Defaults to MOUSER_API_KEY environment variable.
            cache: Optional cache used to reduce repeated API calls.

        Raises:
            ValueError: When api_key is not provided and MOUSER_API_KEY is not set.
        """

        self._api_key = api_key or os.environ.get("MOUSER_API_KEY")
        if not self._api_key:
            raise ValueError(
                "Mouser API Key is required. Set MOUSER_API_KEY or pass --api-key."
            )

        self._cache = cache

    @property
    def provider_id(self) -> str:
        return "mouser"

    @property
    def name(self) -> str:
        return "Mouser"

    def search(self, query: str, *, limit: int = 10) -> list[SearchResult]:
        if requests is None:  # pragma: no cover
            raise RuntimeError(
                "Search support requires the 'requests' package. Install it with: pip install requests"
            )

        cache_key = None
        if self._cache is not None:
            cache_key = SearchCacheKey.create(
                provider_id=self.provider_id, query=query, limit=limit
            )
            cached = self._cache.get(cache_key)
            if cached is not None:
                return list(cached)

        # Fetch more than requested to allow client-side filtering.
        records = min(100, max(50, int(limit) * 2))

        url = f"{self.BASE_URL}/keyword"
        payload = {
            "SearchByKeywordRequest": {
                "keyword": query,
                "records": records,
                "startingRecord": 0,
                "searchOptions": "None",
                "searchWithYourSignUpLanguage": "English",
            }
        }

        try:
            response = requests.post(
                url,
                params={"apiKey": self._api_key},
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.error("Mouser API request failed: %s", exc)
            return []

        # Mouser embeds error strings inside the JSON body.
        errors = data.get("Errors")
        if isinstance(errors, list) and errors:
            msgs = [
                str(e.get("Message", "Unknown Error"))
                for e in errors
                if isinstance(e, dict)
            ]
            logger.error("Mouser API error(s): %s", ", ".join(msgs) if msgs else errors)
            return []

        results = self._parse_results(data)
        results = results[: max(0, int(limit))]

        if cache_key is not None and self._cache is not None:
            self._cache.set(cache_key, results)

        return results

    @staticmethod
    def _parse_stock_quantity(availability: str) -> int:
        if not availability:
            return 0

        # Common format: "6,609 In Stock".
        parts = availability.split()
        if not parts:
            return 0

        head = parts[0].replace(",", "")
        if not head.isdigit():
            return 0

        try:
            return int(head)
        except ValueError:
            return 0

    def _parse_results(self, data: dict[str, Any]) -> list[SearchResult]:
        search_results = data.get("SearchResults", {})
        parts = search_results.get("Parts", [])
        if not isinstance(parts, list):
            return []

        results: list[SearchResult] = []

        for part in parts:
            if not isinstance(part, dict):
                continue

            availability = str(part.get("Availability", ""))
            stock_qty = self._parse_stock_quantity(availability)

            price = "N/A"
            price_breaks = part.get("PriceBreaks", [])
            if isinstance(price_breaks, list) and price_breaks:
                first = price_breaks[0] if isinstance(price_breaks[0], dict) else {}
                if isinstance(first, dict):
                    price = str(first.get("Price", "N/A"))

            attributes: dict[str, str] = {}
            for attr in part.get("ProductAttributes", []) or []:
                if not isinstance(attr, dict):
                    continue
                name = str(attr.get("AttributeName", "") or "").strip()
                value = str(attr.get("AttributeValue", "") or "").strip()
                if name and value:
                    attributes[name] = value

            lifecycle = str(part.get("LifecycleStatus", "Unknown"))
            min_order_raw = str(part.get("Min", "1"))
            try:
                min_order = int(min_order_raw)
            except ValueError:
                min_order = 1

            results.append(
                SearchResult(
                    manufacturer=str(part.get("Manufacturer", "")),
                    mpn=str(part.get("ManufacturerPartNumber", "")),
                    description=str(part.get("Description", "")),
                    datasheet=str(part.get("DataSheetUrl", "")),
                    distributor=self.provider_id,
                    distributor_part_number=str(part.get("MouserPartNumber", "")),
                    availability=availability,
                    price=price,
                    details_url=str(part.get("ProductDetailUrl", "")),
                    raw_data=part,
                    lifecycle_status=lifecycle,
                    min_order_qty=min_order,
                    category=str(part.get("Category", "")),
                    attributes=attributes,
                    stock_quantity=stock_qty,
                )
            )

        return results


__all__ = ["MouserProvider"]
