from __future__ import annotations

from unittest.mock import Mock

import pytest

from jbom.services.search.cache import InMemorySearchCache
from jbom.services.search.mouser_provider import MouserProvider


def _mock_response(payload: dict):
    resp = Mock()
    resp.raise_for_status = Mock()
    resp.json = Mock(return_value=payload)
    return resp


def test_mouser_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("MOUSER_API_KEY", raising=False)
    with pytest.raises(ValueError):
        MouserProvider()


def test_mouser_provider_parses_basic_result(monkeypatch):
    cache = InMemorySearchCache()

    # Provide env key so constructor succeeds.
    monkeypatch.setenv("MOUSER_API_KEY", "dummy")

    import jbom.services.search.mouser_provider as mp

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

    provider = MouserProvider(cache=cache)
    results = provider.search("10K resistor", limit=5)
    assert len(results) == 1

    r = results[0]
    assert r.manufacturer == "Yageo"
    assert r.distributor == "mouser"
    assert r.stock_quantity == 6609
    assert r.attributes.get("Resistance") == "10 kOhms"


def test_mouser_provider_uses_cache(monkeypatch):
    cache = InMemorySearchCache()
    monkeypatch.setenv("MOUSER_API_KEY", "dummy")

    import jbom.services.search.mouser_provider as mp

    post = Mock(return_value=_mock_response({"SearchResults": {"Parts": []}}))
    monkeypatch.setattr(mp, "requests", Mock(post=post))

    provider = MouserProvider(cache=cache)

    provider.search("abc", limit=10)
    provider.search("abc", limit=10)

    assert post.call_count == 1
