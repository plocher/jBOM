"""Opt-in URL recovery ladder for ``jbom audit --check-urls`` (jBOM#358).

Mechanizes the five-rung LCSC URL recovery ladder empirically discovered by
the agent-assisted curation pass (jBOM#351; findings asset:
SPCoast-inventory ``docs/curation-pass-2026-07.md``, "URL fetchability
ladder" section):

1. ``wmsc.lcsc.com`` CDN direct fetch -- the durable, byte-stable form.
   Fetched and validated as-is; ~100% direct-PDF rate in the curation data.
2. LCSC *viewer* URL (``www.lcsc.com/datasheet/lcsc_datasheet_...``) -- an
   HTML SPA shell, not fetchable by curl. Recoverable by a mechanical URL
   transform to the wmsc CDN path (~95% recovery rate).
3. Bare LCSC C-number / no direct CDN form -- recoverable via the LCSC
   product-detail API, which returns a durable
   ``datasheet.lcsc.com/datasheet/pdf/<hash>.pdf`` URL.
4. Distributor/manufacturer URLs -- mixed results (some fetch directly,
   some bot-block). The curation pass resolved bot-blocked cases through
   *human* search hunts (manufacturer catalogs, canonical mirrors,
   community mirrors) -- genuine judgment, not a mechanizable step. This
   module therefore only retries the recorded URL; it never guesses,
   searches, or invents a mirror/manufacturer URL. Failures are surfaced
   for manual/agent follow-up.
5. Signed/ephemeral URLs (e.g. JLC OSS time-limited tokens) -- dead by
   design (the signature expires) and are never fetched, stored, or
   proposed as a recovery target.

This module performs no network I/O of its own: the caller supplies a
``fetch`` callable (``url -> bytes``), exactly mirroring the injection
pattern used by :mod:`jbom.services.datasheet_staging` for the same
hermeticity reasons -- no test in this repository may touch the real
network, and ``--check-urls`` must be a strict, explicit opt-in (default
off, no fetch attempted unless the caller asks).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import urlparse

from jbom.services.datasheet_staging import looks_like_html, looks_like_pdf

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rung identifiers
# ---------------------------------------------------------------------------

RUNG_DIRECT = 1
RUNG_VIEWER_TRANSFORM = 2
RUNG_PRODUCT_DETAIL_API = 3
RUNG_MANUFACTURER_RETRY = 4
RUNG_SIGNED_EPHEMERAL = 5

# ---------------------------------------------------------------------------
# Outcome tokens
# ---------------------------------------------------------------------------

OUTCOME_OK = "ok"  # Original URL already fetches a real PDF; no upgrade needed.
OUTCOME_RECOVERED = "recovered"  # A ladder rung found a working replacement URL.
OUTCOME_DEAD = "dead"  # Signed/ephemeral; dead by design, never store.
OUTCOME_MANUAL = "manual"  # Ladder exhausted; needs human/agent judgment.

_LCSC_VIEWER_HOST = "www.lcsc.com"
_LCSC_VIEWER_PREFIX = "/datasheet/lcsc_datasheet_"
_LCSC_CDN_HOST = "wmsc.lcsc.com"
_LCSC_PRODUCT_DETAIL_API_URL = (
    "https://wmsc.lcsc.com/ftps/wm/product/detail?productCode={code}"
)
_LCSC_PRODUCT_CODE_RE = re.compile(r"\bC\d+\b")
_DURABLE_LCSC_PDF_RE = re.compile(
    r"https?://datasheet\.lcsc\.com/datasheet/pdf/[^\s\"'<>]+\.pdf",
    re.IGNORECASE,
)

# Query-string/host markers characteristic of signed, time-limited object
# storage URLs (e.g. JLCPCB's Aliyun OSS-backed asset store). Presence of
# any of these means "dead by design" -- the signature/token will expire,
# so this URL is never a valid long-term recovery target.
_SIGNED_URL_MARKERS: tuple[str, ...] = (
    "signature=",
    "ossaccesskeyid=",
    "x-amz-signature=",
    "x-amz-security-token=",
)


def is_signed_ephemeral_url(url: str) -> bool:
    """Return True when *url* looks like a signed/time-limited object URL."""

    lowered = url.lower()
    return any(marker in lowered for marker in _SIGNED_URL_MARKERS)


def is_lcsc_host(url: str) -> bool:
    """Return True when *url*'s host is any ``lcsc.com`` subdomain."""

    return urlparse(url).netloc.lower().endswith("lcsc.com")


def is_lcsc_viewer_url(url: str) -> bool:
    """Return True when *url* is an LCSC HTML viewer-page datasheet URL."""

    parsed = urlparse(url)
    return (
        parsed.netloc.lower() == _LCSC_VIEWER_HOST
        and parsed.path.lower().startswith(_LCSC_VIEWER_PREFIX)
    )


