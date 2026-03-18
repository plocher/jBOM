"""Mouser Search API provider."""

from __future__ import annotations

import logging
import os
import re
import time
from typing import TYPE_CHECKING, Any, Optional

from jbom.config.suppliers import resolve_supplier_by_id
from jbom.services.search.cache import SearchCache, SearchCacheKey
from jbom.services.search.models import SearchResult
from jbom.services.search.normalization import extract_package_token
from jbom.services.search.provider import SearchProvider

if TYPE_CHECKING:
    from jbom.config.providers import SearchProviderConfig

logger = logging.getLogger(__name__)

_RESISTANCE_TOKEN_PATTERN = re.compile(
    r"\b(?:\d+(?:\.\d+)?(?:R|K|M)\d*|\d+(?:\.\d+)?\s*(?:OHM|OHMS|KOHM|KOHMS|MOHM|MOHMS|Ω))\b",
    re.IGNORECASE,
)
_CAPACITANCE_TOKEN_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:PF|NF|UF|µF|μF|MF)\b", re.IGNORECASE
)
_INDUCTANCE_TOKEN_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:NH|UH|µH|μH|MH|H)\b", re.IGNORECASE
)
_TOLERANCE_TOKEN_PATTERN = re.compile(r"(?:\+/-\s*)?(\d+(?:\.\d+)?)\s*%", re.IGNORECASE)

_ATTRIBUTE_NORMALIZATION_MAP: dict[str, str] = {
    "resistance": "Resistance",
    "resistance value": "Resistance",
    "resistor value": "Resistance",
    "capacitance": "Capacitance",
    "capacitance value": "Capacitance",
    "inductance": "Inductance",
    "tolerance": "Tolerance",
    "voltage rating": "Voltage Rating",
    "rated voltage": "Voltage Rating",
    "package": "Package",
    "package / case": "Package",
    "package case": "Package",
    "case code - in": "Package",
    "case code - mm": "Package",
}

try:
    import requests  # type: ignore
except ImportError:  # pragma: no cover
    requests = None  # type: ignore


