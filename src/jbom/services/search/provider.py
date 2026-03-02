"""Search provider abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from jbom.services.search.models import SearchResult

if TYPE_CHECKING:
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


__all__ = ["SearchProvider"]
