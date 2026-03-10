from __future__ import annotations

from unittest.mock import Mock

from jbom.common.types import InventoryItem
from jbom.config.providers import SearchProviderConfig
from jbom.config.fabricators import load_fabricator
from jbom.config.suppliers import SupplierConfig
from jbom.services.search.cache import InMemorySearchCache
from jbom.services.search.inventory_search_service import InventorySearchService
from jbom.suppliers.lcsc.provider import JlcpcbProvider
from jbom.services.search.models import SearchResult
from jbom.services.search.provider import SearchProvider


def _inv_item(
    *,
    ipn: str,
    category: str,
    value: str,
    package: str,
    tolerance: str,
    row_type: str = "ITEM",
    component_id: str = "",
    lcsc: str = "",
    raw_data: dict[str, str] | None = None,
) -> InventoryItem:
    return InventoryItem(
        row_type=row_type,
        component_id=component_id,
        ipn=ipn,
        keywords="",
        category=category,
        description="",
        smd="",
        value=value,
        type="",
        tolerance=tolerance,
        voltage="",
        amperage="",
        wattage="",
        lcsc=lcsc,
        manufacturer="",
        mfgpn="",
        datasheet="",
        package=package,
        raw_data=raw_data or {},
    )


def test_split_rows_by_type_separates_component_and_item_rows() -> None:
    component = _inv_item(
        ipn="",
        category="RES",
        value="10K",
        package="0603",
        tolerance="5%",
        row_type="COMPONENT",
        component_id="1|CAT=RES|PKG=0603|TOL=5%|VAL=10K",
    )
    item = _inv_item(
        ipn="R-10K-0603",
        category="RES",
        value="10K",
        package="0603",
        tolerance="1%",
        row_type="ITEM",
    )

    components, items = InventorySearchService.split_rows_by_type([component, item])
    assert [c.component_id for c in components] == ["1|CAT=RES|PKG=0603|TOL=5%|VAL=10K"]
    assert [i.ipn for i in items] == ["R-10K-0603"]


def _sr(**kw) -> SearchResult:
    base = dict(
        manufacturer="Mfg",
        mpn="MPN",
        description="desc",
        datasheet="",
        distributor="mouser",
        distributor_part_number="123",
        availability="100 In Stock",
        price="$0.10",
        details_url="",
        raw_data={},
        lifecycle_status="Active",
        min_order_qty=1,
        category="",
        attributes={},
        stock_quantity=100,
    )
    base.update(kw)
    return SearchResult(**base)


def test_inventory_search_service_deduplicates_provider_calls_and_fans_out() -> None:
    provider = Mock(spec=SearchProvider)
    provider.search = Mock(return_value=[_sr()])

    svc = InventorySearchService(provider, candidate_limit=1, request_delay_seconds=0.0)

    items: list[InventoryItem] = []

    # 10 items, 3 unique queries.
    items.extend(
        [
            _inv_item(
                ipn=f"R10K-{i}",
                category="RES",
                value="10K",
                package="0603",
                tolerance="1%",
            )
            for i in range(1, 6)
        ]
    )
    items.extend(
        [
            _inv_item(
                ipn=f"R1K-{i}",
                category="RES",
                value="1K",
                package="0603",
                tolerance="1%",
            )
            for i in range(1, 4)
        ]
    )
    items.extend(
        [
            _inv_item(
                ipn=f"C100N-{i}",
                category="CAP",
                value="100nF",
                package="0603",
                tolerance="10%",
            )
            for i in range(1, 3)
        ]
    )

    records = svc.search(items)

    assert provider.search.call_count == 3

    # Preserve fan-out: one record per input item, maintaining associations.
    assert [r.inventory_item.ipn for r in records] == [i.ipn for i in items]
    assert {r.inventory_item.ipn for r in records}.issuperset({"R10K-1", "R10K-2"})

    report = svc.generate_report(records)
    assert "Unique queries dispatched: 3 (of 10 items)" in report


def test_filter_searchable_items_allows_led_single_character_value() -> None:
    items = [
        _inv_item(
            ipn="LED-R-1",
            category="LED",
            value="R",
            package="0603",
            tolerance="",
        ),
        _inv_item(
            ipn="LED-EMPTY",
            category="LED",
            value="",
            package="0603",
            tolerance="",
        ),
    ]

    filtered = InventorySearchService.filter_searchable_items(items, categories=None)
    assert [i.ipn for i in filtered] == ["LED-R-1"]


