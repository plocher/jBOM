from __future__ import annotations

from unittest.mock import Mock
from jbom.common.types import InventoryItem

from jbom.config.providers import SearchProviderConfig
from jbom.services.search.cache import InMemorySearchCache
from jbom.suppliers.lcsc.provider import JlcpcbProvider


def _fake_api_response() -> dict:
    return {
        "code": 200,
        "data": {
            "componentPageInfo": {
                "list": [
                    {
                        "componentCode": "C25231",
                        "componentModelEn": "RC0603FR-0710KL",
                        "componentBrandEn": "Yageo",
                        "describe": "RES SMD 10k 1% 0603",
                        "lcscGoodsUrl": "https://www.lcsc.com/product-detail/C25231.html",
                        "dataManualUrl": "https://example.com/datasheet.pdf",
                        "stockCount": 6609,
                        "minBuyNumber": 1,
                        "componentPrices": [
                            {"productPrice": "0.10", "productNumber": 1},
                            {"productPrice": "0.09", "productNumber": 100},
                        ],
                        "attributes": [
                            {
                                "attribute_name_en": "Resistance",
                                "attribute_value_name": "10kΩ",
                            },
                            {
                                "attribute_name_en": "Tolerance",
                                "attribute_value_name": "1%",
                            },
                        ],
                    }
                ]
            }
        },
    }


def test_jlcpcb_provider_parses_basic_result(monkeypatch) -> None:
    import jbom.suppliers.lcsc.api as api_mod

    # Ensure the provider considers itself available even if requests isn't installed
    # in this test environment.
    monkeypatch.setattr(api_mod, "requests", Mock())

    cache = InMemorySearchCache()
    cfg = SearchProviderConfig(type="jlcpcb_api", extra={"rate_limit_seconds": 0})
    provider = JlcpcbProvider.from_config(cfg, cache=cache)

    assert provider.available() is True

    assert provider._api is not None
    monkeypatch.setattr(
        provider._api, "search_keyword", Mock(return_value=_fake_api_response())
    )

    results = provider.search("10k 0603", limit=5)
    assert len(results) == 1

    r = results[0]
    assert r.distributor == "lcsc"
    assert r.distributor_part_number == "C25231"
    assert r.manufacturer == "Yageo"
    assert r.mpn == "RC0603FR-0710KL"
    assert r.stock_quantity == 6609
    assert r.price == "0.10"
    assert r.attributes.get("Resistance") == "10kΩ"


def test_jlcpcb_provider_uses_cache(monkeypatch) -> None:
    import jbom.suppliers.lcsc.api as api_mod

    monkeypatch.setattr(api_mod, "requests", Mock())

    cache = InMemorySearchCache()
    cfg = SearchProviderConfig(type="jlcpcb_api", extra={"rate_limit_seconds": 0})
    provider = JlcpcbProvider.from_config(cfg, cache=cache)

    assert provider._api is not None
    search_keyword = Mock(return_value=_fake_api_response())
    monkeypatch.setattr(provider._api, "search_keyword", search_keyword)

    provider.search("10k 0603", limit=1)
    provider.search("10k 0603", limit=1)

    assert search_keyword.call_count == 1


def _inv_item(
    *,
    category: str = "RES",
    value: str = "10K",
    tolerance: str = "",
    package: str = "0603",
    smd: str = "SMD",
    resistance: float | None = 10_000.0,
    capacitance: float | None = None,
    voltage: str = "",
    wattage: str = "",
    type_: str = "",
) -> InventoryItem:
    return InventoryItem(
        ipn="TEST-1",
        keywords="",
        category=category,
        description="",
        smd=smd,
        value=value,
        type=type_,
        tolerance=tolerance,
        voltage=voltage,
        amperage="",
        wattage=wattage,
        lcsc="",
        manufacturer="",
        mfgpn="",
        datasheet="",
        package=package,
        resistance=resistance,
        capacitance=capacitance,
        raw_data={},
    )


