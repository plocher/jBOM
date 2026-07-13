"""Unit tests for jbom.services.datasheet_url_recovery (jBOM#358).

All network access is faked via an injected ``fetch`` callable -- no test
in this module touches the network.
"""

from __future__ import annotations

import pytest

from jbom.services.datasheet_url_recovery import (
    OUTCOME_DEAD,
    OUTCOME_MANUAL,
    OUTCOME_OK,
    OUTCOME_RECOVERED,
    RUNG_DIRECT,
    RUNG_MANUFACTURER_RETRY,
    RUNG_PRODUCT_DETAIL_API,
    RUNG_SIGNED_EPHEMERAL,
    RUNG_VIEWER_TRANSFORM,
    extract_durable_pdf_url,
    extract_lcsc_product_code,
    is_lcsc_host,
    is_lcsc_viewer_url,
    is_signed_ephemeral_url,
    product_detail_api_url,
    recover_datasheet_url,
    transform_viewer_to_cdn,
)

_PDF_BYTES = b"%PDF-1.4\n%fixture pdf\n%%EOF"
_HTML_BYTES = b"<!DOCTYPE html><html><head></head><body>Not Found</body></html>"


def _fetch_map(mapping: dict[str, bytes]):
    """Return a fetch callable that resolves URLs from *mapping*, else errors."""

    def _fetch(url: str) -> bytes:
        if url not in mapping:
            raise RuntimeError(f"no fixture for {url!r}")
        return mapping[url]

    return _fetch


# ---------------------------------------------------------------------------
# Rung 1: direct fetch
# ---------------------------------------------------------------------------


def test_rung1_direct_pdf_is_ok() -> None:
    url = "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/abc123.pdf"
    result = recover_datasheet_url(url, fetch=_fetch_map({url: _PDF_BYTES}))

    assert result.outcome == OUTCOME_OK
    assert result.proposed_url is None
    assert result.rung_reached == RUNG_DIRECT
    assert result.attempts[0].rung == RUNG_DIRECT


def test_empty_url_is_dead() -> None:
    result = recover_datasheet_url("", fetch=_fetch_map({}))

    assert result.outcome == OUTCOME_DEAD
    assert result.rung_reached == 0


# ---------------------------------------------------------------------------
# Rung 2: LCSC viewer -> CDN transform
# ---------------------------------------------------------------------------


def test_rung2_viewer_url_recovered_via_transform() -> None:
    viewer_url = "https://www.lcsc.com/datasheet/lcsc_datasheet_2103141930_WS2812B.pdf"
    cdn_url = transform_viewer_to_cdn(viewer_url)

    fetch = _fetch_map({viewer_url: _HTML_BYTES, cdn_url: _PDF_BYTES})
    result = recover_datasheet_url(viewer_url, fetch=fetch)

    assert result.outcome == OUTCOME_RECOVERED
    assert result.proposed_url == cdn_url
    assert result.rung_reached == RUNG_VIEWER_TRANSFORM


def test_rung2_viewer_url_transform_still_html_falls_through() -> None:
    """Bare C-number viewer URLs are documented as NOT recoverable by transform."""

    viewer_url = "https://www.lcsc.com/datasheet/lcsc_datasheet_C123456.pdf"
    cdn_url = transform_viewer_to_cdn(viewer_url)

    fetch = _fetch_map({viewer_url: _HTML_BYTES, cdn_url: _HTML_BYTES})
    result = recover_datasheet_url(viewer_url, fetch=fetch)

    # Falls through to rung 3 (LCSC host, C-number extractable) and then
    # rung 4 if that also fails; assert it does NOT falsely report OK/RECOVERED.
    assert result.outcome in {OUTCOME_MANUAL, OUTCOME_RECOVERED}
    if result.outcome == OUTCOME_RECOVERED:
        assert result.proposed_url != cdn_url


def test_is_lcsc_viewer_url_detection() -> None:
    assert is_lcsc_viewer_url(
        "https://www.lcsc.com/datasheet/lcsc_datasheet_2103141930_WS2812B.pdf"
    )
    assert not is_lcsc_viewer_url("https://www.lcsc.com/product-detail/C123456.html")
    assert not is_lcsc_viewer_url("https://wmsc.lcsc.com/wmsc/upload/file/x.pdf")


# ---------------------------------------------------------------------------
# Rung 3: LCSC product-detail API
# ---------------------------------------------------------------------------


def test_rung3_bare_c_number_recovered_via_product_detail_api() -> None:
    original_url = "https://www.lcsc.com/datasheet/C7442870.pdf"
    api_url = product_detail_api_url("C7442870")
    durable_url = "https://datasheet.lcsc.com/datasheet/pdf/abc123hash.pdf"
    api_response = f'{{"result":{{"pdfUrl":"{durable_url}"}}}}'.encode("utf-8")

    fetch = _fetch_map(
        {
            original_url: _HTML_BYTES,
            api_url: api_response,
            durable_url: _PDF_BYTES,
        }
    )
    result = recover_datasheet_url(original_url, fetch=fetch)

    assert result.outcome == OUTCOME_RECOVERED
    assert result.proposed_url == durable_url
    assert result.rung_reached == RUNG_PRODUCT_DETAIL_API


