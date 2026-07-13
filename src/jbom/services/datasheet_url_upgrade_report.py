"""URL upgrade proposals and full-sheet-paste rendering (jBOM#358).

Orchestrates :func:`jbom.services.datasheet_url_recovery.recover_datasheet_url`
across an inventory's Items to build a per-Item upgrade proposal, folds in
convergence support (jBOM#351's one-URL-per-Name provenance rule: when
Items sharing a ``Datasheet Name`` disagree on ``Datasheet`` URL, propose
the canonical one), and renders the result as a full-sheet-paste CSV -- the
shape the curation pass found actually worked for human application (all
rows, in original sheet order, only the ``Datasheet`` cell rewritten where
an upgrade is proposed).

This module never writes to an inventory file. It only produces data for a
human (or a downstream tool acting on human instruction) to paste back.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from jbom.common.types import InventoryItem
from jbom.services.datasheet_url_recovery import (
    OUTCOME_OK,
    OUTCOME_RECOVERED,
    UrlRecoveryResult,
    recover_datasheet_url,
)

try:
    import requests  # type: ignore
except ImportError:  # pragma: no cover - exercised only when requests is absent
    requests = None  # type: ignore

_ROW_TYPE_ITEM = "ITEM"
_DEFAULT_URL_COLUMN = "Datasheet"
_DEFAULT_NAME_COLUMN = "Datasheet Name"


@dataclass(frozen=True)
class UrlUpgradeProposal:
    """One Item's URL-check outcome and (optional) upgrade proposal.

    Attributes:
        ipn: The Item's IPN, used to key back into the original CSV row.
        datasheet_name: The Item's recorded ``Datasheet Name``, or ``""``.
        original_url: The URL as recorded in the inventory.
        proposed_url: The upgraded URL to propose, or ``None`` when the
            original URL is fine as-is or no mechanical recovery/consensus
            was found.
        outcome: The underlying :mod:`datasheet_url_recovery` outcome
            token for this Item's own URL (before convergence overrides).
        rung_reached: The ladder rung reached for this Item's own URL.
        note: Human-readable summary, including convergence notes.
    """

    ipn: str
    datasheet_name: str
    original_url: str
    proposed_url: str | None
    outcome: str
    rung_reached: int
    note: str = ""


def default_fetch(url: str, *, timeout: float = 20.0) -> bytes:
    """Fetch *url* over the network and return the raw response body.

    Only reachable when ``--check-urls`` is explicitly given on the CLI;
    never called by any test in this repository (see
    :func:`resolve_check_urls_fetch`).
    """

    if requests is None:  # pragma: no cover - exercised only without requests
        raise RuntimeError(
            "jbom audit --check-urls requires the 'requests' package. "
            "Install it with: pip install requests"
        )
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.content


def resolve_check_urls_fetch(fetch_fixtures_manifest: str) -> Callable[[str], bytes]:
    """Return the effective fetch callable for a ``--check-urls`` run.

    When *fetch_fixtures_manifest* is set (test-only; see
    ``defaults.check_urls.fetch_fixtures_manifest`` in the active jBOM
    profile), URLs are resolved against that local JSON manifest instead
    of the network -- mirroring
    :func:`jbom.services.datasheet_staging._resolve_fetch`. Otherwise the
    current module-level :func:`default_fetch` is used, looked up by name
    at call time so tests can monkeypatch
    ``jbom.services.datasheet_url_upgrade_report.default_fetch`` directly.
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
        raise RuntimeError(f"No fixture registered for URL {url!r} in {manifest_path}")
    return Path(file_path).read_bytes()


def _item_datasheet_name(item: InventoryItem, *, name_column: str) -> str:
    return str((item.raw_data or {}).get(name_column, "") or "").strip()


