from __future__ import annotations

from datetime import timedelta

from jbom.config.suppliers import SupplierConfig
from jbom.services.search.cache import DiskSearchCache, SearchCacheKey
from jbom.services.search.models import SearchResult
from jbom.services.search.mouser_provider import MouserProvider


def _sr(**kw) -> SearchResult:
    base = dict(
        manufacturer="Yageo",
        mpn="RC0603FR-0710KL",
        description="RES 10K",
        datasheet="http://example",
        distributor="mouser",
        distributor_part_number="123-ABC",
        availability="6,609 In Stock",
        price="$0.10",
        details_url="http://detail",
        raw_data={},
        lifecycle_status="Active",
        min_order_qty=1,
        category="Resistors",
        attributes={"Resistance": "10 kOhms"},
        stock_quantity=6609,
    )
    base.update(kw)
    return SearchResult(**base)


def test_disk_cache_round_trip(tmp_path) -> None:
    cache = DiskSearchCache("mouser", cache_root=tmp_path, ttl=timedelta(hours=1))
    key = SearchCacheKey.create(provider_id="mouser", query="10k 0603", limit=3)

    value = [_sr()]
    cache.set(key, value)

    # No temp file should remain after atomic replace.
    provider_dir = tmp_path / "mouser"
    assert provider_dir.exists()
    assert not any(p.name.endswith(".tmp") for p in provider_dir.iterdir())

    got = cache.get(key)
    assert got == value


def test_disk_cache_expiry_deletes_entry(tmp_path) -> None:
    cache = DiskSearchCache("mouser", cache_root=tmp_path, ttl=timedelta(seconds=-1))
    key = SearchCacheKey.create(provider_id="mouser", query="10k 0603", limit=3)

    cache.set(key, [_sr()])

    # Immediately expired.
    assert cache.get(key) is None

    provider_dir = tmp_path / "mouser"
    assert provider_dir.exists()
    assert list(provider_dir.iterdir()) == []


def test_disk_cache_clear_removes_provider_dir(tmp_path) -> None:
    cache = DiskSearchCache("mouser", cache_root=tmp_path, ttl=timedelta(hours=1))
    key = SearchCacheKey.create(provider_id="mouser", query="10k 0603", limit=3)

    cache.set(key, [_sr()])
    provider_dir = tmp_path / "mouser"
    assert provider_dir.exists()

    cache.clear()
    assert not provider_dir.exists()


def test_disk_cache_missing_profile_ttl_falls_back_to_10s(
    tmp_path, monkeypatch, caplog
) -> None:
    from jbom.services.search import cache as cache_mod

    supplier = SupplierConfig(
        id="mouser",
        name="Mouser",
        inventory_column="Mouser",
        # Missing TTL entries on purpose.
        search_cache_ttl_seconds=None,
        search_cache_ttl_hours=None,
    )

    monkeypatch.setattr(cache_mod, "resolve_supplier_by_id", lambda _sid: supplier)

    cache = DiskSearchCache("mouser", cache_root=tmp_path)
    assert cache._ttl == timedelta(seconds=10)

    assert any(
        "defaulting DiskSearchCache TTL to 10s" in rec.message for rec in caplog.records
    )


class _FakeResponse:
    def __init__(self) -> None:
        self.status_code = 200
        self.text = "OK"

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"SearchResults": {"Parts": []}}


def test_mouser_provider_uses_disk_cache_across_instances(
    tmp_path, monkeypatch
) -> None:
    from jbom.services.search import mouser_provider

    calls = {"count": 0}

    def _fake_post(*_args, **_kwargs):
        calls["count"] += 1
        return _FakeResponse()

    monkeypatch.setattr(mouser_provider.requests, "post", _fake_post)
    monkeypatch.setattr(
        MouserProvider,
        "_parse_results",
        lambda _self, _data: [_sr()],
    )

    cache1 = DiskSearchCache("mouser", cache_root=tmp_path, ttl=timedelta(hours=1))
    provider1 = MouserProvider(api_key="dummy", cache=cache1, max_retries=0)
    got1 = provider1.search("10k 0603", limit=1)
    assert calls["count"] == 1
    assert got1

    # New provider instance, same disk cache root -> should be a cache hit.
    cache2 = DiskSearchCache("mouser", cache_root=tmp_path, ttl=timedelta(hours=1))
    provider2 = MouserProvider(api_key="dummy", cache=cache2, max_retries=0)
    got2 = provider2.search("10k 0603", limit=1)

    assert got2 == got1
    assert calls["count"] == 1
