"""Unit tests for NullSearchProvider (null_api).

Covers:
- always reports available() == True
- returns [] by default (no fixtures)
- returns fixture results when fixtures path is configured
- search_for_item delegates to search
- lookup_by_mpn returns first fixture or None
- from_config: no fixtures key → empty
- from_config: relative path resolved against cwd
- from_config: absolute path used as-is
- fixture JSON deserialization
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from jbom.suppliers.null.provider import NullSearchProvider, _result_from_dict
from jbom.services.search.models import SearchResult
from jbom.config.providers import SearchProviderConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fixture_result(pn: str = "S25804") -> dict:
    return {
        "manufacturer": "Yageo",
        "mpn": "RC0603FR-0710KL",
        "distributor": "generic",
        "distributor_part_number": pn,
        "description": "RES 10K 1% 0603",
        "datasheet": "",
        "availability": "500 In Stock",
        "price": "0.01",
        "details_url": "",
        "raw_data": {},
        "stock_quantity": 500,
    }


def _write_fixture(directory: Path, results: list[dict]) -> Path:
    fixture_path = directory / "fixtures.json"
    fixture_path.write_text(json.dumps(results), encoding="utf-8")
    return fixture_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNullSearchProviderAvailability:
    def test_always_available(self) -> None:
        provider = NullSearchProvider()
        assert provider.available() is True

    def test_unavailable_reason_empty(self) -> None:
        provider = NullSearchProvider()
        assert provider.unavailable_reason() == ""

    def test_provider_id(self) -> None:
        provider = NullSearchProvider()
        assert provider.provider_id == "null"

    def test_name(self) -> None:
        provider = NullSearchProvider()
        assert "null" in provider.name.lower() or "fixture" in provider.name.lower()


class TestNullSearchProviderNoFixtures:
    def test_search_returns_empty_without_fixtures(self) -> None:
        provider = NullSearchProvider()
        results = provider.search("10K resistor")
        assert results == []

    def test_search_for_item_returns_empty_without_fixtures(self) -> None:
        provider = NullSearchProvider()
        item = MagicMock()
        results = provider.search_for_item(item, query="10K")
        assert results == []

    def test_lookup_by_mpn_returns_none_without_fixtures(self) -> None:
        provider = NullSearchProvider()
        assert provider.lookup_by_mpn("Yageo", "RC0603FR-0710KL") is None

    def test_search_with_nonexistent_fixtures_path(self) -> None:
        provider = NullSearchProvider(fixtures_path=Path("/nonexistent/path.json"))
        assert provider.search("query") == []


class TestNullSearchProviderWithFixtures:
    def test_search_returns_fixture_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = _write_fixture(
                Path(tmpdir), [_make_fixture_result("S25804")]
            )
            provider = NullSearchProvider(fixtures_path=fixture_path)
            results = provider.search("10K resistor")

        assert len(results) == 1
        assert results[0].distributor_part_number == "S25804"

    def test_search_respects_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fixtures = [_make_fixture_result(f"PN{i:03d}") for i in range(10)]
            fixture_path = _write_fixture(Path(tmpdir), fixtures)
            provider = NullSearchProvider(fixtures_path=fixture_path)
            results = provider.search("query", limit=3)

        assert len(results) == 3

    def test_search_for_item_returns_same_as_search(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = _write_fixture(
                Path(tmpdir), [_make_fixture_result("S25804")]
            )
            provider = NullSearchProvider(fixtures_path=fixture_path)
            item = MagicMock()
            results = provider.search_for_item(item, query="10K")

        assert len(results) == 1
        assert results[0].distributor_part_number == "S25804"

    def test_lookup_by_mpn_returns_first_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = _write_fixture(
                Path(tmpdir),
                [_make_fixture_result("S25804"), _make_fixture_result("S99999")],
            )
            provider = NullSearchProvider(fixtures_path=fixture_path)
            result = provider.lookup_by_mpn("Yageo", "RC0603FR-0710KL")

        assert result is not None
        assert result.distributor_part_number == "S25804"

    def test_multiple_fixtures_all_returned(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fixtures = [_make_fixture_result(f"PN{i}") for i in range(5)]
            fixture_path = _write_fixture(Path(tmpdir), fixtures)
            provider = NullSearchProvider(fixtures_path=fixture_path)
            results = provider.search("query")

        assert len(results) == 5


class TestNullSearchProviderFromConfig:
    def _cfg(self, **extra) -> SearchProviderConfig:
        return SearchProviderConfig(type="null_api", extra=extra)

    def _dummy_cache(self):
        return MagicMock()

    def test_from_config_no_fixtures(self) -> None:
        cfg = self._cfg()
        provider = NullSearchProvider.from_config(cfg, cache=self._dummy_cache())
        assert provider.available() is True
        assert provider.search("q") == []

    def test_from_config_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = _write_fixture(Path(tmpdir), [_make_fixture_result("ABS1")])
            cfg = self._cfg(fixtures=str(fixture_path))
            provider = NullSearchProvider.from_config(cfg, cache=self._dummy_cache())
            results = provider.search("q")

        assert len(results) == 1
        assert results[0].distributor_part_number == "ABS1"

    def test_from_config_relative_path_resolved_against_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            fixture_path = _write_fixture(tmppath, [_make_fixture_result("REL1")])
            relative = fixture_path.relative_to(tmppath)
            cfg = self._cfg(fixtures=str(relative))
            with patch("jbom.suppliers.null.provider.Path.cwd", return_value=tmppath):
                provider = NullSearchProvider.from_config(
                    cfg, cache=self._dummy_cache()
                )
            results = provider.search("q")

        assert len(results) == 1
        assert results[0].distributor_part_number == "REL1"

    def test_from_config_nonexistent_fixtures_path_returns_empty(self) -> None:
        cfg = self._cfg(fixtures="/no/such/file.json")
        provider = NullSearchProvider.from_config(cfg, cache=self._dummy_cache())
        assert provider.search("q") == []


class TestResultFromDict:
    def test_basic_deserialization(self) -> None:
        d = _make_fixture_result("X99")
        r = _result_from_dict(d)
        assert isinstance(r, SearchResult)
        assert r.distributor_part_number == "X99"
        assert r.manufacturer == "Yageo"
        assert r.mpn == "RC0603FR-0710KL"
        assert r.stock_quantity == 500

    def test_missing_keys_use_defaults(self) -> None:
        r = _result_from_dict({})
        assert r.distributor_part_number == ""
        assert r.manufacturer == ""
        assert r.distributor == "generic"
        assert r.stock_quantity == 0
