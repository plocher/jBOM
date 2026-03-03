"""LCSC search provider backed by the JLCPCB live API.

This is the Phase 2 deliverable for Issue #115.

Notes:
- No API key required.
- Uses DiskSearchCache via the injected SearchCache.
- Sorting is performed client-side by SearchSorter, but the provider requests
  stock-desc ordering from the API (sortMode=STOCK_SORT, sortASC=DESC).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from jbom.services.search.cache import SearchCache, SearchCacheKey
from jbom.services.search import jlcpcb_api
from jbom.services.search.jlcpcb_api import JlcpcbPartsApi
from jbom.services.search.models import SearchResult
from jbom.services.search.provider import SearchProvider

if TYPE_CHECKING:
    from jbom.config.providers import SearchProviderConfig


@dataclass(frozen=True)
class _Config:
    rate_limit_seconds: float


class JlcpcbProvider(SearchProvider):
    """LCSC search via JLCPCB's public parts API."""

    def __init__(
        self, *, cache: SearchCache, rate_limit_seconds: float | None = None
    ) -> None:
        self._cfg = _Config(
            rate_limit_seconds=2.0
            if rate_limit_seconds is None
            else max(0.0, float(rate_limit_seconds))
        )
        self._cache = cache

        # Preserve SearchProvider contract: missing requests => available() == False.
        self._api: JlcpcbPartsApi | None = None
        if jlcpcb_api.requests is not None:  # pragma: no cover
            self._api = JlcpcbPartsApi(
                cfg=JlcpcbPartsApi.default_config(
                    provider_id=self.provider_id,
                    rate_limit_seconds=self._cfg.rate_limit_seconds,
                )
            )

    @classmethod
    def from_config(
        cls, cfg: "SearchProviderConfig", *, cache: SearchCache
    ) -> "JlcpcbProvider":
        rate_limit = cfg.extra.get("rate_limit_seconds")
        rate_limit_norm = None
        if rate_limit is not None and str(rate_limit).strip() != "":
            try:
                rate_limit_norm = float(rate_limit)
            except (TypeError, ValueError):
                rate_limit_norm = None

        return cls(cache=cache, rate_limit_seconds=rate_limit_norm)

    def available(self) -> bool:
        return self._api is not None

    def unavailable_reason(self) -> str:
        return (
            "LCSC search provider (jlcpcb_api) requires the 'requests' package. "
            "Install it with: pip install requests"
        )

    @property
    def provider_id(self) -> str:
        return "lcsc"

    @property
    def name(self) -> str:
        return "LCSC (JLCPCB live API)"

    def search(self, query: str, *, limit: int = 10) -> list[SearchResult]:
        cache_key = SearchCacheKey.create(
            provider_id=self.provider_id, query=query, limit=limit
        )
        cached = self._cache.get(cache_key)
        if cached is not None:
            return list(cached)

        # Page size is capped by the CLI to <=100, but keep bounds safe.
        page_size = max(1, min(1024, int(limit)))

        if self._api is None:
            raise RuntimeError(self.unavailable_reason())

        data = self._api.search_keyword(
            query=query,
            page=1,
            page_size=page_size,
            sort_mode="STOCK_SORT",
            sort_asc="DESC",
        )

        results = self._parse_results(data)

        # Store raw provider results (the CLI applies filters/ranking).
        self._cache.set(cache_key, results)
        return list(results)

    def _parse_results(self, data: dict[str, Any]) -> list[SearchResult]:
        payload = data.get("data")
        if not isinstance(payload, dict):
            return []

        page_info = payload.get("componentPageInfo")
        if not isinstance(page_info, dict):
            return []

        rows = page_info.get("list")
        if not isinstance(rows, list):
            return []

        out: list[SearchResult] = []
        for row in rows:
            if not isinstance(row, dict):
                continue

            out.append(self._row_to_result(row))

        return out

    def _row_to_result(self, row: dict[str, Any]) -> SearchResult:
        c_number = str(row.get("componentCode") or "").strip()
        mpn = str(row.get("componentModelEn") or "").strip()
        manufacturer = str(row.get("componentBrandEn") or "").strip()
        description = str(row.get("describe") or "").strip()

        details_url = str(row.get("lcscGoodsUrl") or "").strip()
        datasheet = str(row.get("dataManualUrl") or "").strip()

        stock_qty = 0
        try:
            stock_qty = int(row.get("stockCount") or 0)
        except (TypeError, ValueError):
            stock_qty = 0

        availability = f"{stock_qty} In Stock" if stock_qty >= 0 else ""

        price = "N/A"
        price_breaks = row.get("componentPrices")
        if isinstance(price_breaks, list) and price_breaks:
            first = price_breaks[0] if isinstance(price_breaks[0], dict) else {}
            if isinstance(first, dict) and first.get("productPrice") is not None:
                price = str(first.get("productPrice"))

        attributes: dict[str, str] = {}
        raw_attrs = row.get("attributes")
        if isinstance(raw_attrs, list):
            for a in raw_attrs:
                if not isinstance(a, dict):
                    continue
                name = str(a.get("attribute_name_en") or "").strip()
                value = str(a.get("attribute_value_name") or "").strip()
                if name and value and name not in attributes:
                    attributes[name] = value

        min_order_qty = 1
        if row.get("minBuyNumber") is not None:
            try:
                min_order_qty = int(row.get("minBuyNumber") or 1)
            except (TypeError, ValueError):
                min_order_qty = 1

        return SearchResult(
            manufacturer=manufacturer,
            mpn=mpn,
            description=description,
            datasheet=datasheet,
            distributor=self.provider_id,
            distributor_part_number=c_number,
            availability=availability,
            price=price,
            details_url=details_url,
            raw_data=row,
            min_order_qty=min_order_qty,
            attributes=attributes,
            stock_quantity=stock_qty,
        )


__all__ = ["JlcpcbProvider"]
