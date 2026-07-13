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

Configuration is sourced entirely from jBOM's ``defaults:`` profile stanza
(see ``datasheet_staging:`` in ``docs/reference/configuration.md``) rather
than ad hoc environment variables, so staging directory / fetch-budget
overrides follow the same ``.jbom/`` profile-hierarchy precedence as every
other jBOM setting.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Optional
from urllib.parse import urlparse

from jbom.common.types import InventoryItem
from jbom.config.defaults import DefaultsConfig, get_defaults

log = logging.getLogger(__name__)

try:
    import requests  # type: ignore
except ImportError:  # pragma: no cover - exercised only when requests is absent
    requests = None  # type: ignore

UNVERIFIED_SUFFIX = ".unverified"
VERIFIED_SUFFIX = ".pdf"

_DATASHEET_NAME_COLUMN = "Datasheet Name"

_PDF_MAGIC = b"%PDF-"
_PDF_MAGIC_SEARCH_WINDOW = 1024
_HTML_MARKERS = (b"<!doctype html", b"<html", b"<head", b"<body")
_HTML_SNIFF_WINDOW = 2048


def resolve_staging_dir(
    explicit: Path | str | None = None,
    *,
    cwd: Path | None = None,
    defaults: DefaultsConfig | None = None,
) -> Path | None:
    """Resolve the staging directory via the profile system.

    Precedence (highest first):

    1. *explicit* -- an explicit override passed by the caller.
    2. ``defaults:.datasheet_staging.staging_dir`` from the active jBOM
       profile (project ``.jbom/`` overrides > ``common.jbom.yaml`` >
       ``$JBOM_PROFILE_PATH`` > ``~/.jbom/`` > built-in), the same
       resolution order used by every other jBOM configuration value.

    The staging directory is a user-machine binding (it names a checkout of
    the SPCoast-inventory repo, which lives at a different path per
    machine), so there is deliberately no code-level fallback path: when
    neither of the above is set, this returns ``None`` and staging is
    inert. A user enables it once, for every invocation, by declaring
    ``defaults.datasheet_staging.staging_dir`` in their own
    ``~/.jbom/common.jbom.yaml``.

    Args:
        explicit: Optional caller-supplied override.
        cwd: Working directory used for project-local profile search. Passed
            straight through to :func:`jbom.config.defaults.get_defaults`.
        defaults: Optional pre-loaded :class:`DefaultsConfig`, to avoid
            reloading the profile when the caller already has one.

    Returns:
        Resolved path to the staging directory, or ``None`` when staging is
        not configured. The directory is not created here; callers create
        it lazily on first write.
    """

    if explicit:
        return Path(explicit)

    cfg = defaults if defaults is not None else get_defaults(cwd=cwd)
    configured = cfg.get_datasheet_staging_config().staging_dir
    if configured:
        return Path(configured).expanduser()

    return None


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
        status: One of ``"inactive"``, ``"skip-empty-url"``,
            ``"admitted-skip"``, ``"staged-skip"``, ``"verified"``,
            ``"flagged"``, ``"fetch-error"``, or ``"budget-skip"``.
        path: The staged file path, when one exists.
        message: Human-readable summary, suitable for verbose/warning output.
    """

    status: str
    path: Path | None = None
    message: str = ""


def default_fetch(url: str, *, timeout: float = 20.0) -> bytes:
    """Fetch *url* over the network and return the raw response body."""

    if requests is None:  # pragma: no cover - exercised only without requests
        raise RuntimeError(
            "Datasheet staging fetch requires the 'requests' package. "
            "Install it with: pip install requests"
        )
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.content


def _resolve_fetch(fetch_fixtures_manifest: str) -> Callable[[str], bytes]:
    """Return the effective fetch callable for a staging batch.

    When *fetch_fixtures_manifest* is set (test-only; see
    ``DatasheetStagingConfig.fetch_fixtures_manifest``), URLs are resolved
    against that local JSON manifest instead of the network. Otherwise the
    current module-level :func:`default_fetch` is used -- looked up by name
    at call time (not bound at import time) so tests can monkeypatch
    ``jbom.services.datasheet_staging.default_fetch`` directly.
    """

    manifest = (fetch_fixtures_manifest or "").strip()
    if not manifest:
        return default_fetch

    manifest_path = Path(manifest)

    def _fixture_fetch(url: str) -> bytes:
        return _fetch_from_fixture_manifest(url, manifest_path)

    return _fixture_fetch


def _fetch_from_fixture_manifest(url: str, manifest_path: Path) -> bytes:
    """Resolve *url* to local fixture bytes via a ``{url: file_path}`` manifest."""

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
    staging_dir: Path | None,
    fetch: Optional[Callable[[str], bytes]] = None,
    fetch_fixtures_manifest: str = "",
) -> StagingOutcome:
    """Idempotently stage one Datasheet URL.

    Args:
        url: The Item's Datasheet URL, as encountered by ``jbom search`` or
            ``jbom inventory --supplier``.
        item: Optional owning :class:`InventoryItem`, used only to check
            :func:`is_admitted` (already-in-Library skip).
        staging_dir: Resolved staging directory (see
            :func:`resolve_staging_dir`), or ``None`` when staging is not
            configured -- in which case this is a silent no-op.
        fetch: Injectable network fetch callable, ``url -> bytes``. When
            omitted, resolved from *fetch_fixtures_manifest* (falling back to
            :func:`default_fetch`).
        fetch_fixtures_manifest: Test-only fixture-manifest path; ignored
            when *fetch* is provided explicitly.

    Returns:
        A :class:`StagingOutcome` describing what happened.
    """

    if staging_dir is None:
        log.debug(
            "Datasheet staging inactive (no datasheet_staging.staging_dir "
            "configured); skipping %r.",
            url,
        )
        return StagingOutcome(
            status="inactive", message="Datasheet staging is not configured."
        )

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

    resolved_fetch = (
        fetch if fetch is not None else _resolve_fetch(fetch_fixtures_manifest)
    )

    try:
        content = resolved_fetch(url)
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


@dataclass(frozen=True)
class StagingBatchResult:
    """Outcome of one :func:`stage_datasheet_urls` batch run.

    Attributes:
        outcomes: One :class:`StagingOutcome` per URL that was evaluated
            (admitted/staged skips included; budget-skipped entries are
            *not* included here, see ``skipped_for_budget``).
        attempted: Number of URLs that required an actual network fetch
            attempt (excludes free admitted/staged skips).
        budget_exceeded: True when ``max_fetches_per_run`` or
            ``fetch_time_budget_seconds`` was hit before all entries were
            processed.
        skipped_for_budget: Number of entries left unprocessed because the
            budget was exceeded.
    """

    outcomes: list[StagingOutcome] = field(default_factory=list)
    attempted: int = 0
    budget_exceeded: bool = False
    skipped_for_budget: int = 0

    def summary_message(self) -> str:
        """Return a one-line human-readable summary for CLI output."""

        if not self.budget_exceeded:
            return ""
        return (
            "Datasheet staging budget exceeded "
            f"(attempted={self.attempted}); skipped {self.skipped_for_budget} "
            "remaining URL(s) this run."
        )


def stage_datasheet_urls(
    entries: Iterable[tuple[str, Optional[InventoryItem]]],
    *,
    cwd: Path | None = None,
    defaults: DefaultsConfig | None = None,
) -> StagingBatchResult:
    """Stage a batch of ``(url, item)`` pairs, honoring the fetch budget.

    This is the shared orchestration used by both ``jbom search`` and
    ``jbom inventory --supplier``: it resolves the staging directory and
    fetch behavior once from the active profile (see
    :class:`~jbom.config.defaults.DatasheetStagingConfig`), then stages each
    entry via :func:`stage_datasheet_url`, stopping early -- without failing
    the surrounding command -- once ``max_fetches_per_run`` or
    ``fetch_time_budget_seconds`` is exceeded. Admitted/already-staged
    entries are always processed (they never touch the network), so the
    budget only governs real fetch attempts.

    Args:
        entries: Iterable of ``(datasheet_url, inventory_item_or_none)``.
        cwd: Working directory for profile resolution.
        defaults: Optional pre-loaded :class:`DefaultsConfig`.

    Returns:
        A :class:`StagingBatchResult` summarizing what happened.
    """

    cfg = defaults if defaults is not None else get_defaults(cwd=cwd)
    staging_cfg = cfg.get_datasheet_staging_config()
    staging_dir = resolve_staging_dir(defaults=cfg)
    if staging_dir is None:
        # Staging is a user-machine opt-in (datasheet_staging.staging_dir is
        # unset). Inert: no fetches, no filesystem writes, no per-URL log
        # noise -- just a single debug-level note.
        log.debug(
            "Datasheet staging inactive (no datasheet_staging.staging_dir "
            "configured); skipping this batch."
        )
        return StagingBatchResult()

    fetch = _resolve_fetch(staging_cfg.fetch_fixtures_manifest)
    max_fetches = staging_cfg.max_fetches_per_run
    time_budget = staging_cfg.fetch_time_budget_seconds

    outcomes: list[StagingOutcome] = []
    attempted = 0
    skipped_for_budget = 0
    budget_exceeded = False
    start = time.monotonic()

    for url, item in entries:
        normalized_url = (url or "").strip()
        if not normalized_url:
            continue

        if budget_exceeded:
            skipped_for_budget += 1
            continue

        stem = staged_filename_for_url(normalized_url)
        free = is_admitted(item) or (
            find_existing_staged_path(staging_dir, stem) is not None
        )
        if not free:
            over_count = attempted >= max_fetches
            over_time = (time.monotonic() - start) >= time_budget
            if over_count or over_time:
                budget_exceeded = True
                skipped_for_budget += 1
                continue
            attempted += 1

        outcomes.append(
            stage_datasheet_url(
                normalized_url, item=item, staging_dir=staging_dir, fetch=fetch
            )
        )

    return StagingBatchResult(
        outcomes=outcomes,
        attempted=attempted,
        budget_exceeded=budget_exceeded,
        skipped_for_budget=skipped_for_budget,
    )


__all__ = [
    "UNVERIFIED_SUFFIX",
    "VERIFIED_SUFFIX",
    "StagingBatchResult",
    "StagingOutcome",
    "default_fetch",
    "find_existing_staged_path",
    "is_admitted",
    "looks_like_html",
    "looks_like_pdf",
    "resolve_staging_dir",
    "stage_datasheet_url",
    "stage_datasheet_urls",
    "staged_filename_for_url",
]
