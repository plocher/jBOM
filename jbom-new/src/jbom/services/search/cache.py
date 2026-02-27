"""Search caching helpers.

Phase 6 constraint: keep web API usage low (rate limits / bandwidth). For now we
use in-memory caching, but the interface is designed so we can later add a
persistent user-level cache.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from jbom.services.search.models import SearchResult


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


__all__ = [
    "InMemorySearchCache",
    "SearchCache",
    "SearchCacheKey",
    "normalize_query",
]
