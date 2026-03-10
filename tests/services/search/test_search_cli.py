from __future__ import annotations

import argparse

from jbom.cli.search import _build_cache as _build_search_cache
from jbom.cli.search import handle_search
from jbom.services.search.cache import DiskSearchCache, InMemorySearchCache
from jbom.services.search.models import SearchResult


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


def test_build_cache_no_cache_flag_returns_inmemory(monkeypatch) -> None:
    args = argparse.Namespace(provider="mouser", no_cache=True, clear_cache=False)
    cache = _build_search_cache(args)
    assert isinstance(cache, InMemorySearchCache)


def test_build_cache_clear_cache_flag_calls_clear_provider(monkeypatch) -> None:
    calls: dict[str, str] = {}

    def _clear_provider(provider_id: str, *, cache_root=None) -> None:
        calls["provider_id"] = provider_id

    monkeypatch.setattr(
        DiskSearchCache, "clear_provider", staticmethod(_clear_provider)
    )

    args = argparse.Namespace(provider="mouser", no_cache=True, clear_cache=True)
    cache = _build_search_cache(args)
    assert isinstance(cache, InMemorySearchCache)
    assert calls["provider_id"] == "mouser"


def test_search_console_output(monkeypatch, capsys):
    # Avoid any network calls.
    import jbom.suppliers.mouser.provider as mouser_provider

    monkeypatch.setattr(
        mouser_provider.MouserProvider,
        "search",
        lambda self, query, *, limit=10: [_sr()],
    )

    args = argparse.Namespace(
        query="10K resistor 0603",
        provider="mouser",
        limit=1,
        api_key="dummy",
        all=True,
        no_parametric=True,
        output="console",
        fields=None,
        list_fields=False,
    )

    rc = handle_search(args, _cache=InMemorySearchCache())
    assert rc == 0

    out = capsys.readouterr().out
    assert "Supplier PN" in out
    assert "Description" in out
    assert "123-ABC" in out  # supplier_part_number


def test_search_csv_stdout(monkeypatch, capsys):
    import jbom.suppliers.mouser.provider as mouser_provider

    monkeypatch.setattr(
        mouser_provider.MouserProvider,
        "search",
        lambda self, query, *, limit=10: [_sr()],
    )

    args = argparse.Namespace(
        query="10K resistor 0603",
        provider="mouser",
        limit=1,
        api_key="dummy",
        all=True,
        no_parametric=True,
        output="-",
        fields=None,
        list_fields=False,
    )

    rc = handle_search(args, _cache=InMemorySearchCache())
    assert rc == 0

    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("Supplier PN,Price,Stock")
    assert any("123-ABC" in line for line in out[1:])


def test_search_csv_file(monkeypatch, tmp_path):
    import jbom.suppliers.mouser.provider as mouser_provider

    monkeypatch.setattr(
        mouser_provider.MouserProvider,
        "search",
        lambda self, query, *, limit=10: [_sr()],
    )

    outpath = tmp_path / "out.csv"

    args = argparse.Namespace(
        query="10K resistor 0603",
        provider="mouser",
        limit=1,
        api_key="dummy",
        all=True,
        no_parametric=True,
        output=str(outpath),
        fields=None,
        list_fields=False,
    )

    rc = handle_search(args, _cache=InMemorySearchCache())
    assert rc == 0

    text = outpath.read_text(encoding="utf-8")
    assert text.splitlines()[0].startswith("Supplier PN,Price,Stock")
    assert "123-ABC" in text


def test_search_list_fields_exits_without_api_key(monkeypatch, capsys):
    # This should not require an API key and should not call providers.
    import jbom.suppliers.mouser.provider as mouser_provider

    def _boom(*_a, **_kw):
        raise AssertionError("Provider.search should not be called for --list-fields")

    monkeypatch.setattr(mouser_provider.MouserProvider, "search", _boom)

    args = argparse.Namespace(
        query="ignored",
        provider="mouser",
        limit=1,
        api_key=None,
        all=True,
        no_parametric=True,
        output="console",
        fields=None,
        list_fields=True,
    )

    rc = handle_search(args, _cache=InMemorySearchCache())
    assert rc == 0

    out = capsys.readouterr().out
    assert "supplier_part_number" in out
    assert "Supplier PN" in out


def test_search_fields_override_affects_csv_schema(monkeypatch, capsys):
    import jbom.suppliers.mouser.provider as mouser_provider

    monkeypatch.setattr(
        mouser_provider.MouserProvider,
        "search",
        lambda self, query, *, limit=10: [_sr()],
    )

    args = argparse.Namespace(
        query="10K resistor 0603",
        provider="mouser",
        limit=1,
        api_key="dummy",
        all=True,
        no_parametric=True,
        output="-",
        fields="mpn,manufacturer",
        list_fields=False,
    )

    rc = handle_search(args, _cache=InMemorySearchCache())
    assert rc == 0

    out = capsys.readouterr().out.splitlines()
    assert out[0] == "MPN,Manufacturer"
    assert any("RC0603FR-0710KL" in line for line in out[1:])
    assert any("Yageo" in line for line in out[1:])


def test_search_unknown_field_rejected(monkeypatch, capsys):
    import jbom.suppliers.mouser.provider as mouser_provider

    def _boom(*_a, **_kw):
        raise AssertionError("Provider.search should not be called on invalid --fields")

    monkeypatch.setattr(mouser_provider.MouserProvider, "search", _boom)

    args = argparse.Namespace(
        query="10K resistor 0603",
        provider="mouser",
        limit=1,
        api_key="dummy",
        all=True,
        no_parametric=True,
        output="console",
        fields="does_not_exist",
        list_fields=False,
    )

    rc = handle_search(args, _cache=InMemorySearchCache())
    assert rc == 1

    captured = capsys.readouterr()
    assert "Unknown field" in captured.err
    assert "does_not_exist" in captured.err


def test_search_lcsc_provider_exits_cleanly_when_unavailable(monkeypatch, capsys):
    # Avoid live network calls by forcing the provider to be unavailable.
    import jbom.suppliers.lcsc.api as api_mod

    monkeypatch.setattr(api_mod, "requests", None)

    args = argparse.Namespace(
        query="10K resistor 0603",
        provider="lcsc",
        limit=1,
        api_key=None,
        all=True,
        no_parametric=True,
        output="console",
        fields=None,
        list_fields=False,
    )

    rc = handle_search(args, _cache=InMemorySearchCache())
    assert rc == 1

    captured = capsys.readouterr()
    assert "requires the 'requests' package" in captured.err
