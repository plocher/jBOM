from __future__ import annotations

import argparse
from jbom.cli.main import create_parser

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
    args = argparse.Namespace(supplier="mouser", no_cache=True, clear_cache=False)
    cache = _build_search_cache(args)
    assert isinstance(cache, InMemorySearchCache)


def test_build_cache_clear_cache_flag_calls_clear_provider(monkeypatch) -> None:
    calls: dict[str, str] = {}

    def _clear_provider(provider_id: str, *, cache_root=None) -> None:
        calls["provider_id"] = provider_id

    monkeypatch.setattr(
        DiskSearchCache, "clear_provider", staticmethod(_clear_provider)
    )

    args = argparse.Namespace(supplier="mouser", no_cache=True, clear_cache=True)
    cache = _build_search_cache(args)
    assert isinstance(cache, InMemorySearchCache)
    assert calls["provider_id"] == "mouser"


def test_search_default_supplier_is_generic() -> None:
    parser = create_parser()
    args = parser.parse_args(["search", "10k resistor"])
    assert args.supplier == "generic"


def test_search_supplier_argument_is_case_insensitive() -> None:
    parser = create_parser()
    args = parser.parse_args(["search", "10k resistor", "--supplier", "LCSC"])
    assert args.supplier == "lcsc"


def test_defaults_argument_is_case_insensitive() -> None:
    parser = create_parser()
    args = parser.parse_args(["search", "10k resistor", "--defaults", "GENERIC"])
    assert args.defaults == "generic"


def test_bom_fabricator_argument_is_case_insensitive() -> None:
    parser = create_parser()
    args = parser.parse_args(["bom", ".", "--fabricator", "JLC"])
    assert args.fabricator == "jlc"


def test_parts_fabricator_argument_is_case_insensitive() -> None:
    parser = create_parser()
    args = parser.parse_args(["parts", ".", "--fabricator", "PCBWAY"])
    assert args.fabricator == "pcbway"


def test_search_shapes_led_query_before_provider_call(monkeypatch, capsys) -> None:
    import jbom.suppliers.mouser.provider as mouser_provider

    seen_queries: list[str] = []

    def _search(self, query, *, limit=10):
        seen_queries.append(query)
        return [_sr()]

    monkeypatch.setattr(mouser_provider.MouserProvider, "search", _search)

    args = argparse.Namespace(
        query="led green 0603",
        supplier="mouser",
        limit=1,
        api_key="dummy",
        all=True,
        no_parametric=True,
        output="-",
        fields="supplier_part_number",
        list_fields=False,
    )

    rc = handle_search(args, _cache=InMemorySearchCache())
    assert rc == 0
    assert seen_queries
    shaped = seen_queries[0].lower()
    assert "led" in shaped
    assert "green" in shaped
    assert "0603" in shaped
    assert "smd" in shaped
    assert "indicator" in shaped

    _ = capsys.readouterr()


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
        supplier="mouser",
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
        supplier="mouser",
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

    import csv as csv_mod
    import io

    out_text = capsys.readouterr().out
    reader = csv_mod.reader(io.StringIO(out_text))
    header = next(reader)
    assert header[:4] == ["Supplier PN", "Manufacturer", "MPN", "Package"]
    assert "Category" in header
    assert "Price" in header
    data_rows = list(reader)
    assert any("123-ABC" in cell for row in data_rows for cell in row)