class MouserProvider(SearchProvider):
    """Mouser keyword search API integration."""

    BASE_URL = "https://api.mouser.com/api/v1/search"

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        api_key_env: str = "MOUSER_API_KEY",
        cache: Optional[SearchCache] = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        retry_delay: float | None = None,
    ) -> None:
        """Create a provider.

        Args:
            api_key: Mouser API key.
            api_key_env: Environment variable name suggested to users when api_key is missing.
            cache: Optional cache used to reduce repeated API calls.
            timeout: Request timeout in seconds (defaults to supplier profile).
            max_retries: Max retry attempts for transient failures (defaults to supplier profile).
            retry_delay: Initial delay (seconds) before retry; uses exponential backoff (defaults to supplier profile).
        """

        self._api_key_env = (
            api_key_env or "MOUSER_API_KEY"
        ).strip() or "MOUSER_API_KEY"
        self._api_key = (
            (api_key or "").strip() or os.environ.get(self._api_key_env) or None
        )

        self._cache = cache

        supplier = resolve_supplier_by_id(self.provider_id)

        if timeout is None:
            timeout = supplier.search_timeout_seconds if supplier is not None else None
        if max_retries is None:
            max_retries = supplier.search_max_retries if supplier is not None else None
        if retry_delay is None:
            retry_delay = (
                supplier.search_retry_delay_seconds if supplier is not None else None
            )

        # Keep behavior robust if the supplier profile is incomplete.
        if timeout is None:
            logger.warning(
                "Supplier profile '%s' missing search.api.timeout_seconds; defaulting to 10s",
                self.provider_id,
            )
            timeout = 10.0
        if max_retries is None:
            logger.warning(
                "Supplier profile '%s' missing search.api.max_retries; defaulting to 3",
                self.provider_id,
            )
            max_retries = 3
        if retry_delay is None:
            logger.warning(
                "Supplier profile '%s' missing search.api.retry_delay_seconds; defaulting to 1s",
                self.provider_id,
            )
            retry_delay = 1.0

        self._timeout = max(0.0, float(timeout))
        self._max_retries = max(0, int(max_retries))
        self._retry_delay = max(0.0, float(retry_delay))

    @classmethod
    def from_config(
        cls, cfg: SearchProviderConfig, *, cache: SearchCache
    ) -> "MouserProvider":
        api_key = cfg.extra.get("api_key")
        api_key_norm = str(api_key).strip() if api_key is not None else ""

        api_key_env = cfg.extra.get("api_key_env")
        api_key_env_norm = (
            str(api_key_env).strip() if api_key_env is not None else "MOUSER_API_KEY"
        )
        api_key_env_norm = api_key_env_norm or "MOUSER_API_KEY"

        resolved_key = api_key_norm or os.environ.get(api_key_env_norm)

        return cls(
            api_key=resolved_key,
            api_key_env=api_key_env_norm,
            cache=cache,
        )

    def available(self) -> bool:
        if requests is None:  # pragma: no cover
            return False
        return bool(self._api_key)

    def unavailable_reason(self) -> str:
        if requests is None:  # pragma: no cover
            return "Search support requires the 'requests' package. Install it with: pip install requests"
        if not self._api_key:
            return f"Mouser API Key is required. Set {self._api_key_env} or pass --api-key."
        return ""

    @property
    def provider_id(self) -> str:
        return "mouser"

    @property
    def name(self) -> str:
        return "Mouser"

    def search(self, query: str, *, limit: int = 10) -> list[SearchResult]:
        if requests is None:  # pragma: no cover
            raise RuntimeError(self.unavailable_reason())
        if not self._api_key:
            raise RuntimeError(self.unavailable_reason())

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

        data: dict[str, Any] | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = requests.post(
                    url,
                    params={"apiKey": self._api_key},
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    timeout=self._timeout,
                )
            except Exception as exc:
                if attempt >= self._max_retries:
                    logger.error("Mouser API request failed: %s", exc)
                    return []

                delay = self._retry_delay * (2**attempt)
                logger.debug(
                    "Mouser API request failed; retrying %s/%s in %.2fs: %s",
                    attempt + 1,
                    self._max_retries,
                    delay,
                    exc,
                )
                time.sleep(delay)
                continue

            status_raw = getattr(response, "status_code", 200)
            try:
                status = int(status_raw)  # type: ignore[arg-type]
            except Exception:
                status = 200

            if 400 <= status < 500:
                logger.error(
                    "Mouser API request failed (client error %s): %s",
                    status,
                    response.text,
                )
                return []

            if status >= 500:
                if attempt >= self._max_retries:
                    logger.error(
                        "Mouser API request failed (server error %s): %s",
                        status,
                        response.text,
                    )
                    return []

                delay = self._retry_delay * (2**attempt)
                logger.debug(
                    "Mouser API request failed (server error %s); retrying %s/%s in %.2fs",
                    status,
                    attempt + 1,
                    self._max_retries,
                    delay,
                )
                time.sleep(delay)
                continue

            try:
                response.raise_for_status()
                data = response.json()
                break
            except Exception as exc:
                # Non-retryable at this point.
                logger.error("Mouser API request failed: %s", exc)
                return []

        if data is None:
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

    @staticmethod
    def _normalize_attribute_name(name: str) -> str:
        key = " ".join((name or "").strip().lower().split())
        return _ATTRIBUTE_NORMALIZATION_MAP.get(key, (name or "").strip())

    @staticmethod
    def _extract_package_token(*texts: str) -> str:
        return extract_package_token(*texts)

    @staticmethod
    def _extract_first(pattern: re.Pattern[str], text: str) -> str:
        if not text:
            return ""
        match = pattern.search(text)
        if not match:
            return ""
        return match.group(0).strip()

    @staticmethod
    def _infer_passive_intent(category: str, description: str) -> str:
        haystack = f"{category} {description}".upper()
        if "RESISTOR" in haystack:
            return "RES"
        if "CAPACITOR" in haystack:
            return "CAP"
        if "INDUCTOR" in haystack:
            return "IND"
        return ""

    def _enrich_attributes_from_description(
        self,
        *,
        attributes: dict[str, str],
        description: str,
        category: str,
        mpn: str,
    ) -> dict[str, str]:
        out = dict(attributes)

        if not out.get("Package"):
            package = self._extract_package_token(description, mpn)
            if package:
                out["Package"] = package

        if not out.get("Tolerance"):
            tolerance_num = self._extract_first(_TOLERANCE_TOKEN_PATTERN, description)
            if tolerance_num:
                norm = tolerance_num.replace("+/-", "").replace(" ", "")
                if norm.endswith("%"):
                    out["Tolerance"] = norm

        intent = self._infer_passive_intent(category, description)
        if intent == "RES" and not out.get("Resistance"):
            resistance = self._extract_first(_RESISTANCE_TOKEN_PATTERN, description)
            if resistance:
                out["Resistance"] = resistance
        if intent == "CAP" and not out.get("Capacitance"):
            capacitance = self._extract_first(_CAPACITANCE_TOKEN_PATTERN, description)
            if capacitance:
                out["Capacitance"] = capacitance
        if intent == "IND" and not out.get("Inductance"):
            inductance = self._extract_first(_INDUCTANCE_TOKEN_PATTERN, description)
            if inductance:
                out["Inductance"] = inductance

        return out

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
                    canonical_name = self._normalize_attribute_name(name)
                    if canonical_name and canonical_name not in attributes:
                        attributes[canonical_name] = value

            description = str(part.get("Description", ""))
            category = str(part.get("Category", ""))
            mpn = str(part.get("ManufacturerPartNumber", ""))
            attributes = self._enrich_attributes_from_description(
                attributes=attributes,
                description=description,
                category=category,
                mpn=mpn,
            )

            lifecycle = str(part.get("LifecycleStatus", "Unknown"))
            min_order_raw = str(part.get("Min", "1"))
            try:
                min_order = int(min_order_raw)
            except ValueError:
                min_order = 1

            results.append(
                SearchResult(
                    manufacturer=str(part.get("Manufacturer", "")),
                    mpn=mpn,
                    description=description,
                    datasheet=str(part.get("DataSheetUrl", "")),
                    distributor=self.provider_id,
                    distributor_part_number=str(part.get("MouserPartNumber", "")),
                    availability=availability,
                    price=price,
                    details_url=str(part.get("ProductDetailUrl", "")),
                    raw_data=part,
                    lifecycle_status=lifecycle,
                    min_order_qty=min_order,
                    category=category,
                    attributes=attributes,
                    stock_quantity=stock_qty,
                )
            )

        return results


__all__ = ["MouserProvider"]
