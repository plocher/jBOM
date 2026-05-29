"""Unit tests for the promote subpackage (adapter / parser / identity / workflow)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from jbom.services.promote.description_parser import (
    derive_category,
    parse_description,
)
from jbom.services.promote.identity import build_ipn
from jbom.services.promote.source_adapters import (
    GenericCsvAdapter,
    JlcpcbExportAdapter,
    detect_source_format,
    select_adapter,
)
from jbom.services.promote.workflow import (
    CANONICAL_FIELDS,
    PromotionResult,
    promote_rows,
)
from jbom.services.search.inventory_search_service import (
    InventorySearchCandidate,
    InventorySearchRecord,
)
from jbom.services.search.models import SearchResult


# ---------------------------------------------------------------------------
# Adapter tests
# ---------------------------------------------------------------------------


def test_detect_source_format_recognizes_jlc_headers() -> None:
    headers = [
        "Category",
        "MFR Part #",
        "Footprint",
        "Description",
        "JLCPCB Part #",
        "JLCPCB Parts Qty",
    ]
    assert detect_source_format(headers) == "jlc"


def test_detect_source_format_falls_back_to_generic() -> None:
    headers = ["IPN", "Category", "Value", "Package"]
    assert detect_source_format(headers) == "generic"


def test_jlc_adapter_maps_canonical_fields() -> None:
    adapter = JlcpcbExportAdapter()
    seed = adapter.adapt(
        {
            "Category": "Capacitors",
            "MFR Part #": "CC0603KRX7R9BB104",
            "Footprint": "0603",
            "Description": "0.1uF 50V X7R 10% 0603",
            "JLCPCB Part #": "C2286",
            "JLCPCB Parts Qty": "120",
            "Unit Price($)": "0.01",
        }
    )
    assert seed.spn == "C2286"
    assert seed.mfgpn == "CC0603KRX7R9BB104"
    assert seed.package == "0603"
    assert seed.category_hint == "Capacitors"
    assert seed.description == "0.1uF 50V X7R 10% 0603"
    assert seed.extras == {
        "JLCPCB Parts Qty": "120",
        "Unit Price($)": "0.01",
    }


def test_generic_adapter_passthrough_with_extras() -> None:
    adapter = GenericCsvAdapter()
    seed = adapter.adapt(
        {
            "SPN": "ABC",
            "MPN": "XYZ",
            "Manufacturer": "ACME",
            "Category": "Resistor",
            "Package": "0603",
            "Description": "10K 1% 0603",
            "CustomCol": "kept",
        }
    )
    assert seed.spn == "ABC"
    assert seed.mfgpn == "XYZ"
    assert seed.manufacturer == "ACME"
    assert seed.package == "0603"
    assert seed.category_hint == "Resistor"
    assert seed.description == "10K 1% 0603"
    assert seed.extras == {"CustomCol": "kept"}


def test_select_adapter_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        select_adapter("nope")


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


def test_parse_capacitor_description() -> None:
    parsed = parse_description(
        "0.1uF 50V X7R ±10% 0603",
        category_hint="Capacitors",
        package_hint="0603",
        mfgpn="CC0603KRX7R9BB104",
    )
    assert parsed.category == "CAP"
    assert parsed.package == "0603"
    assert parsed.tolerance == "10%"
    assert parsed.voltage == "50V"
    assert parsed.type == "X7R"
    assert parsed.capacitance == pytest.approx(0.1e-6, rel=1e-3)
    assert parsed.value


def test_parse_resistor_description_supports_ohm_symbol() -> None:
    parsed = parse_description(
        "10kΩ 1% 0603 chip resistor",
        category_hint="Resistors",
        package_hint="0603",
    )
    assert parsed.category == "RES"
    assert parsed.resistance == pytest.approx(10000.0, rel=1e-6)
    assert parsed.tolerance == "1%"
    assert parsed.package == "0603"
    assert parsed.value


def test_parse_inductor_description() -> None:
    parsed = parse_description(
        "10uH 5% 1210 shielded power inductor",
        category_hint="Inductors",
        package_hint="1210",
    )
    assert parsed.category == "IND"
    assert parsed.inductance == pytest.approx(10e-6, rel=1e-6)
    assert parsed.tolerance == "5%"
    assert parsed.package == "1210"
    assert parsed.value


def test_parse_led_description() -> None:
    parsed = parse_description(
        "Red LED 620nm 100mcd 120° 0603",
        category_hint="LEDs",
        package_hint="0603",
    )
    assert parsed.category == "LED"
    assert parsed.wavelength == "620nm"
    assert parsed.mcd == "100mcd"
    assert parsed.angle == "120°"
    assert parsed.package == "0603"


def test_derive_category_uses_hint_first() -> None:
    assert derive_category(category_hint="Resistors") == "RES"
    assert derive_category(category_hint="Diodes") == "DIO"


def test_derive_category_falls_back_to_description() -> None:
    assert derive_category(description="Schottky DIODE 30V") == "DIO"


# ---------------------------------------------------------------------------
# Identity policy tests
# ---------------------------------------------------------------------------


def test_build_ipn_passive_capacitor() -> None:
    parsed = parse_description(
        "0.1uF 50V X7R 10% 0603",
        category_hint="Capacitors",
        package_hint="0603",
    )
    ipn = build_ipn(parsed)
    assert ipn.startswith("CAP_")
    assert "0603" in ipn
    assert "X7R" in ipn


def test_build_ipn_returns_empty_when_unsupported_category() -> None:
    parsed = parse_description("AMS1117-3.3 LDO regulator SOT-223")
    parsed.category = "IC"
    assert build_ipn(parsed) == ""


# ---------------------------------------------------------------------------
# Workflow tests (with mocked enrichment)
# ---------------------------------------------------------------------------


def _fake_search_result(*, mpn: str, dpn: str) -> SearchResult:
    return SearchResult(
        manufacturer="YAGEO",
        mpn=mpn,
        description="0.1uF 50V X7R 10% 0603",
        datasheet="https://example.com/datasheet.pdf",
        distributor="lcsc",
        distributor_part_number=dpn,
        availability="In Stock",
        price="0.01",
        details_url="https://example.com/details",
        raw_data={},
    )


def test_workflow_produces_canonical_columns_without_enrichment() -> None:
    adapter = JlcpcbExportAdapter()
    rows = [
        {
            "Category": "Capacitors",
            "MFR Part #": "CC0603KRX7R9BB104",
            "Footprint": "0603",
            "Description": "0.1uF 50V X7R 10% 0603",
            "JLCPCB Part #": "C2286",
            "JLCPCB Parts Qty": "120",
        }
    ]
    result: PromotionResult = promote_rows(
        rows,
        adapter=adapter,
        supplier_context="lcsc",
        supplier_label="LCSC",
        search_service=None,
    )
    assert result.stats.rows_total == 1
    assert result.stats.rows_parsed == 1
    assert result.stats.rows_with_canonical_value == 1
    assert result.stats.rows_enrichment_skipped == 1
    canonical = result.rows[0].canonical
    for column in (
        "RowType",
        "Category",
        "Value",
        "Package",
        "Tolerance",
        "Type",
        "V",
        "Capacitance",
        "SupplierContext",
    ):
        assert column in CANONICAL_FIELDS, column
        assert column in canonical, column
    assert canonical["Category"] == "CAP"
    assert canonical["Package"] == "0603"
    assert canonical["Tolerance"] == "10%"
    assert canonical["Type"] == "X7R"
    assert canonical["V"] == "50V"
    assert canonical["SPN"] == "C2286"
    assert canonical["MFGPN"] == "CC0603KRX7R9BB104"
    assert canonical["Supplier"] == "LCSC"
    assert canonical["SupplierContext"] == "lcsc"
    # Supplemental traceability columns retained after canonical block.
    assert "JLCPCB Parts Qty" in result.fieldnames
    assert result.fieldnames.index("RowType") < result.fieldnames.index(
        "JLCPCB Parts Qty"
    )


def test_workflow_uses_mpn_lookup_when_available() -> None:
    adapter = JlcpcbExportAdapter()
    rows = [
        {
            "Category": "Capacitors",
            "MFR Part #": "CC0603KRX7R9BB104",
            "Footprint": "0603",
            "Description": "0.1uF 50V X7R 10% 0603",
            "JLCPCB Part #": "C2286",
        }
    ]
    fake_provider = MagicMock()
    fake_provider.lookup_by_mpn.return_value = _fake_search_result(
        mpn="CC0603KRX7R9BB104",
        dpn="C2286",
    )
    fake_service = SimpleNamespace(
        _provider=fake_provider,
        search=MagicMock(return_value=[]),
    )

    result = promote_rows(
        rows,
        adapter=adapter,
        supplier_context="lcsc",
        supplier_label="LCSC",
        search_service=fake_service,
    )
    assert fake_provider.lookup_by_mpn.called
    # Keyword search should not be called when MPN lookup wins.
    assert not fake_service.search.called
    canonical = result.rows[0].canonical
    assert canonical["Manufacturer"] == "YAGEO"
    assert canonical["Datasheet"] == "https://example.com/datasheet.pdf"
    assert result.stats.rows_enriched_mpn == 1


def test_workflow_falls_back_to_keyword_search() -> None:
    adapter = JlcpcbExportAdapter()
    rows = [
        {
            "Category": "Capacitors",
            "MFR Part #": "CC0603KRX7R9BB104",
            "Footprint": "0603",
            "Description": "0.1uF 50V X7R 10% 0603",
            "JLCPCB Part #": "C2286",
        }
    ]

    candidate = InventorySearchCandidate(
        result=_fake_search_result(mpn="CC0603KRX7R9BB104", dpn="C2286"),
        match_score=99,
    )
    fake_provider = MagicMock()
    fake_provider.lookup_by_mpn.return_value = None

    class _FakeService:
        _provider = fake_provider

        def __init__(self) -> None:
            self.search_calls = 0

        def search(self, items):
            self.search_calls += 1
            return [
                InventorySearchRecord(
                    inventory_item=items[0],
                    query="q",
                    candidates=[candidate],
                )
            ]

    fake_service = _FakeService()
    result = promote_rows(
        rows,
        adapter=adapter,
        supplier_context="lcsc",
        supplier_label="LCSC",
        search_service=fake_service,
    )
    assert fake_provider.lookup_by_mpn.called
    assert fake_service.search_calls == 1
    assert result.stats.rows_enriched_search == 1
    canonical = result.rows[0].canonical
    assert canonical["Manufacturer"] == "YAGEO"
    assert canonical["Datasheet"] == "https://example.com/datasheet.pdf"


def test_workflow_counts_misses_when_provider_has_nothing() -> None:
    adapter = JlcpcbExportAdapter()
    rows = [
        {
            "Category": "Capacitors",
            "MFR Part #": "",
            "Footprint": "0603",
            "Description": "0.1uF 50V X7R 10% 0603",
            "JLCPCB Part #": "C2286",
        }
    ]

    fake_provider = MagicMock()
    fake_provider.lookup_by_mpn.return_value = None
    fake_service = SimpleNamespace(
        _provider=fake_provider,
        search=MagicMock(
            return_value=[
                InventorySearchRecord(
                    inventory_item=MagicMock(),
                    query="q",
                    candidates=[],
                )
            ]
        ),
    )
    result = promote_rows(
        rows,
        adapter=adapter,
        supplier_context="lcsc",
        supplier_label="LCSC",
        search_service=fake_service,
    )
    assert result.stats.rows_enriched_mpn == 0
    assert result.stats.rows_enriched_search == 0
    assert result.stats.rows_enrichment_misses == 1