def transform_viewer_to_cdn(url: str) -> str:
    """Mechanically transform an LCSC viewer URL to its wmsc CDN form.

    ``www.lcsc.com/datasheet/lcsc_datasheet_<rest>`` ->
    ``wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/<rest>``, per the
    curation pass's rung-2 finding.
    """

    parsed = urlparse(url)
    rest = parsed.path[len(_LCSC_VIEWER_PREFIX) :]
    return f"https://{_LCSC_CDN_HOST}/wmsc/upload/file/pdf/v2/lcsc/{rest}"


def extract_lcsc_product_code(url: str) -> str | None:
    """Extract an LCSC C-number product code from *url*, if present."""

    match = _LCSC_PRODUCT_CODE_RE.search(url)
    return match.group(0) if match else None


def product_detail_api_url(product_code: str) -> str:
    """Return the LCSC product-detail API URL for *product_code*."""

    return _LCSC_PRODUCT_DETAIL_API_URL.format(code=product_code)


def extract_durable_pdf_url(response_text: str) -> str | None:
    """Extract a durable ``datasheet.lcsc.com`` PDF URL from API response text.

    Uses a text-level regex rather than a strict JSON schema so this module
    tolerates whatever the response wrapper shape happens to be, as long as
    the durable URL appears verbatim somewhere in the payload.
    """

    match = _DURABLE_LCSC_PDF_RE.search(response_text)
    return match.group(0) if match else None


@dataclass(frozen=True)
class RungAttempt:
    """One rung's attempt within a :func:`recover_datasheet_url` call.

    Attributes:
        rung: Which ladder rung this attempt represents (1-5).
        url_tried: The URL actually fetched (or would-have-been-fetched)
            for this rung.
        note: Human-readable outcome note for this attempt.
    """

    rung: int
    url_tried: str
    note: str = ""


@dataclass(frozen=True)
class UrlRecoveryResult:
    """Result of walking the recovery ladder for one Datasheet URL.

    Attributes:
        original_url: The URL as recorded in the inventory.
        outcome: One of :data:`OUTCOME_OK`, :data:`OUTCOME_RECOVERED`,
            :data:`OUTCOME_DEAD`, or :data:`OUTCOME_MANUAL`.
        proposed_url: The recovered/upgraded URL, when ``outcome`` is
            :data:`OUTCOME_RECOVERED`; ``None`` otherwise.
        rung_reached: The highest-numbered rung attempted.
        attempts: Ordered record of every rung attempt made.
        note: Human-readable summary of the outcome.
    """

    original_url: str
    outcome: str
    proposed_url: str | None
    rung_reached: int
    attempts: tuple[RungAttempt, ...] = field(default_factory=tuple)
    note: str = ""


def _classify_fetch(url: str, fetch: Callable[[str], bytes]) -> tuple[bool, str]:
    """Fetch *url* and classify the response; never raises.

    Returns:
        ``(is_pdf, note)`` -- ``is_pdf`` is True only when the content
        passes the same PDF-magic-byte check used by datasheet staging.
    """

    try:
        content = fetch(url)
    except Exception as exc:  # noqa: BLE001 - network/IO errors are data here
        return False, f"fetch error: {exc}"
    if looks_like_pdf(content):
        return True, "PDF"
    if looks_like_html(content):
        return False, "HTML impostor"
    return False, "unrecognized content"