def test_search_adaptive_fetch_expands_when_results_are_sparse(monkeypatch, capsys):
    import jbom.suppliers.mouser.provider as mouser_provider

    calls: list[int] = []

    def _search(self, query, *, limit=10):
        calls.append(int(limit))
        if limit < 100:
            return [
                _sr(mpn="A", distributor_part_number="PN-A", stock_quantity=3),
                _sr(mpn="B", distributor_part_number="PN-B", stock_quantity=2),
                _sr(mpn="C", distributor_part_number="PN-C", stock_quantity=1),
            ]
        return [
            _sr(
                mpn=f"P{i}",
                distributor_part_number=f"PN-{i}",
                stock_quantity=200 - i,
            )
            for i in range(1, 15)
        ]

    monkeypatch.setattr(mouser_provider.MouserProvider, "search", _search)

    args = argparse.Namespace(
        query="10K resistor 0603",
        supplier="mouser",
        limit=10,
        api_key="dummy",
        all=True,
        no_parametric=True,
        output="-",
        fields="supplier_part_number",
        list_fields=False,
    )

    rc = handle_search(args, _cache=InMemorySearchCache())
    assert rc == 0
    assert calls == [50, 100]

    out_text = capsys.readouterr().out
    assert "PN-10" in out_text


def test_search_adaptive_fetch_can_expand_multiple_windows(monkeypatch, capsys):
    import jbom.suppliers.mouser.provider as mouser_provider

    calls: list[int] = []

    def _search(self, query, *, limit=10):
        calls.append(int(limit))
        return [
            _sr(
                mpn=f"P{i}",
                distributor_part_number=f"PN-{i}",
                stock_quantity=5000 - i,
            )
            for i in range(1, int(limit) + 1)
        ]

    def _sparse_filter(results, _query):
        # Keep every 50th item to emulate strict filtering that needs deeper windows.
        return results[::50]

    monkeypatch.setattr(mouser_provider.MouserProvider, "search", _search)
    monkeypatch.setattr(
        "jbom.cli.search.SearchFilter.filter_by_query", staticmethod(_sparse_filter)
    )

    args = argparse.Namespace(
        query="10K resistor 0603",
        supplier="mouser",
        limit=7,
        api_key="dummy",
        all=True,
        no_parametric=False,
        output="-",
        fields="supplier_part_number",
        list_fields=False,
    )

    rc = handle_search(args, _cache=InMemorySearchCache())
    assert rc == 0
    assert calls == [50, 100, 200, 400]
    import csv as csv_mod
    import io

    out_text = capsys.readouterr().out
    reader = csv_mod.reader(io.StringIO(out_text))
    next(reader)  # header
    rows = list(reader)
    assert len(rows) == 7
    assert "PN-301" in out_text


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
        supplier="mouser",
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

    import csv as csv_mod

    text = outpath.read_text(encoding="utf-8")
    reader = csv_mod.reader(text.splitlines())
    header = next(reader)
    assert header[:4] == ["Supplier PN", "Manufacturer", "MPN", "Package"]
    assert "Category" in header
    assert "Price" in header
    assert "123-ABC" in text