def build_upgrade_report(
    items: Sequence[InventoryItem],
    *,
    fetch: Callable[[str], bytes],
    url_column: str = _DEFAULT_URL_COLUMN,
    name_column: str = _DEFAULT_NAME_COLUMN,
) -> list[UrlUpgradeProposal]:
    """Run the recovery ladder over every populated Item Datasheet URL.

    Also applies convergence: when Items sharing a ``Datasheet Name``
    disagree on ``Datasheet`` URL, the canonical URL is proposed for every
    disagreeing member -- preferring a member whose own URL already works
    as-is (:data:`~jbom.services.datasheet_url_recovery.OUTCOME_OK`), else
    a member with a mechanically-recovered upgrade. A canonical URL is
    never invented: if no member's URL resolves cleanly, disagreeing rows
    are left as individual per-URL outcomes for human/agent review.

    Args:
        items: Inventory items (both ITEM and COMPONENT rows may be
            present; only ITEM rows carry Datasheet URLs and are checked).
        fetch: Injectable fetch callable, ``url -> bytes``.
        url_column: Raw CSV column name holding the Datasheet URL.
        name_column: Raw CSV column name holding the Datasheet Name.

    Returns:
        One :class:`UrlUpgradeProposal` per Item with a non-empty
        Datasheet URL, in the same order as *items*.
    """

    results_by_index: dict[int, UrlRecoveryResult] = {}
    for idx, item in enumerate(items):
        if item.row_type != _ROW_TYPE_ITEM:
            continue
        url = (item.datasheet or "").strip()
        if not url:
            continue
        results_by_index[idx] = recover_datasheet_url(url, fetch=fetch)

    groups_by_name: dict[str, list[int]] = defaultdict(list)
    for idx, item in enumerate(items):
        if idx not in results_by_index:
            continue
        name = _item_datasheet_name(item, name_column=name_column)
        if name:
            groups_by_name[name.lower()].append(idx)

    canonical_url_by_name: dict[str, str] = {}
    for name_key, indices in groups_by_name.items():
        urls = {items[i].datasheet.strip() for i in indices}
        if len(urls) <= 1:
            continue  # No disagreement; nothing to converge.

        canonical: str | None = None
        for i in indices:
            if results_by_index[i].outcome == OUTCOME_OK:
                canonical = items[i].datasheet.strip()
                break
        if canonical is None:
            for i in indices:
                result = results_by_index[i]
                if result.outcome == OUTCOME_RECOVERED and result.proposed_url:
                    canonical = result.proposed_url
                    break
        if canonical is not None:
            canonical_url_by_name[name_key] = canonical

    proposals: list[UrlUpgradeProposal] = []
    for idx, item in enumerate(items):
        result = results_by_index.get(idx)
        if result is None:
            continue

        name = _item_datasheet_name(item, name_column=name_column)
        proposed_url = result.proposed_url
        note = result.note

        canonical = canonical_url_by_name.get(name.lower()) if name else None
        if canonical is not None and canonical != item.datasheet.strip():
            proposed_url = canonical
            note = (
                f"Convergence: Items sharing Datasheet Name {name!r} disagree "
                f"on URL; canonical is {canonical}"
            )

        proposals.append(
            UrlUpgradeProposal(
                ipn=item.ipn,
                datasheet_name=name,
                original_url=item.datasheet.strip(),
                proposed_url=proposed_url,
                outcome=result.outcome,
                rung_reached=result.rung_reached,
                note=note,
            )
        )

    return proposals


def render_full_sheet_paste(
    items: Sequence[InventoryItem],
    proposals: Sequence[UrlUpgradeProposal],
    fieldnames: Sequence[str],
    *,
    url_column: str = _DEFAULT_URL_COLUMN,
) -> tuple[list[str], list[dict[str, str]]]:
    """Render all inventory rows, in original order, with URL upgrades pasted in.

    Only the *proposed* upgrades from *proposals* are applied, and only to
    the ``url_column`` cell; every other row and column passes through
    unchanged. This matches the curation pass's "what worked" finding: a
    full-sheet paste CSV (all rows in sheet order), not a sparse row list --
    so a human can paste the whole thing back over the spreadsheet range.

    Args:
        items: Inventory items in original sheet order.
        proposals: Upgrade proposals, as returned by
            :func:`build_upgrade_report`.
        fieldnames: Ordered CSV column names (as returned by
            :meth:`jbom.services.inventory_reader.InventoryReader.load`).
        url_column: Raw CSV column name holding the Datasheet URL.

    Returns:
        ``(fieldnames, rows)`` ready for CSV writing.
    """

    proposal_by_ipn: dict[str, UrlUpgradeProposal] = {
        proposal.ipn: proposal for proposal in proposals if proposal.ipn
    }

    rows: list[dict[str, str]] = []
    for item in items:
        row = {name: str(item.raw_data.get(name, "") or "") for name in fieldnames}
        proposal = proposal_by_ipn.get(item.ipn)
        if (
            proposal is not None
            and proposal.proposed_url
            and proposal.proposed_url != proposal.original_url
        ):
            row[url_column] = proposal.proposed_url
        rows.append(row)

    return list(fieldnames), rows


__all__ = [
    "UrlUpgradeProposal",
    "build_upgrade_report",
    "default_fetch",
    "render_full_sheet_paste",
    "resolve_check_urls_fetch",
]
