"""Unit tests for jbom.services.datasheet_url_upgrade_report (jBOM#358)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from jbom.common.types import InventoryItem
from jbom.services.datasheet_url_upgrade_report import (
    build_upgrade_report,
    render_full_sheet_paste,
    resolve_check_urls_fetch,
)

_PDF_BYTES = b"%PDF-1.4\n%fixture pdf\n%%EOF"
_HTML_BYTES = b"<!DOCTYPE html><html><head></head><body>Not Found</body></html>"


def _fetch_map(mapping: dict[str, bytes]):
    def _fetch(url: str) -> bytes:
        if url not in mapping:
            raise RuntimeError(f"no fixture for {url!r}")
        return mapping[url]

    return _fetch


def _item(
    *,
    ipn: str,
    datasheet: str,
    datasheet_name: str = "",
    row_type: str = "ITEM",
) -> InventoryItem:
    raw_data = {"Datasheet": datasheet, "Datasheet Name": datasheet_name}
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
        row_type=row_type,
        raw_data=raw_data,
    )


# ---------------------------------------------------------------------------
# build_upgrade_report
# ---------------------------------------------------------------------------


def test_build_upgrade_report_skips_items_without_url() -> None:
    items = [_item(ipn="R-1", datasheet="")]
    proposals = build_upgrade_report(items, fetch=_fetch_map({}))
    assert proposals == []


def test_build_upgrade_report_skips_component_rows() -> None:
    items = [
        _item(
            ipn="",
            datasheet="https://wmsc.lcsc.com/x.pdf",
            row_type="COMPONENT",
        )
    ]
    proposals = build_upgrade_report(items, fetch=_fetch_map({}))
    assert proposals == []


def test_build_upgrade_report_ok_item_has_no_proposed_url() -> None:
    url = "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/abc.pdf"
    items = [_item(ipn="R-1", datasheet=url)]

    proposals = build_upgrade_report(items, fetch=_fetch_map({url: _PDF_BYTES}))

    assert len(proposals) == 1
    assert proposals[0].outcome == "ok"
    assert proposals[0].proposed_url is None


def test_build_upgrade_report_recovered_item_has_proposed_url() -> None:
    viewer_url = "https://www.lcsc.com/datasheet/lcsc_datasheet_2103_WS2812B.pdf"
    cdn_url = "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2103_WS2812B.pdf"
    items = [_item(ipn="LED-1", datasheet=viewer_url)]

    proposals = build_upgrade_report(
        items,
        fetch=_fetch_map({viewer_url: _HTML_BYTES, cdn_url: _PDF_BYTES}),
    )

    assert len(proposals) == 1
    assert proposals[0].proposed_url == cdn_url


# ---------------------------------------------------------------------------
# Convergence: shared Datasheet Name, disagreeing URLs
# ---------------------------------------------------------------------------


def test_convergence_proposes_canonical_url_for_disagreeing_members() -> None:
    working_url = "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/uniroyal.pdf"
    stale_url = "https://www.lcsc.com/datasheet/lcsc_datasheet_uniroyal_old.pdf"

    items = [
        _item(
            ipn="RES-1",
            datasheet=working_url,
            datasheet_name="Uniroyal-thick-film-series",
        ),
        _item(
            ipn="RES-2",
            datasheet=stale_url,
            datasheet_name="Uniroyal-thick-film-series",
        ),
    ]

    fetch = _fetch_map({working_url: _PDF_BYTES, stale_url: _HTML_BYTES})
    proposals = build_upgrade_report(items, fetch=fetch)

    by_ipn = {p.ipn: p for p in proposals}
    # RES-1's own URL already works; it is not itself changed.
    assert by_ipn["RES-1"].proposed_url is None
    # RES-2 disagrees and is proposed the canonical (working) URL.
    assert by_ipn["RES-2"].proposed_url == working_url
    assert "Convergence" in by_ipn["RES-2"].note


def test_convergence_does_not_invent_a_canonical_when_none_resolve() -> None:
    dead_url_a = "https://www.example-mfr.com/a.pdf"
    dead_url_b = "https://www.example-mfr.com/b.pdf"

    items = [
        _item(ipn="IC-1", datasheet=dead_url_a, datasheet_name="Shared-Doc"),
        _item(ipn="IC-2", datasheet=dead_url_b, datasheet_name="Shared-Doc"),
    ]
    fetch = _fetch_map({dead_url_a: _HTML_BYTES, dead_url_b: _HTML_BYTES})

    proposals = build_upgrade_report(items, fetch=fetch)

    for proposal in proposals:
        assert proposal.proposed_url is None


def test_convergence_ignores_agreeing_members() -> None:
    url = "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/shared.pdf"
    items = [
        _item(ipn="C-1", datasheet=url, datasheet_name="Shared-Doc"),
        _item(ipn="C-2", datasheet=url, datasheet_name="Shared-Doc"),
    ]
    fetch = _fetch_map({url: _PDF_BYTES})

    proposals = build_upgrade_report(items, fetch=fetch)

    assert all(p.proposed_url is None for p in proposals)


# ---------------------------------------------------------------------------
# render_full_sheet_paste
# ---------------------------------------------------------------------------


def test_render_full_sheet_paste_preserves_row_order_and_unrelated_columns() -> None:
    url_a = "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/a.pdf"
    viewer_b = "https://www.lcsc.com/datasheet/lcsc_datasheet_b.pdf"
    cdn_b = "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/b.pdf"

    items = [
        _item(ipn="R-A", datasheet=url_a),
        _item(ipn="R-B", datasheet=viewer_b),
    ]
    fetch = _fetch_map({url_a: _PDF_BYTES, viewer_b: _HTML_BYTES, cdn_b: _PDF_BYTES})
    proposals = build_upgrade_report(items, fetch=fetch)
    fieldnames, rows = render_full_sheet_paste(
        items, proposals, ["Datasheet", "Datasheet Name"]
    )

    assert fieldnames == ["Datasheet", "Datasheet Name"]
    assert [row["Datasheet"] for row in rows] == [url_a, cdn_b]


def test_render_full_sheet_paste_leaves_urlless_rows_untouched() -> None:
    items = [_item(ipn="R-A", datasheet="")]
    proposals = build_upgrade_report(items, fetch=_fetch_map({}))
    fieldnames, rows = render_full_sheet_paste(items, proposals, ["Datasheet"])

    assert rows == [{"Datasheet": ""}]


def test_render_full_sheet_paste_never_writes_the_source_inventory(
    tmp_path: Path,
) -> None:
    """Regression guard: rendering never touches any file on disk."""

    url = "https://wmsc.lcsc.com/x.pdf"
    inventory_path = tmp_path / "inventory.csv"
    original_text = "IPN,Category,Datasheet\nR-A,RES," + url + "\n"
    inventory_path.write_text(original_text, encoding="utf-8")

    items = [_item(ipn="R-A", datasheet=url)]
    proposals = build_upgrade_report(items, fetch=_fetch_map({url: _PDF_BYTES}))
    render_full_sheet_paste(items, proposals, ["Datasheet"])

    assert inventory_path.read_text(encoding="utf-8") == original_text


# ---------------------------------------------------------------------------
# resolve_check_urls_fetch fixture-manifest injection
# ---------------------------------------------------------------------------


def test_resolve_check_urls_fetch_empty_manifest_returns_default_fetch() -> None:
    from jbom.services.datasheet_url_upgrade_report import default_fetch

    assert resolve_check_urls_fetch("") is default_fetch


def test_resolve_check_urls_fetch_reads_from_manifest(tmp_path: Path) -> None:
    fixture_file = tmp_path / "fixture.bin"
    fixture_file.write_bytes(_PDF_BYTES)

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({"https://example.com/x.pdf": str(fixture_file)}),
        encoding="utf-8",
    )

    fetch = resolve_check_urls_fetch(str(manifest_path))
    assert fetch("https://example.com/x.pdf") == _PDF_BYTES


def test_resolve_check_urls_fetch_raises_for_unregistered_url(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")

    fetch = resolve_check_urls_fetch(str(manifest_path))
    with pytest.raises(RuntimeError):
        fetch("https://example.com/unregistered.pdf")
