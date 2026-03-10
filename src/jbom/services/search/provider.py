"""Search provider abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from jbom.services.search.models import SearchResult

if TYPE_CHECKING:
    from jbom.common.types import InventoryItem
    from jbom.config.providers import SearchProviderConfig
    from jbom.services.search.cache import SearchCache


class SearchProvider(ABC):
    """Abstract base class for distributor catalog search providers."""

    @classmethod
    @abstractmethod
    def from_config(
        cls, cfg: "SearchProviderConfig", *, cache: "SearchCache"
    ) -> "SearchProvider":
        """Instantiate from supplier YAML config.

        Providers own their own configuration schema (cfg.extra).
        """

    @abstractmethod
    def available(self) -> bool:
        """Return False if the provider cannot run (missing key, missing DB, etc.)."""

    @abstractmethod
    def unavailable_reason(self) -> str:
        """Return an actionable message for why :meth:`available` is False."""

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

    def search_for_item(
        self, item: "InventoryItem", *, query: str, limit: int = 10
    ) -> list[SearchResult]:
        """Search using item context for providers that support parametric routing.

        Default delegates to keyword :meth:`search`.  Override in providers that
        can use item attributes (category, package, value) to build a richer
        query (e.g. JLCPCB parametric API).

        Args:
            item:  Inventory item being searched for.
            query: Pre-built keyword query string (used as fallback).
            limit: Max number of results to return.

        Returns:
            List of normalized results.
        """
        return self.search(query, limit=limit)

    def lookup_by_mpn(self, manufacturer: str, mpn: str) -> SearchResult | None:
        """Deterministically resolve a manufacturer part number to a catalog entry.

        Default returns ``None`` (provider does not support MPN lookup).
        Override in providers that can perform a fast, exact-match MPN resolution
        (e.g. JLCPCB).

        Args:
            manufacturer: Manufacturer name (may be empty).
            mpn:          Manufacturer part number.

        Returns:
            Best matching :class:`SearchResult`, or ``None`` if not found.
        """
        return None


__all__ = ["SearchProvider"]