def test_jlcpcb_provider_lookup_by_mpn_picks_highest_stock(monkeypatch) -> None:
    import jbom.suppliers.lcsc.api as api_mod

    monkeypatch.setattr(api_mod, "requests", Mock())

    cache = InMemorySearchCache()
    cfg = SearchProviderConfig(type="jlcpcb_api", extra={"rate_limit_seconds": 0})
    provider = JlcpcbProvider.from_config(cfg, cache=cache)

    assert provider._api is not None

    api_response = {
        "code": 200,
        "data": {
            "componentPageInfo": {
                "list": [
                    {
                        "componentCode": "C111",
                        "componentModelEn": "RC0603FR-0710KL",
                        "componentBrandEn": "Yageo",
                        "describe": "RES SMD 10k 1% 0603",
                        "lcscGoodsUrl": "https://www.lcsc.com/product-detail/C111.html",
                        "dataManualUrl": "https://example.com/datasheet.pdf",
                        "stockCount": 10,
                        "minBuyNumber": 1,
                        "componentPrices": [
                            {"productPrice": "0.10", "productNumber": 1}
                        ],
                        "attributes": [],
                    },
                    {
                        "componentCode": "C222",
                        "componentModelEn": "RC0603FR-0710KL",
                        "componentBrandEn": "Yageo",
                        "describe": "RES SMD 10k 1% 0603 (alt)",
                        "lcscGoodsUrl": "https://www.lcsc.com/product-detail/C222.html",
                        "dataManualUrl": "https://example.com/datasheet.pdf",
                        "stockCount": 500,
                        "minBuyNumber": 1,
                        "componentPrices": [
                            {"productPrice": "0.09", "productNumber": 1}
                        ],
                        "attributes": [],
                    },
                    {
                        "componentCode": "C333",
                        "componentModelEn": "NOT-THE-SAME",
                        "componentBrandEn": "Yageo",
                        "describe": "noise",
                        "lcscGoodsUrl": "https://www.lcsc.com/product-detail/C333.html",
                        "dataManualUrl": "",
                        "stockCount": 999,
                        "minBuyNumber": 1,
                        "componentPrices": [],
                        "attributes": [],
                    },
                ]
            }
        },
    }

    search_keyword = Mock(return_value=api_response)
    monkeypatch.setattr(provider._api, "search_keyword", search_keyword)

    best = provider.lookup_by_mpn("Yageo", "RC0603FR-0710KL")
    assert best is not None
    assert best.distributor_part_number == "C222"
    assert best.stock_quantity == 500

    assert search_keyword.call_count == 1
    _args, kwargs = search_keyword.call_args
    assert kwargs.get("query") == "RC0603FR-0710KL"
    assert kwargs.get("manufacturer") == "Yageo"


def test_jlcpcb_provider_uses_parametric_search_for_resistor_item(
    monkeypatch,
) -> None:
    import jbom.suppliers.lcsc.api as api_mod

    monkeypatch.setattr(api_mod, "requests", Mock())

    cache = InMemorySearchCache()
    cfg = SearchProviderConfig(type="jlcpcb_api", extra={"rate_limit_seconds": 0})
    provider = JlcpcbProvider.from_config(cfg, cache=cache)

    assert provider._api is not None
    search_parametric = Mock(return_value=_fake_api_response())
    search_keyword = Mock(return_value={"data": {"componentPageInfo": {"list": []}}})
    monkeypatch.setattr(provider._api, "search_parametric", search_parametric)
    monkeypatch.setattr(provider._api, "search_keyword", search_keyword)

    item = _inv_item(category="RES", value="10K", tolerance="", package="0603")
    results = provider.search_for_inventory_item(
        item, query="10K resistor 0603", limit=5
    )

    assert len(results) == 1
    assert search_parametric.call_count == 1
    assert search_keyword.call_count == 0

    _args, kwargs = search_parametric.call_args
    assert kwargs["first_sort_name"] == "Resistors"
    payload_attrs = kwargs["component_attribute_list"]
    assert {"Tolerance": ["5%"]} in payload_attrs


def test_jlcpcb_provider_parametric_search_falls_back_to_keyword_when_empty(
    monkeypatch,
) -> None:
    import jbom.suppliers.lcsc.api as api_mod

    monkeypatch.setattr(api_mod, "requests", Mock())

    cache = InMemorySearchCache()
    cfg = SearchProviderConfig(type="jlcpcb_api", extra={"rate_limit_seconds": 0})
    provider = JlcpcbProvider.from_config(cfg, cache=cache)

    assert provider._api is not None
    search_parametric = Mock(return_value={"data": {"componentPageInfo": {"list": []}}})
    search_keyword = Mock(return_value=_fake_api_response())
    monkeypatch.setattr(provider._api, "search_parametric", search_parametric)
    monkeypatch.setattr(provider._api, "search_keyword", search_keyword)

    item = _inv_item(category="RES", value="10K", tolerance="1%", package="0603")
    results = provider.search_for_inventory_item(
        item, query="10K resistor 0603", limit=5
    )

    assert len(results) == 1
    assert search_parametric.call_count == 1
    assert search_keyword.call_count == 1
