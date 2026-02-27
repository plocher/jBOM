"""Search provider abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod

from jbom.services.search.models import SearchResult


class SearchProvider(ABC):
    """Abstract base class for distributor catalog search providers."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Stable provider identifier (e.g. "mouser")."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name (e.g. "Mouser")."""

    @abstractmethod
    def search(self, query: str, *, limit: int = 10) -> list[SearchResult]:
        """Search by keyword / part number.

        Args:
            query: Search query.
            limit: Max number of results to return.

        Returns:
            List of normalized results.
        """


__all__ = ["SearchProvider"]