def test_build_query_uses_supplier_config_keywords(monkeypatch) -> None:
    supplier = SupplierConfig(
        id="mouser",
        name="Mouser",
        inventory_column="Mouser",
        search_type_query_keywords={"RES": "thick film resistor"},
    )

    import jbom.services.search.inventory_search_service as iss

    monkeypatch.setattr(iss, "resolve_supplier_by_id", lambda _sid: supplier)

    class _Provider:
        provider_id = "mouser"

        def search(self, query: str, *, limit: int = 10) -> list[SearchResult]:
            return []

    svc = InventorySearchService(_Provider())
    item = _inv_item(
        ipn="R-TEST",
        category="RES",
        value="10K",
        package="0603",
        tolerance="1%",
    )

    query = svc.build_query(item)
    assert "thick film resistor" in query


def test_filter_sparse_items_for_fabricator_scopes_by_supplier_columns() -> None:
    fab = load_fabricator("jlc")

    items = [
        _inv_item(
            ipn="HAS-LCSC",
            category="RES",
            value="10K",
            package="0603",
            tolerance="1%",
            lcsc="C123",
        ),
        _inv_item(
            ipn="HAS-MOUSER",
            category="RES",
            value="10K",
            package="0603",
            tolerance="1%",
            raw_data={"Mouser": "123"},
        ),
        _inv_item(
            ipn="HAS-FARNELL",
            category="RES",
            value="10K",
            package="0603",
            tolerance="1%",
            raw_data={"Farnell": "F-123"},
        ),
        _inv_item(
            ipn="SPARSE",
            category="RES",
            value="10K",
            package="0603",
            tolerance="1%",
        ),
    ]

    sparse = InventorySearchService.filter_sparse_items_for_fabricator(
        items, fabricator=fab
    )
    assert [i.ipn for i in sparse] == ["SPARSE"]


def test_inventory_search_service_fans_out_provider_errors_to_all_items() -> None:
    err_msg = "provider unavailable"

    def _fake_search(query: str, *, limit: int = 10) -> list[SearchResult]:
        if "10k" in query.lower():
            raise RuntimeError(err_msg)
        return [_sr()]

    provider = Mock(spec=SearchProvider)
    provider.search = Mock(side_effect=_fake_search)

    svc = InventorySearchService(provider, candidate_limit=1, request_delay_seconds=0.0)

    items = [
        _inv_item(
            ipn="R10K-1",
            category="RES",
            value="10K",
            package="0603",
            tolerance="1%",
        ),
        _inv_item(
            ipn="R10K-2",
            category="RES",
            value="10K",
            package="0603",
            tolerance="1%",
        ),
        _inv_item(
            ipn="R1K-1",
            category="RES",
            value="1K",
            package="0603",
            tolerance="1%",
        ),
    ]

    records = svc.search(items)

    # 2 unique queries: one fails, one succeeds.
    assert provider.search.call_count == 2

    by_ipn = {r.inventory_item.ipn: r for r in records}

    assert by_ipn["R10K-1"].candidates == []
    assert by_ipn["R10K-1"].error == err_msg

    assert by_ipn["R10K-2"].candidates == []
    assert by_ipn["R10K-2"].error == err_msg

    assert by_ipn["R1K-1"].candidates
    assert by_ipn["R1K-1"].error is None


def test_inventory_search_service_uses_item_aware_lcsc_dispatch(monkeypatch) -> None:
    import jbom.suppliers.lcsc.api as api_mod

    monkeypatch.setattr(api_mod, "requests", Mock())

    cache = InMemorySearchCache()
    cfg = SearchProviderConfig(type="jlcpcb_api", extra={"rate_limit_seconds": 0})
    provider = JlcpcbProvider.from_config(cfg, cache=cache)

    search_for_inventory_item = Mock(
        return_value=[_sr(distributor="lcsc", distributor_part_number="C25231")]
    )
    monkeypatch.setattr(
        provider, "search_for_inventory_item", search_for_inventory_item
    )

    search_keyword_only = Mock(
        side_effect=AssertionError(
            "provider.search should not be used for JLC inventory item queries"
        )
    )
    monkeypatch.setattr(provider, "search", search_keyword_only)

    svc = InventorySearchService(provider, candidate_limit=1, request_delay_seconds=0.0)

    items = [
        _inv_item(
            ipn="R10K-1",
            category="RES",
            value="10K",
            package="0603",
            tolerance="1%",
        ),
        _inv_item(
            ipn="R10K-2",
            category="RES",
            value="10K",
            package="0603",
            tolerance="1%",
        ),
    ]

    records = svc.search(items)
    assert [r.inventory_item.ipn for r in records] == ["R10K-1", "R10K-2"]
    assert all(r.candidates for r in records)
    assert search_for_inventory_item.call_count == 1
