"""Null search provider for testing and generic supplier profile.

Always available.  Returns an empty list by default.  When ``fixtures``
is configured in the provider config (path to a JSON file), deserializes
and returns those :class:`SearchResult` objects.

Registered as provider type ``null_api``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jbom.services.search.models import SearchResult
from jbom.services.search.provider import SearchProvider

if TYPE_CHECKING:
    from jbom.common.types import InventoryItem
    from jbom.config.providers import SearchProviderConfig
    from jbom.services.search.cache import SearchCache


class NullSearchProvider(SearchProvider):
    """A no-op search provider for testing and the generic supplier profile.

    Always reports :meth:`available` as ``True``.  Returns an empty list by
    default.  When ``fixtures`` is configured in the provider config, loads
    :class:`SearchResult` objects from the JSON fixture file and returns them
    from every search call.
    """

    def __init__(self, *, fixtures_path: Path | None = None) -> None:
        """Create a NullSearchProvider.

        Args:
            fixtures_path: Optional path to a JSON fixture file.  When
                present and readable, :meth:`search` returns those results.
        """
        self._fixtures_path = fixtures_path
        self._fixtures: list[SearchResult] = []

        if fixtures_path is not None and fixtures_path.is_file():
            try:
                raw = json.loads(fixtures_path.read_text(encoding="utf-8"))
                if isinstance(raw, list):
                    self._fixtures = [_result_from_dict(r) for r in raw]
            except Exception:
                self._fixtures = []

    @classmethod
    def from_config(
        cls, cfg: "SearchProviderConfig", *, cache: "SearchCache"
    ) -> "NullSearchProvider":
        """Instantiate from supplier YAML config.

        Reads optional ``fixtures`` key from ``cfg.extra``.  The value may be
        an absolute path or a path relative to the process working directory.

        Args:
            cfg: Provider configuration (``cfg.extra["fixtures"]`` is optional).
            cache: Unused — NullSearchProvider never makes network requests.
        """
        raw_fixtures = cfg.extra.get("fixtures")
        fixtures_path: Path | None = None
        if raw_fixtures:
            p = Path(str(raw_fixtures))
            fixtures_path = p if p.is_absolute() else (Path.cwd() / p)
        return cls(fixtures_path=fixtures_path)

    def available(self) -> bool:
        """Always True — no API key, network, or database required."""
        return True

    def unavailable_reason(self) -> str:
        """Never called since :meth:`available` always returns ``True``."""
        return ""

    @property
    def provider_id(self) -> str:
        """Stable provider identifier."""
        return "null"

    @property
    def name(self) -> str:
        """Human-readable name."""
        return "Null (fixture / no-op)"

    def search(self, query: str, *, limit: int = 10) -> list[SearchResult]:
        """Return fixture results if configured, otherwise empty list.

        Args:
            query: Ignored.
            limit: Maximum number of results.

        Returns:
            Up to *limit* fixture results, or empty list when no fixtures.
        """
        return list(self._fixtures[:limit])

    def search_for_item(
        self, item: "InventoryItem", *, query: str, limit: int = 10
    ) -> list[SearchResult]:
        """Delegates to :meth:`search`."""
        return self.search(query, limit=limit)

    def lookup_by_mpn(self, manufacturer: str, mpn: str) -> SearchResult | None:
        """Return the first fixture result if any, otherwise ``None``."""
        return self._fixtures[0] if self._fixtures else None


def _result_from_dict(d: dict[str, Any]) -> SearchResult:
    """Deserialize a :class:`SearchResult` from a fixture dict."""
    return SearchResult(
        manufacturer=str(d.get("manufacturer", "")),
        mpn=str(d.get("mpn", "")),
        description=str(d.get("description", "")),
        datasheet=str(d.get("datasheet", "")),
        distributor=str(d.get("distributor", "generic")),
        distributor_part_number=str(d.get("distributor_part_number", "")),
        availability=str(d.get("availability", "")),
        price=str(d.get("price", "")),
        details_url=str(d.get("details_url", "")),
        raw_data={},
        stock_quantity=int(d.get("stock_quantity", 0) or 0),
    )


__all__ = ["NullSearchProvider"]