def test_extract_lcsc_product_code() -> None:
    assert extract_lcsc_product_code("https://www.lcsc.com/datasheet/C7442870.pdf") == (
        "C7442870"
    )
    assert extract_lcsc_product_code("https://example.com/no-code-here.pdf") is None


def test_extract_durable_pdf_url_from_response_text() -> None:
    text = '{"data":{"pdfUrl":"https://datasheet.lcsc.com/datasheet/pdf/xyz.pdf"}}'
    assert (
        extract_durable_pdf_url(text)
        == "https://datasheet.lcsc.com/datasheet/pdf/xyz.pdf"
    )
    assert extract_durable_pdf_url('{"data": {}}') is None


def test_rung3_no_durable_url_in_api_response_falls_to_manual() -> None:
    original_url = "https://www.lcsc.com/datasheet/C9999999.pdf"
    api_url = product_detail_api_url("C9999999")

    fetch = _fetch_map(
        {
            original_url: _HTML_BYTES,
            api_url: b'{"result": {}}',
        }
    )
    result = recover_datasheet_url(original_url, fetch=fetch)

    assert result.outcome == OUTCOME_MANUAL
    assert result.rung_reached == RUNG_MANUFACTURER_RETRY


# ---------------------------------------------------------------------------
# Rung 4: distributor/manufacturer retry-only, no mirror guessing
# ---------------------------------------------------------------------------


def test_rung4_manufacturer_url_failure_is_manual_not_guessed() -> None:
    url = "https://www.nxp.com/docs/en/data-sheet/PCA9685.pdf"
    fetch_calls: list[str] = []

    def _fetch(u: str) -> bytes:
        fetch_calls.append(u)
        if u != url:
            raise RuntimeError(f"no fixture for {u!r}")
        return _HTML_BYTES

    result = recover_datasheet_url(url, fetch=_fetch)

    assert result.outcome == OUTCOME_MANUAL
    assert result.proposed_url is None
    assert result.rung_reached == RUNG_MANUFACTURER_RETRY
    # Every attempt url_tried is the original URL -- no invented mirror URL --
    # and the network is only actually fetched once (rung 4 reuses rung 1's
    # result rather than re-fetching).
    assert {attempt.url_tried for attempt in result.attempts} == {url}
    assert fetch_calls == [url]


def test_rung4_manufacturer_url_success_is_ok() -> None:
    url = "https://www.nichicon.co.jp/english/products/pdfs/e-uvr.pdf"
    fetch = _fetch_map({url: _PDF_BYTES})

    result = recover_datasheet_url(url, fetch=fetch)

    assert result.outcome == OUTCOME_OK
    assert result.rung_reached == RUNG_DIRECT


def test_rung4_never_invents_a_mirror_url() -> None:
    """Regression guard: no rung ever fabricates a URL beyond documented transforms."""

    url = "https://www.mouser.com/datasheet/2/149/LM358-1849205.pdf"
    fetch = _fetch_map({url: _HTML_BYTES})

    result = recover_datasheet_url(url, fetch=fetch)

    tried_urls = {attempt.url_tried for attempt in result.attempts}
    assert tried_urls == {url}


# ---------------------------------------------------------------------------
# Rung 5: signed/ephemeral URLs are dead by design
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://jlc-oss.oss-cn-shenzhen.aliyuncs.com/file.pdf?OSSAccessKeyId=abc&Signature=xyz&Expires=123",
        "https://example-bucket.s3.amazonaws.com/file.pdf?X-Amz-Signature=abc123",
    ],
)
def test_rung5_signed_url_is_dead_never_fetched(url: str) -> None:
    def _explode(_url: str) -> bytes:
        raise AssertionError("signed/ephemeral URLs must never be fetched")

    result = recover_datasheet_url(url, fetch=_explode)

    assert result.outcome == OUTCOME_DEAD
    assert result.proposed_url is None
    assert result.rung_reached == RUNG_SIGNED_EPHEMERAL
    assert len(result.attempts) == 1


def test_is_signed_ephemeral_url_detection() -> None:
    assert is_signed_ephemeral_url("https://x.example.com/f.pdf?Signature=abc")
    assert not is_signed_ephemeral_url("https://wmsc.lcsc.com/wmsc/upload/x.pdf")


def test_is_lcsc_host() -> None:
    assert is_lcsc_host("https://wmsc.lcsc.com/wmsc/upload/file/x.pdf")
    assert is_lcsc_host("https://www.lcsc.com/datasheet/C1.pdf")
    assert not is_lcsc_host("https://www.nxp.com/docs/x.pdf")