def test_search_list_fields_exits_without_api_key(monkeypatch, capsys):
    # This should not require an API key and should not call providers.
    import jbom.suppliers.mouser.provider as mouser_provider

    def _boom(*_a, **_kw):
        raise AssertionError("Provider.search should not be called for --list-fields")

    monkeypatch.setattr(mouser_provider.MouserProvider, "search", _boom)

    args = argparse.Namespace(
        query="ignored",
        supplier="mouser",
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
        supplier="mouser",
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

    import csv as csv_mod
    import io

    out_text = capsys.readouterr().out
    reader = csv_mod.reader(io.StringIO(out_text))
    header = next(reader)
    assert header == ["MPN", "Manufacturer"]
    data_rows = list(reader)
    assert any("RC0603FR-0710KL" in cell for row in data_rows for cell in row)
    assert any("Yageo" in cell for row in data_rows for cell in row)


def test_search_fields_aliases_are_accepted(monkeypatch, capsys):
    import jbom.suppliers.mouser.provider as mouser_provider

    monkeypatch.setattr(
        mouser_provider.MouserProvider,
        "search",
        lambda self, query, *, limit=10: [_sr()],
    )

    args = argparse.Namespace(
        query="10K resistor 0603",
        supplier="mouser",
        limit=1,
        api_key="dummy",
        all=True,
        no_parametric=True,
        output="-",
        fields="Category,Description,Manufacturer,MPN,Package,Price,Stock,Supplier_PN",
        list_fields=False,
    )

    rc = handle_search(args, _cache=InMemorySearchCache())
    assert rc == 0

    import csv as csv_mod
    import io

    out_text = capsys.readouterr().out
    reader = csv_mod.reader(io.StringIO(out_text))
    header = next(reader)
    assert header == [
        "Category",
        "Description",
        "Manufacturer",
        "MPN",
        "Package",
        "Price",
        "Stock",
        "Supplier PN",
    ]


def test_search_package_and_category_use_raw_payload_fallback(monkeypatch, capsys):
    import jbom.suppliers.mouser.provider as mouser_provider

    fallback_result = _sr(
        category="",
        raw_data={
            "componentSpecificationEn": "0603",
            "firstSortName": "Chip Resistor - Surface Mount",
            "secondSortName": "Resistors",
        },
    )

    monkeypatch.setattr(
        mouser_provider.MouserProvider,
        "search",
        lambda self, query, *, limit=10: [fallback_result],
    )

    args = argparse.Namespace(
        query="10K resistor 0603",
        supplier="mouser",
        limit=1,
        api_key="dummy",
        all=True,
        no_parametric=True,
        output="-",
        fields="category,package",
        list_fields=False,
    )

    rc = handle_search(args, _cache=InMemorySearchCache())
    assert rc == 0

    import csv as csv_mod
    import io

    out_text = capsys.readouterr().out
    reader = csv_mod.reader(io.StringIO(out_text))
    header = next(reader)
    row = next(reader)
    assert header == ["Category", "Package"]
    assert row == ["Resistors: Chip Resistor - Surface Mount", "0603"]


def test_search_description_shows_library_tier_notation(monkeypatch, capsys):
    import jbom.suppliers.mouser.provider as mouser_provider

    basic = _sr(
        distributor_part_number="PN-BASIC",
        description="10K 0603 resistor",
        raw_data={"componentLibraryType": "base"},
    )
    extended = _sr(
        distributor_part_number="PN-EXT",
        description="10K 0603 resistor",
        raw_data={"componentLibraryType": "expand"},
    )

    monkeypatch.setattr(
        mouser_provider.MouserProvider,
        "search",
        lambda self, query, *, limit=10: [basic, extended],
    )

    args = argparse.Namespace(
        query="10K resistor 0603",
        supplier="mouser",
        limit=2,
        api_key="dummy",
        all=True,
        no_parametric=True,
        output="-",
        fields="supplier_part_number,description",
        list_fields=False,
    )

    rc = handle_search(args, _cache=InMemorySearchCache())
    assert rc == 0

    import csv as csv_mod
    import io

    out_text = capsys.readouterr().out
    reader = csv_mod.reader(io.StringIO(out_text))
    header = next(reader)
    rows = list(reader)
    assert header == ["Supplier PN", "Description"]
    assert ["PN-BASIC", "[basic] 10K 0603 resistor"] in rows
    assert ["PN-EXT", "[extended] 10K 0603 resistor"] in rows


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
        supplier="lcsc",
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


def test_search_errors_when_no_profile_default_fields(monkeypatch, capsys):
    import jbom.suppliers.mouser.provider as mouser_provider

    def _boom(*_a, **_kw):
        raise AssertionError("Provider.search should not be called with no defaults")

    class _NoFieldsDefaults:
        name = "empty"

        def get_search_output_fields_default(self) -> list[str]:
            return []

    monkeypatch.setattr(mouser_provider.MouserProvider, "search", _boom)
    monkeypatch.setattr("jbom.cli.search.get_defaults", lambda: _NoFieldsDefaults())

    args = argparse.Namespace(
        query="10K resistor 0603",
        supplier="mouser",
        limit=1,
        api_key="dummy",
        all=True,
        no_parametric=True,
        output="console",
        fields=None,
        list_fields=False,
    )

    rc = handle_search(args, _cache=InMemorySearchCache())
    assert rc == 1

    captured = capsys.readouterr()
    assert "No default search fields configured" in captured.err
