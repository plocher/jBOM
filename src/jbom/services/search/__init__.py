"""Search services.

Phase 6 harvest: external catalog search providers (starting with Mouser),
plus filtering/sorting/caching helpers.

This package is intentionally provider-agnostic.
"""

from jbom.services.search.models import SearchResult
from jbom.services.search.provider import SearchProvider

__all__ = ["SearchProvider", "SearchResult"]
