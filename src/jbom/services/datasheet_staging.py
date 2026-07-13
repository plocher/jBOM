"""Staging fetch for datasheet documents (jBOM#355).

Implements the fetch half of the datasheet-document acquisition lifecycle
decided in jBOM#349: an always-on staging fetch that rides the already
networked ``jbom search`` / ``jbom inventory --supplier`` flows.

Staging conventions (glossary owned by SPCoast-inventory's CONTEXT.md;
imported terms: Staging, Intake, Admission, Library, Document, Datasheet
Name, Never-Rename):

* Staging is a gitignored ``staging/`` directory inside the SPCoast-inventory
  checkout. Downloads land here with a ``.unverified`` suffix until a
  ``file(1)``-style content check confirms the payload is a real PDF.
  Verified PDFs are written with a plain ``.pdf`` suffix.
* HTML impostors keep the ``.unverified`` suffix and are flagged with a
  warning; per jBOM#345 HTML is never admitted, so this module never
  promotes an unverified file automatically.
* Filenames are derived deterministically from the Datasheet URL
  (:func:`staged_filename_for_url`), so re-fetching the same URL always
  resolves to the same staged file (idempotency).
* This module never writes to the inventory. Admission into the Library's
  ``datasheets/`` directory is the separate ``jbom inventory admit`` gate
  (jBOM#356), which depends on the staging layout documented here but is
  out of scope for this module.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from jbom.common.types import InventoryItem

log = logging.getLogger(__name__)

try:
    import requests  # type: ignore
except ImportError:  # pragma: no cover - exercised only when requests is absent
    requests = None  # type: ignore

UNVERIFIED_SUFFIX = ".unverified"
VERIFIED_SUFFIX = ".pdf"

_DATASHEET_NAME_COLUMN = "Datasheet Name"
_ENV_STAGING_DIR = "JBOM_STAGING_DIR"
_ENV_INVENTORY_ROOT = "JBOM_INVENTORY_ROOT"
_DEFAULT_INVENTORY_ROOT = Path.home() / "Dropbox" / "KiCad" / "SPCoast-inventory"

# Test seam only: when set, default_fetch() reads response bytes from a local
# JSON manifest (``{url: local_file_path}``) instead of making a real network
# request. Used exclusively by BDD scenarios that exercise the CLI as a
# subprocess (features/steps/datasheet_staging_steps.py); never read by
# production code paths unless a developer explicitly sets it.
_ENV_FETCH_FIXTURES = "JBOM_DATASHEET_FETCH_FIXTURES"

_PDF_MAGIC = b"%PDF-"
_PDF_MAGIC_SEARCH_WINDOW = 1024
_HTML_MARKERS = (b"<!doctype html", b"<html", b"<head", b"<body")
_HTML_SNIFF_WINDOW = 2048


def resolve_staging_dir(explicit: Path | str | None = None) -> Path:
    """Resolve the staging directory using a documented precedence order.

    Precedence (highest first):

    1. *explicit* -- an explicit override passed by the caller.
    2. ``JBOM_STAGING_DIR`` environment variable -- a direct path to the
       staging directory itself.
    3. ``JBOM_INVENTORY_ROOT`` environment variable -- path to the
       SPCoast-inventory checkout; staging directory is ``<root>/staging``.
    4. A sensible, non-hardcoded-username default:
       ``~/Dropbox/KiCad/SPCoast-inventory/staging``.

    Args:
        explicit: Optional caller-supplied override.

    Returns:
        Resolved path to the staging directory. The directory is not
        created here; callers create it lazily on first write.
    """

    if explicit:
        return Path(explicit)

    env_staging_dir = os.environ.get(_ENV_STAGING_DIR, "").strip()
    if env_staging_dir:
        return Path(env_staging_dir)

    env_inventory_root = os.environ.get(_ENV_INVENTORY_ROOT, "").strip()
    if env_inventory_root:
        return Path(env_inventory_root) / "staging"

    return _DEFAULT_INVENTORY_ROOT / "staging"


def looks_like_pdf(content: bytes) -> bool:
    """Return True when *content* starts with a PDF signature.

    Mirrors ``file(1)``'s PDF detection: the ``%PDF-`` magic bytes must
    appear within the document header window.
    """

    return _PDF_MAGIC in content[:_PDF_MAGIC_SEARCH_WINDOW]


def looks_like_html(content: bytes) -> bool:
    """Return True when *content* looks like an HTML document."""

    head = content[:_HTML_SNIFF_WINDOW].lower()
    return any(marker in head for marker in _HTML_MARKERS)


def staged_filename_for_url(url: str) -> str:
    """Derive a stable staging filename stem (no suffix) for a Datasheet URL."""

    parsed = urlparse(url)
    basename = Path(parsed.path).name or "datasheet"
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", basename)
    stem = re.sub(r"\.(pdf|html?|php|aspx?)$", "", stem, flags=re.IGNORECASE)
    stem = stem.strip("._-") or "datasheet"
    digest = hashlib.sha256(url.strip().encode("utf-8")).hexdigest()[:10]
    return f"{stem}-{digest}"


def is_admitted(item: InventoryItem | None) -> bool:
    """Return True when *item* already has a populated ``Datasheet Name``."""

    if item is None:
        return False
    raw = item.raw_data or {}
    return bool(str(raw.get(_DATASHEET_NAME_COLUMN, "")).strip())


def find_existing_staged_path(staging_dir: Path, stem: str) -> Path | None:
    """Return the existing staged file for *stem*, verified or unverified."""

    verified_path = staging_dir / f"{stem}{VERIFIED_SUFFIX}"
    if verified_path.exists():
        return verified_path
    unverified_path = staging_dir / f"{stem}{UNVERIFIED_SUFFIX}"
    if unverified_path.exists():
        return unverified_path
    return None


@dataclass(frozen=True)
class StagingOutcome:
    """Result of one :func:`stage_datasheet_url` call.

    Attributes:
        status: One of ``"skip-empty-url"``, ``"admitted-skip"``,
            ``"staged-skip"``, ``"verified"``, ``"flagged"``, or
            ``"fetch-error"``.
        path: The staged file path, when one exists.
        message: Human-readable summary, suitable for verbose/warning output.
    """

    status: str
    path: Path | None = None
    message: str = ""


def default_fetch(url: str, *, timeout: float = 20.0) -> bytes:
    """Fetch *url* over the network and return the raw response body.

    When ``JBOM_DATASHEET_FETCH_FIXTURES`` is set (a test-only seam), reads
    response bytes from the local file mapped to *url* in that JSON manifest
    instead of making a real network request.
    """

    fixtures_path = os.environ.get(_ENV_FETCH_FIXTURES, "").strip()
    if fixtures_path:
        return _fetch_from_fixture_manifest(url, Path(fixtures_path))

    if requests is None:  # pragma: no cover - exercised only without requests
        raise RuntimeError(
            "Datasheet staging fetch requires the 'requests' package. "
            "Install it with: pip install requests"
        )
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.content


def _fetch_from_fixture_manifest(url: str, manifest_path: Path) -> bytes:
    """Resolve *url* to local fixture bytes via a ``{url: file_path}`` manifest."""

    import json

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    file_path = manifest.get(url)
    if not file_path:
        raise RuntimeError(
            f"No fixture registered for datasheet URL {url!r} in {manifest_path}"
        )
    return Path(file_path).read_bytes()


def stage_datasheet_url(
    url: str,
    *,
    item: InventoryItem | None = None,
    staging_dir: Path,
    fetch: Callable[[str], bytes] = default_fetch,
) -> StagingOutcome:
    """Idempotently stage one Datasheet URL.

    Args:
        url: The Item's Datasheet URL, as encountered by ``jbom search`` or
            ``jbom inventory --supplier``.
        item: Optional owning :class:`InventoryItem`, used only to check
            :func:`is_admitted` (already-in-Library skip).
        staging_dir: Resolved staging directory (see
            :func:`resolve_staging_dir`).
        fetch: Injectable network fetch callable, ``url -> bytes``.

    Returns:
        A :class:`StagingOutcome` describing what happened.
    """

    url = (url or "").strip()
    if not url:
        return StagingOutcome(
            status="skip-empty-url", message="No Datasheet URL to stage."
        )

    if is_admitted(item):
        return StagingOutcome(
            status="admitted-skip",
            message=f"Item already admitted (Datasheet Name present); skipping {url!r}.",
        )

    stem = staged_filename_for_url(url)
    existing = find_existing_staged_path(staging_dir, stem)
    if existing is not None:
        return StagingOutcome(
            status="staged-skip",
            path=existing,
            message=f"Already staged: {existing.name}",
        )

    try:
        content = fetch(url)
    except Exception as exc:
        return StagingOutcome(
            status="fetch-error", message=f"Failed to fetch {url!r}: {exc}"
        )

    staging_dir.mkdir(parents=True, exist_ok=True)

    if looks_like_pdf(content):
        verified_path = staging_dir / f"{stem}{VERIFIED_SUFFIX}"
        verified_path.write_bytes(content)
        return StagingOutcome(
            status="verified",
            path=verified_path,
            message=f"Staged verified PDF: {verified_path.name}",
        )

    unverified_path = staging_dir / f"{stem}{UNVERIFIED_SUFFIX}"
    unverified_path.write_bytes(content)
    reason = "HTML impostor" if looks_like_html(content) else "unrecognized content"
    warning = (
        f"Datasheet URL did not resolve to a PDF ({reason}): "
        f"{url} -> {unverified_path.name}"
    )
    log.warning(warning)
    return StagingOutcome(status="flagged", path=unverified_path, message=warning)


__all__ = [
    "UNVERIFIED_SUFFIX",
    "VERIFIED_SUFFIX",
    "StagingOutcome",
    "default_fetch",
    "find_existing_staged_path",
    "is_admitted",
    "looks_like_html",
    "looks_like_pdf",
    "resolve_staging_dir",
    "stage_datasheet_url",
    "staged_filename_for_url",
]
