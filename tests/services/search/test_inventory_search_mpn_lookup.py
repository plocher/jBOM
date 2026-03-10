from __future__ import annotations

from unittest.mock import Mock

from jbom.common.types import InventoryItem
from jbom.config.providers import SearchProviderConfig
from jbom.services.search.cache import InMemorySearchCache
from jbom.services.search.inventory_search_service import InventorySearchService
from jbom.suppliers.lcsc.provider import JlcpcbProvider
from jbom.services.search.models import SearchResult


def _inv_item(*, ipn: str, manufacturer: str, mfgpn: str) -> InventoryItem:
    return InventoryItem(
        ipn=ipn,
        keywords="",
        category="RES",
        description="",
        smd="",
        value="10K",
        type="",
        tolerance="1%",
        voltage="",
        amperage="",
        wattage="",
        lcsc="",
        manufacturer=manufacturer,
        mfgpn=mfgpn,
        datasheet="",
        package="0603",
        raw_data={},
    )


def _sr(*, cnum: str, manufacturer: str, mpn: str, stock: int) -> SearchResult:
    return SearchResult(
        manufacturer=manufacturer,
        mpn=mpn,
        description="RES",
        datasheet="",
        distributor="lcsc",
        distributor_part_number=cnum,
        availability=f"{stock} In Stock",
        price="$0.01",
        details_url="",
        raw_data={},
        lifecycle_status="Active",
        min_order_qty=1,
        attributes={},
        stock_quantity=stock,
    )


def test_inventory_search_service_uses_mpn_lookup_when_available(monkeypatch) -> None:
    import jbom.suppliers.lcsc.api as api_mod

    monkeypatch.setattr(api_mod, "requests", Mock())

    cache = InMemorySearchCache()
    cfg = SearchProviderConfig(type="jlcpcb_api", extra={"rate_limit_seconds": 0})
    provider = JlcpcbProvider.from_config(cfg, cache=cache)

    # Replace lookup/search with mocks so we don't touch the network.
    lookup = Mock(
        return_value=_sr(
            cnum="C222", manufacturer="Yageo", mpn="RC0603FR-0710KL", stock=500
        )
    )
    monkeypatch.setattr(provider, "lookup_by_mpn", lookup)

    search = Mock(
        side_effect=AssertionError(
            "provider.search should not be called when lookup succeeds"
        )
    )
    monkeypatch.setattr(provider, "search", search)

    svc = InventorySearchService(provider, candidate_limit=1, request_delay_seconds=0.0)

    item = _inv_item(ipn="R10K-1", manufacturer="Yageo", mfgpn="RC0603FR-0710KL")
    records = svc.search([item])

    assert len(records) == 1
    assert records[0].candidates
    assert records[0].candidates[0].result.distributor_part_number == "C222"

    lookup.assert_called_once_with("Yageo", "RC0603FR-0710KL")


def test_inventory_search_service_deduplicates_mpn_lookup_calls(monkeypatch) -> None:
    import jbom.suppliers.lcsc.api as api_mod

    monkeypatch.setattr(api_mod, "requests", Mock())

    cache = InMemorySearchCache()
    cfg = SearchProviderConfig(type="jlcpcb_api", extra={"rate_limit_seconds": 0})
    provider = JlcpcbProvider.from_config(cfg, cache=cache)

    lookup = Mock(
        return_value=_sr(
            cnum="C222", manufacturer="Yageo", mpn="RC0603FR-0710KL", stock=500
        )
    )
    monkeypatch.setattr(provider, "lookup_by_mpn", lookup)

    svc = InventorySearchService(provider, candidate_limit=1, request_delay_seconds=0.0)

    items = [
        _inv_item(ipn="R10K-1", manufacturer="Yageo", mfgpn="RC0603FR-0710KL"),
        _inv_item(ipn="R10K-2", manufacturer="Yageo", mfgpn="RC0603FR-0710KL"),
    ]

    records = svc.search(items)
    assert [r.inventory_item.ipn for r in records] == ["R10K-1", "R10K-2"]
    assert all(r.candidates for r in records)

    assert lookup.call_count == 1
