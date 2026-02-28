"""Search caching helpers.

Phase 6 constraint: keep web API usage low (rate limits / bandwidth). For now we
use in-memory caching, but we also support an optional persistent disk cache.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, Protocol

from jbom.config.suppliers import resolve_supplier_by_id
from jbom.services.search.models import SearchResult

logger = logging.getLogger(__name__)


def normalize_query(query: str) -> str:
    """Normalize a query string for caching keys."""

    return " ".join((query or "").strip().lower().split())


@dataclass(frozen=True)
class SearchCacheKey:
    """Cache key for a provider search."""

    provider_id: str
    query: str
    limit: int

    @staticmethod
    def create(*, provider_id: str, query: str, limit: int) -> "SearchCacheKey":
        return SearchCacheKey(
            provider_id=(provider_id or "").strip().lower(),
            query=normalize_query(query),
            limit=int(limit),
        )


class SearchCache(Protocol):
    """Cache interface for search results."""

    def get(self, key: SearchCacheKey) -> Optional[list[SearchResult]]:
        """Return cached results, or None if absent."""

    def set(self, key: SearchCacheKey, value: list[SearchResult]) -> None:
        """Store results for later reuse."""


class InMemorySearchCache:
    """Simple in-memory cache keyed by provider/query/limit."""

    def __init__(self) -> None:
        self._data: dict[SearchCacheKey, list[SearchResult]] = {}

    def get(self, key: SearchCacheKey) -> Optional[list[SearchResult]]:
        return self._data.get(key)

    def set(self, key: SearchCacheKey, value: list[SearchResult]) -> None:
        self._data[key] = list(value)


def _serialize_search_result(result: SearchResult) -> dict[str, Any]:
    return {
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
        "attributes": dict(result.attributes or {}),
        "stock_quantity": result.stock_quantity,
    }


def _deserialize_search_result(data: dict[str, Any]) -> SearchResult:
    return SearchResult(
        manufacturer=str(data.get("manufacturer", "")),
        mpn=str(data.get("mpn", "")),
        description=str(data.get("description", "")),
        datasheet=str(data.get("datasheet", "")),
        distributor=str(data.get("distributor", "")),
        distributor_part_number=str(data.get("distributor_part_number", "")),
        availability=str(data.get("availability", "")),
        price=str(data.get("price", "")),
        details_url=str(data.get("details_url", "")),
        raw_data=dict(data.get("raw_data", {}) or {}),
        lifecycle_status=str(data.get("lifecycle_status", "Unknown")),
        min_order_qty=int(data.get("min_order_qty", 1) or 1),
        category=str(data.get("category", "")),
        attributes=dict(data.get("attributes", {}) or {}),
        stock_quantity=int(data.get("stock_quantity", 0) or 0),
    )


def _parse_iso8601_timestamp(text: str) -> datetime:
    """Parse an ISO8601 timestamp.

    Supports the common trailing 'Z' suffix.
    """

    t = (text or "").strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"

    dt = datetime.fromisoformat(t)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class DiskSearchCache:
    """Persistent per-provider search cache.

    Stores one JSON file per cache key at `~/.cache/jbom/search/{provider_id}/`.
    """

    def __init__(
        self,
        provider_id: str,
        *,
        ttl: timedelta | None = None,
        cache_root: Path | None = None,
    ) -> None:
        self._provider_id = (provider_id or "").strip().lower()

        if ttl is None:
            supplier = resolve_supplier_by_id(self._provider_id)
            ttl_hours = (
                supplier.search_cache_ttl_hours if supplier is not None else None
            )

            if ttl_hours is None:
                logger.warning(
                    "Supplier profile '%s' missing search.cache.ttl_hours; defaulting DiskSearchCache TTL to 24h",
                    self._provider_id,
                )
                ttl = timedelta(hours=24)
            else:
                try:
                    ttl_hours_f = float(ttl_hours)
                except (TypeError, ValueError):
                    ttl_hours_f = 0.0

                if ttl_hours_f <= 0:
                    logger.warning(
                        "Supplier profile '%s' has invalid search.cache.ttl_hours=%r; defaulting DiskSearchCache TTL to 24h",
                        self._provider_id,
                        ttl_hours,
                    )
                    ttl = timedelta(hours=24)
                else:
                    ttl = timedelta(hours=ttl_hours_f)

        self._ttl = ttl

        root = cache_root if cache_root is not None else Path("~/.cache/jbom/search")
        self._root = Path(root).expanduser()
        self._provider_dir = self._root / self._provider_id

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @staticmethod
    def clear_provider(provider_id: str, *, cache_root: Path | None = None) -> None:
        """Delete all cached entries for provider_id."""

        pid = (provider_id or "").strip().lower()
        root = cache_root if cache_root is not None else Path("~/.cache/jbom/search")
        provider_dir = Path(root).expanduser() / pid

        if provider_dir.exists():
            shutil.rmtree(provider_dir)

    def clear(self) -> None:
        """Delete all cached entries for this provider."""

        DiskSearchCache.clear_provider(self._provider_id, cache_root=self._root)

    def _key_filename(self, key: SearchCacheKey) -> str:
        token = f"{key.provider_id}{key.query}{key.limit}"
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return f"{digest}.json"

    def _path_for_key(self, key: SearchCacheKey) -> Path:
        return self._provider_dir / self._key_filename(key)

    def get(self, key: SearchCacheKey) -> Optional[list[SearchResult]]:
        path = self._path_for_key(key)
        if not path.exists():
            return None

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            expires_at = _parse_iso8601_timestamp(str(payload.get("expires_at", "")))
        except Exception:
            # Corrupt cache entry — delete and treat as miss.
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
            return None

        now = datetime.now(timezone.utc)
        if expires_at <= now:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
            return None

        results = payload.get("results", [])
        if not isinstance(results, list):
            return None

        out: list[SearchResult] = []
        for r in results:
            if not isinstance(r, dict):
                continue
            out.append(_deserialize_search_result(r))

        return out

    def set(self, key: SearchCacheKey, value: list[SearchResult]) -> None:
        self._provider_dir.mkdir(parents=True, exist_ok=True)

        expires_at = datetime.now(timezone.utc) + self._ttl
        payload = {
            "key": {
                "provider_id": key.provider_id,
                "query": key.query,
                "limit": key.limit,
            },
            "results": [_serialize_search_result(r) for r in value],
            "expires_at": expires_at.isoformat(),
        }

        path = self._path_for_key(key)
        tmp_path = Path(str(path) + ".tmp")
        tmp_path.write_text(json.dumps(payload), encoding="utf-8")
        os.replace(tmp_path, path)


__all__ = [
    "DiskSearchCache",
    "InMemorySearchCache",
    "SearchCache",
    "SearchCacheKey",
    "normalize_query",
]
