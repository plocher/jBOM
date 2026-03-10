from __future__ import annotations

from unittest.mock import Mock

import pytest

from jbom.config.providers import SearchProviderConfig
from jbom.config.suppliers import SupplierConfig
from jbom.services.search.cache import InMemorySearchCache
from jbom.suppliers.mouser.provider import MouserProvider


def _mock_response(payload: dict):
    resp = Mock()
    resp.raise_for_status = Mock()
    resp.json = Mock(return_value=payload)
    return resp


def test_mouser_provider_requires_api_key(monkeypatch):
    import jbom.suppliers.mouser.provider as mp

    monkeypatch.setattr(mp, "requests", Mock())
    monkeypatch.delenv("MOUSER_API_KEY", raising=False)

    provider = MouserProvider(api_key=None)
    assert provider.available() is False
    assert "MOUSER_API_KEY" in provider.unavailable_reason()

    with pytest.raises(RuntimeError):
        provider.search("10K resistor", limit=5)


def test_mouser_provider_parses_basic_result(monkeypatch):
    cache = InMemorySearchCache()

    import jbom.suppliers.mouser.provider as mp

    post = Mock(
        return_value=_mock_response(
            {
                "SearchResults": {
                    "Parts": [
                        {
                            "Manufacturer": "Yageo",
                            "ManufacturerPartNumber": "RC0603FR-0710KL",
                            "Description": "RES 10K",
                            "DataSheetUrl": "http://example",
                            "MouserPartNumber": "123-ABC",
                            "Availability": "6,609 In Stock",
                            "PriceBreaks": [{"Price": "$0.10"}],
                            "ProductDetailUrl": "http://detail",
                            "LifecycleStatus": "Active",
                            "Min": "1",
                            "Category": "Resistors",
                            "ProductAttributes": [
                                {
                                    "AttributeName": "Resistance",
                                    "AttributeValue": "10 kOhms",
                                },
                                {"AttributeName": "Tolerance", "AttributeValue": "1%"},
                            ],
                        }
                    ]
                }
            }
        )
    )
    monkeypatch.setattr(mp, "requests", Mock(post=post))

    cfg = SearchProviderConfig(type="mouser_api", extra={"api_key": "dummy"})
    provider = MouserProvider.from_config(cfg, cache=cache)
    results = provider.search("10K resistor", limit=5)
    assert len(results) == 1

    r = results[0]
    assert r.manufacturer == "Yageo"
    assert r.distributor == "mouser"
    assert r.stock_quantity == 6609
    assert r.attributes.get("Resistance") == "10 kOhms"


def test_mouser_provider_uses_cache(monkeypatch):
    cache = InMemorySearchCache()

    import jbom.suppliers.mouser.provider as mp

    post = Mock(return_value=_mock_response({"SearchResults": {"Parts": []}}))
    monkeypatch.setattr(mp, "requests", Mock(post=post))

    cfg = SearchProviderConfig(type="mouser_api", extra={"api_key": "dummy"})
    provider = MouserProvider.from_config(cfg, cache=cache)

    provider.search("abc", limit=10)
    provider.search("abc", limit=10)

    assert post.call_count == 1


def test_mouser_provider_defaults_retry_settings_when_profile_missing(
    monkeypatch, caplog
):
    cache = InMemorySearchCache()

    import jbom.suppliers.mouser.provider as mp

    # Simulate a supplier profile that exists but doesn't specify search.api.*.
    supplier = SupplierConfig(
        id="mouser",
        name="Mouser",
        inventory_column="Mouser",
        search_cache_ttl_hours=24,
    )
    monkeypatch.setattr(mp, "resolve_supplier_by_id", lambda _sid: supplier)

    cfg = SearchProviderConfig(type="mouser_api", extra={"api_key": "dummy"})
    provider = MouserProvider.from_config(cfg, cache=cache)

    assert provider._timeout == 10.0
    assert provider._max_retries == 3
    assert provider._retry_delay == 1.0

    assert any(
        "missing search.api.timeout_seconds" in r.message for r in caplog.records
    )
    assert any("missing search.api.max_retries" in r.message for r in caplog.records)
    assert any(
        "missing search.api.retry_delay_seconds" in r.message for r in caplog.records
    )
