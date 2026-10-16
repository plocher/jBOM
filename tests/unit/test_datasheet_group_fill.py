"""Unit tests for datasheet family URL group-fill (jBOM#374)."""

from __future__ import annotations

from jbom.common.types import InventoryItem
from jbom.services.datasheet_group_fill import (
    build_datasheet_family_url_map,
    resolve_output_datasheet,
)
from jbom.services.datasheet_library import DATASHEET_NAME_COLUMN


def _make_item(
    *,
    ipn: str = "IPN1",
    datasheet: str = "",
    datasheet_name: str = "",
) -> InventoryItem:
    raw: dict[str, str] = {}
    if datasheet_name:
        raw[DATASHEET_NAME_COLUMN] = datasheet_name
    return InventoryItem(
        ipn=ipn,
        keywords="",
        category="RES",
        description="",
        smd="",
        value="10K",
        type="",
        tolerance="",
        voltage="",
        amperage="",
        wattage="",
        datasheet=datasheet,
        raw_data=raw,
    )


class TestBuildDatasheetFamilyUrlMap:
    def test_single_canonical_url_maps_case_insensitively(self) -> None:
        items = [
            _make_item(
                ipn="A",
                datasheet="https://example.com/rc0805.pdf",
                datasheet_name="Yageo-RC0805",
            ),
            _make_item(ipn="B", datasheet="", datasheet_name="yageo-rc0805"),
            _make_item(ipn="C", datasheet="", datasheet_name="YAGEO-RC0805"),
        ]

        family_map = build_datasheet_family_url_map(items)

        assert family_map == {"yageo-rc0805": "https://example.com/rc0805.pdf"}

    def test_conflicting_urls_omit_family(self) -> None:
        items = [
            _make_item(
                ipn="A",
                datasheet="https://example.com/a.pdf",
                datasheet_name="Family-X",
            ),
            _make_item(
                ipn="B",
                datasheet="https://example.com/b.pdf",
                datasheet_name="family-x",
            ),
        ]

        assert build_datasheet_family_url_map(items) == {}

    def test_zero_urls_omit_family(self) -> None:
        items = [
            _make_item(ipn="A", datasheet="", datasheet_name="Family-Y"),
            _make_item(ipn="B", datasheet="", datasheet_name="Family-Y"),
        ]

        assert build_datasheet_family_url_map(items) == {}

    def test_identical_urls_on_multiple_rows_still_map(self) -> None:
        url = "https://example.com/same.pdf"
        items = [
            _make_item(ipn="A", datasheet=url, datasheet_name="Family-Z"),
            _make_item(ipn="B", datasheet=url, datasheet_name="Family-Z"),
        ]

        assert build_datasheet_family_url_map(items) == {"family-z": url}

    def test_rows_without_name_are_ignored(self) -> None:
        items = [
            _make_item(ipn="A", datasheet="https://example.com/orphan.pdf"),
            _make_item(
                ipn="B",
                datasheet="https://example.com/family.pdf",
                datasheet_name="Named",
            ),
        ]

        assert build_datasheet_family_url_map(items) == {
            "named": "https://example.com/family.pdf"
        }


class TestResolveOutputDatasheet:
    def test_populated_cell_is_verbatim(self) -> None:
        item = _make_item(
            datasheet="https://example.com/own.pdf",
            datasheet_name="Family",
        )
        family_map = {"family": "https://example.com/canonical.pdf"}

        assert resolve_output_datasheet(item, family_map) == (
            "https://example.com/own.pdf"
        )

    def test_blank_cell_fills_from_family_map(self) -> None:
        item = _make_item(datasheet="", datasheet_name="Family")
        family_map = {"family": "https://example.com/canonical.pdf"}

        assert resolve_output_datasheet(item, family_map) == (
            "https://example.com/canonical.pdf"
        )

    def test_blank_with_no_name_stays_blank(self) -> None:
        item = _make_item(datasheet="", datasheet_name="")
        family_map = {"family": "https://example.com/canonical.pdf"}

        assert resolve_output_datasheet(item, family_map) == ""

    def test_blank_with_name_but_no_family_url_stays_blank(self) -> None:
        item = _make_item(datasheet="", datasheet_name="Missing-Family")

        assert resolve_output_datasheet(item, {}) == ""

    def test_case_insensitive_name_lookup(self) -> None:
        item = _make_item(datasheet="", datasheet_name="Yageo-RC0805")
        family_map = {"yageo-rc0805": "https://example.com/rc0805.pdf"}

        assert resolve_output_datasheet(item, family_map) == (
            "https://example.com/rc0805.pdf"
        )