def recover_datasheet_url(
    url: str,
    *,
    fetch: Callable[[str], bytes],
) -> UrlRecoveryResult:
    """Walk the five-rung recovery ladder for one Datasheet URL.

    Args:
        url: The Item's recorded Datasheet URL.
        fetch: Injectable fetch callable, ``url -> bytes``. Callers own
            network access entirely; this function never imports
            ``requests`` or touches the network directly. Also used to
            fetch the LCSC product-detail API URL at rung 3 (bytes are
            decoded as UTF-8 text for durable-URL extraction).

    Returns:
        A :class:`UrlRecoveryResult` describing the outcome and, when
        applicable, a proposed upgrade URL. Never invents a URL that was
        not either the original or a mechanically-derived transform/API
        result -- rung 4 failures are reported as :data:`OUTCOME_MANUAL`,
        never guessed at.
    """

    normalized = (url or "").strip()
    attempts: list[RungAttempt] = []

    if not normalized:
        return UrlRecoveryResult(
            original_url=url,
            outcome=OUTCOME_DEAD,
            proposed_url=None,
            rung_reached=0,
            attempts=(),
            note="Empty Datasheet URL",
        )

    # Rung 5 short-circuit: signed/ephemeral URLs are dead by design. Never
    # fetched, never proposed, never stored -- the curation pass found
    # these die on a schedule regardless of current reachability.
    if is_signed_ephemeral_url(normalized):
        attempts.append(
            RungAttempt(
                RUNG_SIGNED_EPHEMERAL,
                normalized,
                "signed/ephemeral URL pattern detected; dead by design",
            )
        )
        return UrlRecoveryResult(
            original_url=normalized,
            outcome=OUTCOME_DEAD,
            proposed_url=None,
            rung_reached=RUNG_SIGNED_EPHEMERAL,
            attempts=tuple(attempts),
            note="Signed/ephemeral URL; never store (dead by design)",
        )

    # Rung 1: direct fetch of the recorded URL.
    is_pdf, note = _classify_fetch(normalized, fetch)
    attempts.append(RungAttempt(RUNG_DIRECT, normalized, note))
    if is_pdf:
        return UrlRecoveryResult(
            original_url=normalized,
            outcome=OUTCOME_OK,
            proposed_url=None,
            rung_reached=RUNG_DIRECT,
            attempts=tuple(attempts),
            note="Fetched a real PDF as-is; no upgrade needed",
        )

    # Rung 2: LCSC viewer -> CDN mechanical URL transform.
    if is_lcsc_viewer_url(normalized):
        transformed = transform_viewer_to_cdn(normalized)
        is_pdf, note = _classify_fetch(transformed, fetch)
        attempts.append(RungAttempt(RUNG_VIEWER_TRANSFORM, transformed, note))
        if is_pdf:
            return UrlRecoveryResult(
                original_url=normalized,
                outcome=OUTCOME_RECOVERED,
                proposed_url=transformed,
                rung_reached=RUNG_VIEWER_TRANSFORM,
                attempts=tuple(attempts),
                note="Recovered via LCSC viewer->CDN URL transform",
            )

    # Rung 3: LCSC product-detail API lookup by C-number.
    if is_lcsc_host(normalized):
        product_code = extract_lcsc_product_code(normalized)
        if product_code:
            api_url = product_detail_api_url(product_code)
            try:
                api_response = fetch(api_url)
            except Exception as exc:  # noqa: BLE001 - recorded as a note
                attempts.append(
                    RungAttempt(
                        RUNG_PRODUCT_DETAIL_API,
                        api_url,
                        f"API fetch error: {exc}",
                    )
                )
            else:
                durable_url = extract_durable_pdf_url(
                    api_response.decode("utf-8", errors="ignore")
                )
                if durable_url:
                    is_pdf, note = _classify_fetch(durable_url, fetch)
                    attempts.append(
                        RungAttempt(RUNG_PRODUCT_DETAIL_API, durable_url, note)
                    )
                    if is_pdf:
                        return UrlRecoveryResult(
                            original_url=normalized,
                            outcome=OUTCOME_RECOVERED,
                            proposed_url=durable_url,
                            rung_reached=RUNG_PRODUCT_DETAIL_API,
                            attempts=tuple(attempts),
                            note="Recovered via LCSC product-detail API",
                        )
                else:
                    attempts.append(
                        RungAttempt(
                            RUNG_PRODUCT_DETAIL_API,
                            api_url,
                            "API response did not contain a durable PDF URL",
                        )
                    )

    # Rung 4: distributor/manufacturer URLs -- retry the recorded URL only.
    # Per the curation pass, locating a canonical mirror beyond the given
    # URL was a human/agent judgment call (manufacturer catalog hunts,
    # canonical mirrors, community attachments) and is deliberately never
    # mechanized here: no mirror-guessing, no search, no invented URLs.
    attempts.append(
        RungAttempt(
            RUNG_MANUFACTURER_RETRY,
            normalized,
            "ladder exhausted; locating a canonical mirror is a human/agent "
            "judgment call, not mechanized here",
        )
    )
    return UrlRecoveryResult(
        original_url=normalized,
        outcome=OUTCOME_MANUAL,
        proposed_url=None,
        rung_reached=RUNG_MANUFACTURER_RETRY,
        attempts=tuple(attempts),
        note="Requires manual/agent dig-deeper review",
    )


__all__ = [
    "OUTCOME_DEAD",
    "OUTCOME_MANUAL",
    "OUTCOME_OK",
    "OUTCOME_RECOVERED",
    "RUNG_DIRECT",
    "RUNG_MANUFACTURER_RETRY",
    "RUNG_PRODUCT_DETAIL_API",
    "RUNG_SIGNED_EPHEMERAL",
    "RUNG_VIEWER_TRANSFORM",
    "RungAttempt",
    "UrlRecoveryResult",
    "extract_durable_pdf_url",
    "extract_lcsc_product_code",
    "is_lcsc_host",
    "is_lcsc_viewer_url",
    "is_signed_ephemeral_url",
    "product_detail_api_url",
    "recover_datasheet_url",
    "transform_viewer_to_cdn",
]
