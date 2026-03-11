"""Tests for verbose progress output in InventorySearchService (issue #167)."""

from __future__ import annotations

from unittest.mock import Mock

from jbom.common.types import InventoryItem
from jbom.config.providers import SearchProviderConfig
from jbom.services.search.cache import InMemorySearchCache
from jbom.services.search.inventory_search_service import InventorySearchService
from jbom.services.search.models import SearchResult
from jbom.services.search.provider import SearchProvider
from jbom.suppliers.lcsc.provider import JlcpcbProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _inv_item(
    *,
    ipn: str,
    category: str = "RES",
    value: str = "10K",
    package: str = "0603",
    manufacturer: str = "",
    mfgpn: str = "",
) -> InventoryItem:
    return InventoryItem(
        ipn=ipn,
        keywords="",
        category=category,
        description="",
        smd="",
        value=value,
        type="",
        tolerance="1%",
        voltage="",
        amperage="",
        wattage="",
        lcsc="",
        manufacturer=manufacturer,
        mfgpn=mfgpn,
        datasheet="",
        package=package,
        raw_data={},
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
        attributes={},
        stock_quantity=100,
    )
    base.update(kw)
    return SearchResult(**base)


# ---------------------------------------------------------------------------
# verbose=False (default): no progress lines emitted
# ---------------------------------------------------------------------------


def test_no_verbose_output_by_default_keyword_search(capsys) -> None:
    """With verbose=False (default), keyword search produces no stderr output."""
    provider = Mock(spec=SearchProvider)
    provider.search_for_item = Mock(return_value=[_sr()])
    provider.provider_id = "generic"

    svc = InventorySearchService(provider, request_delay_seconds=0.0)
    svc.search([_inv_item(ipn="R1")])

    captured = capsys.readouterr()
    assert captured.err == ""


def test_no_verbose_output_by_default_mpn_lookup(capsys, monkeypatch) -> None:
    """With verbose=False (default), MPN lookup produces no stderr output."""
    import jbom.suppliers.lcsc.api as api_mod

    monkeypatch.setattr(api_mod, "requests", Mock())
    cache = InMemorySearchCache()
    cfg = SearchProviderConfig(type="jlcpcb_api", extra={"rate_limit_seconds": 0})
    provider = JlcpcbProvider.from_config(cfg, cache=cache)
    monkeypatch.setattr(
        provider,
        "lookup_by_mpn",
        Mock(
            return_value=_sr(
                distributor_part_number="C100",
                manufacturer="Yageo",
                mpn="RC0603FR-0710KL",
            )
        ),
    )

    svc = InventorySearchService(provider, request_delay_seconds=0.0)
    svc.search([_inv_item(ipn="R1", manufacturer="Yageo", mfgpn="RC0603FR-0710KL")])

    captured = capsys.readouterr()
    assert captured.err == ""


# ---------------------------------------------------------------------------
# verbose=True: progress lines emitted to stderr
# ---------------------------------------------------------------------------


def test_verbose_keyword_search_prints_query_progress(capsys) -> None:
    """With verbose=True, each unique query is reported to stderr."""
    provider = Mock(spec=SearchProvider)
    provider.search_for_item = Mock(return_value=[_sr()])
    provider.provider_id = "generic"

    svc = InventorySearchService(provider, request_delay_seconds=0.0, verbose=True)
    items = [
        _inv_item(ipn="R1", value="10K"),
        _inv_item(ipn="R2", value="1K"),
    ]
    svc.search(items)

    captured = capsys.readouterr()
    # Two distinct queries → two progress lines
    assert "[keyword search 1/2]" in captured.err
    assert "[keyword search 2/2]" in captured.err


def test_verbose_keyword_search_dedup_shows_unique_count(capsys) -> None:
    """Deduplication: 5 identical items → 1 query → progress shows 1/1."""
    provider = Mock(spec=SearchProvider)
    provider.search_for_item = Mock(return_value=[_sr()])
    provider.provider_id = "generic"

    svc = InventorySearchService(provider, request_delay_seconds=0.0, verbose=True)
    items = [_inv_item(ipn=f"R{i}", value="10K") for i in range(5)]
    svc.search(items)

    captured = capsys.readouterr()
    assert "[keyword search 1/1]" in captured.err
    # Should only appear once (deduplicated)
    assert captured.err.count("[keyword search") == 1


