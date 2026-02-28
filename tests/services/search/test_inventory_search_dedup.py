from __future__ import annotations

from unittest.mock import Mock

from jbom.common.types import InventoryItem
from jbom.services.search.inventory_search_service import InventorySearchService
from jbom.services.search.models import SearchResult
from jbom.services.search.provider import SearchProvider


def _inv_item(
    *,
    ipn: str,
    category: str,
    value: str,
    package: str,
    tolerance: str,
) -> InventoryItem:
    return InventoryItem(
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
        lcsc="",
        manufacturer="",
        mfgpn="",
        datasheet="",
        package=package,
    )


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
