"""JLCPCB/LCSC live search API client.

This module implements the minimal HTTP client needed for Issue #115 Phase 2.

Validated by the Phase 1 POC script (scripts/lcsc_api_poc.py):
- No auth required
- Keyword search via selectSmtComponentList/v2
- Stock sorting is controlled by sortMode/sortASC (not stockSort)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from jbom.config.suppliers import resolve_supplier_by_id

logger = logging.getLogger(__name__)

try:
    import requests  # type: ignore
except ImportError:  # pragma: no cover
    requests = None  # type: ignore


@dataclass(frozen=True)
class JlcpcbApiConfig:
    """Runtime configuration for JLCPCB API access."""

    timeout_seconds: float
    max_retries: int
    retry_delay_seconds: float
    rate_limit_seconds: float


class JlcpcbPartsApi:
    """Live search client for JLCPCB's parts API."""

    SEARCH_URL = (
        "https://jlcpcb.com/api/overseas-pcb-order/v1/"
        "shoppingCart/smtGood/selectSmtComponentList/v2"
    )

    def __init__(
        self,
        *,
        cfg: JlcpcbApiConfig,
    ) -> None:
        if requests is None:  # pragma: no cover
            raise RuntimeError(
                "JLCPCB search requires the 'requests' package. Install it with: pip install requests"
            )

        self._cfg = cfg

    @staticmethod
    def default_config(
        *, provider_id: str, rate_limit_seconds: float | None
    ) -> JlcpcbApiConfig:
        """Build config from supplier profile with safe defaults."""

        supplier = resolve_supplier_by_id(provider_id)

        timeout = supplier.search_timeout_seconds if supplier is not None else None
        max_retries = supplier.search_max_retries if supplier is not None else None
        retry_delay = (
            supplier.search_retry_delay_seconds if supplier is not None else None
        )

        if timeout is None:
            timeout = 15.0
        if max_retries is None:
            max_retries = 3
        if retry_delay is None:
            retry_delay = 1.0

        if rate_limit_seconds is None:
            rate_limit_seconds = 2.0

        return JlcpcbApiConfig(
            timeout_seconds=max(0.0, float(timeout)),
            max_retries=max(0, int(max_retries)),
            retry_delay_seconds=max(0.0, float(retry_delay)),
            rate_limit_seconds=max(0.0, float(rate_limit_seconds)),
        )

    def search_keyword(
        self,
        *,
        query: str,
        page: int = 1,
        page_size: int = 50,
        presale_type: str = "stock",
        sort_mode: str = "STOCK_SORT",
        sort_asc: str = "DESC",
        manufacturer: str | None = None,
    ) -> dict[str, Any]:
        """Search by keyword across the catalog.

        Args:
            query: Free-text query.
            page: 1-indexed page.
            page_size: Requested page size (max 1024 observed).
            presale_type: Observed default is "stock".
            sort_mode: Browser-observed sort mode, default "STOCK_SORT".
            sort_asc: "DESC" or "ASC".
            manufacturer: Optional manufacturer/brand filter. When provided, sent
                as `componentBrandList` to reduce irrelevant results at the source.

        Returns:
            Raw decoded JSON response.
        """

        mfg = (manufacturer or "").strip()
        component_brand_list: list[dict[str, Any]] = []
        if mfg:
            component_brand_list = [{"brandName": mfg}]

        payload: dict[str, Any] = {
            "currentPage": int(page),
            "pageSize": int(page_size),
            "keyword": (query or "").strip() or None,
            "componentLibraryType": "",
            "preferredComponentFlag": False,
            "stockFlag": "",
            "presaleType": str(presale_type or "stock"),
            "searchType": 2,
            "stockSort": None,
            "firstSortName": None,
            "secondSortName": None,
            "componentSpecificationList": [],
            "componentAttributeList": [],
            "componentBrandList": component_brand_list,
            "sortMode": str(sort_mode or "").strip(),
            "sortASC": str(sort_asc or "").strip(),
        }

        # Be gentle with the API.
        if self._cfg.rate_limit_seconds > 0:
            time.sleep(self._cfg.rate_limit_seconds)

        return self._post_json(self.SEARCH_URL, payload)

    def search_parametric(
        self,
        *,
        query: str,
        first_sort_name: str,
        second_sort_name: str | None = None,
        component_specification_list: list[str] | None = None,
        component_attribute_list: list[dict[str, list[str]]] | None = None,
        page: int = 1,
        page_size: int = 50,
        presale_type: str = "stock",
        sort_mode: str = "STOCK_SORT",
        sort_asc: str = "DESC",
    ) -> dict[str, Any]:
        """Search using category/spec/attribute filters (Issue #115 Phase 4).

        Args:
            query: Keyword context merged from inventory-derived terms.
            first_sort_name: Top-level JLCPCB category name (e.g. "Resistors").
            second_sort_name: Optional subcategory name.
            component_specification_list: Optional package/spec filters.
            component_attribute_list: Optional attribute filters as
                ``[{attribute_name: [value1, value2]}, ...]``.
            page: 1-indexed page.
            page_size: Requested page size (max 1024 observed).
            presale_type: Observed default is "stock".
            sort_mode: Browser-observed sort mode, default "STOCK_SORT".
            sort_asc: "DESC" or "ASC".

        Returns:
            Raw decoded JSON response.
        """

        specs = [
            str(v).strip()
            for v in (component_specification_list or [])
            if str(v).strip()
        ]

        attrs: list[dict[str, list[str]]] = []
        for group in component_attribute_list or []:
            if not isinstance(group, dict):
                continue
            for name, values in group.items():
                key = str(name).strip()
                if not key:
                    continue
                cleaned_values = [
                    str(v).strip() for v in (values or []) if str(v).strip()
                ]
                if cleaned_values:
                    attrs.append({key: cleaned_values})

        payload: dict[str, Any] = {
            "currentPage": int(page),
            "pageSize": int(page_size),
            "keyword": (query or "").strip() or None,
            "componentLibraryType": "",
            "preferredComponentFlag": False,
            "stockFlag": "",
            "presaleType": str(presale_type or "stock"),
            "searchType": 2,
            "stockSort": None,
            "firstSortName": str(first_sort_name or "").strip(),
            "firstSortNameList": [str(first_sort_name or "").strip()]
            if str(first_sort_name or "").strip()
            else [],
            "secondSortName": str(second_sort_name or "").strip() or None,
            "componentSpecificationList": specs,
            "componentAttributeList": attrs,
            "componentBrandList": [],
            "sortMode": str(sort_mode or "").strip(),
            "sortASC": str(sort_asc or "").strip(),
        }

        if self._cfg.rate_limit_seconds > 0:
            time.sleep(self._cfg.rate_limit_seconds)

        return self._post_json(self.SEARCH_URL, payload)

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://jlcpcb.com",
            "Referer": "https://jlcpcb.com/parts",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        }

        last_exc: Exception | None = None

        for attempt in range(self._cfg.max_retries + 1):
            try:
                with requests.Session() as session:
                    resp = session.post(
                        url,
                        json=payload,
                        headers=headers,
                        timeout=self._cfg.timeout_seconds,
                    )

                resp.raise_for_status()
                data = resp.json()
                if not isinstance(data, dict):
                    raise ValueError(
                        f"Expected JSON object response, got {type(data).__name__}"
                    )

                return data
            except Exception as exc:
                last_exc = exc
                if attempt >= self._cfg.max_retries:
                    raise

                delay = self._cfg.retry_delay_seconds * (2**attempt)
                logger.debug(
                    "JLCPCB API request failed; retrying %s/%s in %.2fs: %s",
                    attempt + 1,
                    self._cfg.max_retries,
                    delay,
                    exc,
                )
                time.sleep(delay)

        # Defensive: should never reach here.
        if last_exc is not None:  # pragma: no cover
            raise last_exc
        raise RuntimeError("JLCPCB API request failed")  # pragma: no cover


__all__ = ["JlcpcbApiConfig", "JlcpcbPartsApi"]