def test_verbose_mpn_lookup_prints_progress(capsys, monkeypatch) -> None:
    """With verbose=True, each MPN lookup is reported to stderr."""
    import jbom.suppliers.lcsc.api as api_mod

    monkeypatch.setattr(api_mod, "requests", Mock())
    cache = InMemorySearchCache()
    cfg = SearchProviderConfig(type="jlcpcb_api", extra={"rate_limit_seconds": 0})
    provider = JlcpcbProvider.from_config(cfg, cache=cache)
    monkeypatch.setattr(
        provider,
        "lookup_by_mpn",
        Mock(
            return_value=_sr(
                distributor_part_number="C100",
                manufacturer="Yageo",
                mpn="RC0603FR-0710KL",
            )
        ),
    )

    svc = InventorySearchService(provider, request_delay_seconds=0.0, verbose=True)
    svc.search([_inv_item(ipn="R1", manufacturer="Yageo", mfgpn="RC0603FR-0710KL")])

    captured = capsys.readouterr()
    assert "[MPN lookup 1/1]" in captured.err
    assert "Yageo" in captured.err
    assert "RC0603FR-0710KL" in captured.err


def test_verbose_mpn_lookup_dedup_shows_unique_count(capsys, monkeypatch) -> None:
    """Two items with the same MPN → one lookup → progress shows 1/1."""
    import jbom.suppliers.lcsc.api as api_mod

    monkeypatch.setattr(api_mod, "requests", Mock())
    cache = InMemorySearchCache()
    cfg = SearchProviderConfig(type="jlcpcb_api", extra={"rate_limit_seconds": 0})
    provider = JlcpcbProvider.from_config(cfg, cache=cache)
    monkeypatch.setattr(
        provider,
        "lookup_by_mpn",
        Mock(
            return_value=_sr(
                distributor_part_number="C100",
                manufacturer="Yageo",
                mpn="RC0603FR-0710KL",
            )
        ),
    )

    svc = InventorySearchService(provider, request_delay_seconds=0.0, verbose=True)
    items = [
        _inv_item(ipn="R1", manufacturer="Yageo", mfgpn="RC0603FR-0710KL"),
        _inv_item(ipn="R2", manufacturer="Yageo", mfgpn="RC0603FR-0710KL"),
    ]
    svc.search(items)

    captured = capsys.readouterr()
    # Deduplicated: only 1 MPN lookup
    assert "[MPN lookup 1/1]" in captured.err
    assert captured.err.count("[MPN lookup") == 1


def test_verbose_mixed_mpn_and_keyword_search(capsys, monkeypatch) -> None:
    """Items with MPN use lookup path; items without use keyword path; both report progress."""
    import jbom.suppliers.lcsc.api as api_mod

    monkeypatch.setattr(api_mod, "requests", Mock())
    cache = InMemorySearchCache()
    cfg = SearchProviderConfig(type="jlcpcb_api", extra={"rate_limit_seconds": 0})
    provider = JlcpcbProvider.from_config(cfg, cache=cache)
    monkeypatch.setattr(
        provider,
        "lookup_by_mpn",
        Mock(
            return_value=_sr(
                distributor_part_number="C100",
                manufacturer="Yageo",
                mpn="RC0603FR-0710KL",
            )
        ),
    )
    monkeypatch.setattr(provider, "search_for_item", Mock(return_value=[_sr()]))

    svc = InventorySearchService(provider, request_delay_seconds=0.0, verbose=True)
    items = [
        _inv_item(ipn="R1", manufacturer="Yageo", mfgpn="RC0603FR-0710KL"),
        _inv_item(ipn="R2", value="1K"),
    ]
    svc.search(items)

    captured = capsys.readouterr()
    assert "[MPN lookup 1/1]" in captured.err
    assert "[keyword search 1/1]" in captured.err
