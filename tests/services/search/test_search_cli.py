from __future__ import annotations

import argparse

from jbom.cli.search import handle_search
from jbom.services.search.cache import InMemorySearchCache
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


def test_search_console_output(monkeypatch, capsys):
    # Avoid any network calls.
    from jbom.services.search import mouser_provider

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
    )

    rc = handle_search(args, _cache=InMemorySearchCache())
    assert rc == 0

    out = capsys.readouterr().out
    assert "Manufacturer" in out
    assert "Yageo" in out


def test_search_csv_stdout(monkeypatch, capsys):
    from jbom.services.search import mouser_provider

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
    )

    rc = handle_search(args, _cache=InMemorySearchCache())
    assert rc == 0

    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("Manufacturer,MPN,Distributor")
    assert any("Yageo" in line for line in out[1:])


def test_search_csv_file(monkeypatch, tmp_path):
    from jbom.services.search import mouser_provider

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
    )

    rc = handle_search(args, _cache=InMemorySearchCache())
    assert rc == 0

    text = outpath.read_text(encoding="utf-8")
    assert text.splitlines()[0].startswith("Manufacturer,MPN,Distributor")
    assert "Yageo" in text
