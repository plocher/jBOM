from __future__ import annotations

import functools
import os

import pytest

from jbom.suppliers.mouser.provider import MouserProvider
from jbom.services.search.models import SearchResult


MOUSER_API_KEY = os.environ.get("MOUSER_API_KEY")


@functools.lru_cache(maxsize=1)
def _live_keyword_search_results() -> list[SearchResult]:
    provider = MouserProvider()
    return provider.search("10K resistor 0603", limit=3)


@pytest.mark.integration
@pytest.mark.skipif(not MOUSER_API_KEY, reason="MOUSER_API_KEY not set")
class TestMouserIntegration:
    def test_live_keyword_search_returns_results(self) -> None:
        results = _live_keyword_search_results()
        assert results

    def test_live_search_result_has_required_fields(self) -> None:
        results = _live_keyword_search_results()
        first = results[0]

        assert first.manufacturer
        assert first.mpn
        assert first.distributor_part_number

        assert isinstance(first.stock_quantity, int)
        assert first.stock_quantity >= 0

        assert isinstance(first.attributes, dict)
