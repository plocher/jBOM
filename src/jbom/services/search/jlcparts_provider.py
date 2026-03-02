"""JLCParts SQLite provider (stub).

Issue #112 explicitly keeps the JLCParts SQLite implementation out of scope.
This provider exists as a placeholder so supplier profiles can declare a provider
chain for LCSC and the CLI can report a clean "not yet implemented" message.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from jbom.services.search.cache import SearchCache
from jbom.services.search.models import SearchResult
from jbom.services.search.provider import SearchProvider

if TYPE_CHECKING:
    from jbom.config.providers import SearchProviderConfig


@dataclass(frozen=True)
class _Config:
    db_path: str | None


class JlcpartsProvider(SearchProvider):
    """Stub provider for LCSC via a local JLCParts SQLite database."""

    def __init__(self, *, db_path: str | None, cache: SearchCache) -> None:
        self._cfg = _Config(db_path=(db_path or "").strip() or None)
        self._cache = cache

    @classmethod
    def from_config(
        cls, cfg: SearchProviderConfig, *, cache: SearchCache
    ) -> "JlcpartsProvider":
        db_path = cfg.extra.get("db_path")
        db_path_norm = str(db_path).strip() if db_path is not None else ""
        return cls(db_path=db_path_norm or None, cache=cache)

    def available(self) -> bool:
        return False

    def unavailable_reason(self) -> str:
        return (
            "LCSC search provider (jlcparts_sqlite) is not yet implemented. "
            "This will be delivered in a follow-on issue."
        )

    @property
    def provider_id(self) -> str:
        return "lcsc"

    @property
    def name(self) -> str:
        return "LCSC (jlcparts sqlite)"

    def search(self, query: str, *, limit: int = 10) -> list[SearchResult]:
        raise NotImplementedError(self.unavailable_reason())


__all__ = ["JlcpartsProvider"]
