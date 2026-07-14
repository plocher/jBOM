"""Admission gate for the datasheet document library (jBOM#356).

Implements the second half of the datasheet-document acquisition lifecycle
decided in jBOM#349 (the first half -- always-on staging fetch -- lives in
:mod:`jbom.services.datasheet_staging`, jBOM#355). ``jbom inventory admit``
is the *sole* gate into the library:

* **Propose** (:func:`propose_admit_manifest`) scans the configured staging
  directory for verified PDFs, matches each one back to the inventory
  "backlog" (rows with a populated ``Datasheet`` URL but no ``Datasheet
  Name`` yet -- see jBOM#348), and proposes a curated document name. Rows
  sharing one URL (family members) are grouped into a single manifest row.
* A human edits the resulting manifest CSV -- names, family grouping,
  and per-row ``Action`` (``ADMIT`` to accept, ``SKIP`` to leave staged).
* **Apply** (:func:`apply_admit_manifest`) moves accepted PDFs into
  ``datasheets/<name>.pdf`` and emits a full-sheet paste-file proposal for
  the ``Datasheet Name`` column (per jBOM#356's acceptance text). Per the
  jBOM#347/#348 human-sole-writer ruling, this module never writes to the
  inventory itself -- only to the staging/library directories and to the
  paste-file it hands back to the human.

Never-rename protection (jBOM#346/#347): a proposed name that collides
(case-insensitively, since macOS/Dropbox filesystems are case-insensitive)
with an *already-published* library document of different content is
refused outright -- admit never silently renames or overwrites a published
document. Re-admitting byte-identical content under its own published name
is treated as an idempotent no-op, not a violation.

Name proposal is a best-effort heuristic derived from inventory columns
only (``Category``, ``Manufacturer``, ``MFGPN``) -- it does not read PDF
content (technology/function tokens like "ThickFilm" or "Schottky" require
opening the datasheet, which is out of scope for automated tooling; see the
``bom-datasheets`` skill for the full POC convention). The human is always
expected to review and correct the proposed name in the manifest before
``--apply``.
"""

from __future__ import annotations

import csv
import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, TextIO

from jbom.common.types import InventoryItem
from jbom.services.datasheet_staging import (
    VERIFIED_SUFFIX,
    is_admitted,
    staged_filename_for_url,
)

_DATASHEET_URL_COLUMN = "Datasheet"
_DATASHEET_NAME_COLUMN = "Datasheet Name"

# Manifest CSV schema (human-editable; round-tripped by propose -> apply).
MANIFEST_COLUMNS: tuple[str, ...] = (
    "Action",
    "ProposedName",
    "Disposition",
    "DupeOf",
    "StagedFile",
    "SourceURL",
    "MemberIPNs",
)

ACTION_ADMIT = "ADMIT"
ACTION_SKIP = "SKIP"

DISPOSITION_NEW = "new"
DISPOSITION_DUPE_OF = "dupe-of"
DISPOSITION_COLLISION = "collision"
DISPOSITION_UNRESOLVABLE = "unresolvable"

_MEMBER_IPN_SEPARATOR = ";"
_CLASS_TOKEN_BY_CATEGORY: dict[str, str] = {
    "RES": "Resistor",
    "CAP": "Capacitor",
    "IND": "Inductor",
    "IC": "IC",
    "LED": "LED",
    "DIODE": "Diode",
    "MOSFET": "MOSFET",
    "TRANSISTOR": "Transistor",
    "CONNECTOR": "Connector",
    "CRYSTAL": "Crystal",
    "SWITCH": "Switch",
    "FUSE": "Fuse",
}


@dataclass(frozen=True)
class AdmitManifestRow:
    """One row of the human-editable admit manifest.

    Attributes:
        action: ``"ADMIT"`` to accept this row at apply time, ``"SKIP"`` to
            leave it staged (default for anything that needs human
            attention: collisions and unresolvable candidates).
        proposed_name: Curated ``Datasheet Name`` (no path, no extension).
            Human-editable; the value used verbatim as the library filename
            stem at apply time.
        disposition: One of ``"new"``, ``"dupe-of"``, ``"collision"``, or
            ``"unresolvable"`` -- see module docstring.
        dupe_of: When ``disposition == "dupe-of"``, the existing published
            name this staged file is byte-identical to.
        staged_file: Filename (not full path) of the verified PDF within
            the staging directory.
        source_url: The Datasheet URL this staged file was fetched from.
        member_ipns: IPNs of inventory Items sharing *source_url* that lack
            a ``Datasheet Name`` -- the "target Item rows" this admission
            will name. Family docs (jBOM#346) have more than one.
    """

    action: str
    proposed_name: str
    disposition: str
    dupe_of: str
    staged_file: str
    source_url: str
    member_ipns: tuple[str, ...] = field(default_factory=tuple)

    def to_csv_row(self) -> dict[str, str]:
        """Render this row as a CSV dict matching :data:`MANIFEST_COLUMNS`."""

        return {
            "Action": self.action,
            "ProposedName": self.proposed_name,
            "Disposition": self.disposition,
            "DupeOf": self.dupe_of,
            "StagedFile": self.staged_file,
            "SourceURL": self.source_url,
            "MemberIPNs": _MEMBER_IPN_SEPARATOR.join(self.member_ipns),
        }

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> "AdmitManifestRow":
        """Parse one CSV dict (as read back from an edited manifest) into a row."""

        member_ipns_raw = str(row.get("MemberIPNs", "") or "").strip()
        member_ipns = (
            tuple(
                token.strip()
                for token in member_ipns_raw.split(_MEMBER_IPN_SEPARATOR)
                if token.strip()
            )
            if member_ipns_raw
            else tuple()
        )
        return cls(
            action=str(row.get("Action", "") or "").strip().upper(),
            proposed_name=str(row.get("ProposedName", "") or "").strip(),
            disposition=str(row.get("Disposition", "") or "").strip(),
            dupe_of=str(row.get("DupeOf", "") or "").strip(),
            staged_file=str(row.get("StagedFile", "") or "").strip(),
            source_url=str(row.get("SourceURL", "") or "").strip(),
            member_ipns=member_ipns,
        )


@dataclass(frozen=True)
class AdmitApplyOutcome:
    """Per-row result of one :func:`apply_admit_manifest` row.

    Attributes:
        row: The manifest row this outcome corresponds to.
        status: ``"admitted"``, ``"skipped"``, ``"already-admitted"``
            (idempotent no-op; byte-identical content already at the
            target name), ``"refused-never-rename"``, or
            ``"refused-invalid-name"`` (unsafe ``ProposedName``, e.g. a path
            traversal attempt).
        message: Human-readable detail, suitable for CLI warning output.
    """

    row: AdmitManifestRow
    status: str
    message: str = ""


@dataclass(frozen=True)
class AdmitApplyResult:
    """Aggregate outcome of one :func:`apply_admit_manifest` run.

    Attributes:
        outcomes: One :class:`AdmitApplyOutcome` per processed manifest row.
        paste_rows: Ordered ``(ipn, proposed_name)`` pairs for the full-sheet
            ``Datasheet Name`` paste-file -- one pair per admitted member
            Item (family docs contribute one pair per member).
    """

    outcomes: list[AdmitApplyOutcome] = field(default_factory=list)
    paste_rows: list[tuple[str, str]] = field(default_factory=list)

    @property
    def admitted_count(self) -> int:
        """Number of rows successfully admitted (including idempotent no-ops)."""

        return sum(
            1
            for outcome in self.outcomes
            if outcome.status in ("admitted", "already-admitted")
        )

    @property
    def refused_count(self) -> int:
        """Number of rows refused (never-rename guard or invalid-name guard)."""

        return sum(
            1 for outcome in self.outcomes if outcome.status.startswith("refused-")
        )


def _normalize_name(name: str) -> str:
    """NFC-normalize and strip a proposed/published name for safe comparison.

    The manifest is human-edited free text; normalizing to NFC before any
    comparison or filesystem use prevents unicode-variant spellings (NFC vs
    NFD encodings of the same visible characters) from slipping past the
    case-insensitive uniqueness invariant (jBOM#346).
    """

    return unicodedata.normalize("NFC", str(name or "").strip())


def invalid_proposed_name_reason(
    proposed_name: str, *, library_dir: Path
) -> str | None:
    """Return a reason string when *proposed_name* is unsafe to use as a
    library filename stem, or ``None`` when it is safe.

    The admit manifest is human-edited free text, so a crafted
    ``ProposedName`` (e.g. ``"../../evil"`` or an absolute path) must never
    be trusted as a bare filename stem -- doing so would let a manifest
    write outside the library directory. Rejects path separators, ``.``/
    ``..`` components, and absolute paths outright, then (belt-and-braces)
    verifies the fully resolved target still lands directly inside
    *library_dir*.
    """

    name = _normalize_name(proposed_name)
    if not name:
        return "ProposedName is empty"
    if "/" in name or "\\" in name or "\x00" in name:
        return f"ProposedName contains a path separator: {proposed_name!r}"
    if name in (".", ".."):
        return f"ProposedName is a path traversal component: {proposed_name!r}"
    if Path(name).is_absolute():
        return f"ProposedName is an absolute path: {proposed_name!r}"

    resolved_library_dir = library_dir.resolve()
    resolved_target = (library_dir / f"{name}.pdf").resolve()
    if resolved_target.parent != resolved_library_dir:
        return f"ProposedName escapes the library directory: {proposed_name!r}"
    return None


def _sanitize_name_token(value: str) -> str:
    """Sanitize one name-component token to filesystem/manifest-safe text."""

    token = re.sub(r"[^A-Za-z0-9]+", "-", str(value or "").strip())
    return token.strip("-")


def _class_token_for_category(category: str) -> str:
    """Return a human-legible class token for a jBOM inventory category."""

    normalized = str(category or "").strip().upper()
    return _CLASS_TOKEN_BY_CATEGORY.get(normalized, normalized.title() or "Part")


def _common_alnum_prefix(values: Iterable[str]) -> str:
    """Return the longest common leading substring shared by all *values*."""

    items = [str(v or "").strip() for v in values if str(v or "").strip()]
    if not items:
        return ""
    prefix = items[0]
    for item in items[1:]:
        limit = min(len(prefix), len(item))
        i = 0
        while i < limit and prefix[i] == item[i]:
            i += 1
        prefix = prefix[:i]
        if not prefix:
            return ""
    return prefix


def propose_document_name(
    *,
    category: str,
    manufacturer: str,
    mfgpn_candidates: Iterable[str],
) -> str:
    """Propose a best-effort curated ``Datasheet Name`` for one candidate.

    Follows the bom-datasheets POC convention's token order
    (``<Class>-<Manufacturer>-<MPN>``) without the technology/function
    tokens that require reading the datasheet itself. When more than one
    MFGPN is supplied (a family candidate), a shared prefix of at least 3
    characters is truncated and suffixed with ``-series`` (jBOM#346); when no
    shared prefix exists, the first MFGPN is used verbatim -- the human is
    expected to correct this in the manifest.

    Args:
        category: Inventory ``Category`` value (e.g. ``"RES"``).
        manufacturer: Inventory ``Manufacturer`` value.
        mfgpn_candidates: MFGPN values of every member Item sharing this
            candidate's source URL.

    Returns:
        A proposed name, e.g. ``"Resistor-Uniroyal-0603WAJ-series"``.
    """

    class_token = _class_token_for_category(category)
    manufacturer_token = _sanitize_name_token(manufacturer) or "Unknown"

    candidates = [
        str(v or "").strip() for v in mfgpn_candidates if str(v or "").strip()
    ]
    if not candidates:
        mpn_token = "unknown"
    elif len(candidates) == 1:
        mpn_token = _sanitize_name_token(candidates[0]) or "unknown"
    else:
        common_prefix = _common_alnum_prefix(candidates).rstrip("-_")
        if len(common_prefix) >= 3:
            mpn_token = f"{_sanitize_name_token(common_prefix)}-series"
        else:
            mpn_token = _sanitize_name_token(candidates[0]) or "unknown"

    return f"{class_token}-{manufacturer_token}-{mpn_token}"


def _sha256_of_file(path: Path) -> str:
    """Return the sha256 hex digest of a file's contents."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _library_name_index(library_dir: Path) -> dict[str, Path]:
    """Return a case-insensitive index of published names -> file paths.

    Keys are NFC-normalized and lower-cased, so lookups are both
    unicode-normalization-insensitive and OS-independent case-insensitive
    (never relying on the host filesystem's own case sensitivity, which
    varies between macOS/Windows and Linux).
    """

    if not library_dir.is_dir():
        return {}
    index: dict[str, Path] = {}
    for candidate in library_dir.glob("*.pdf"):
        index[_normalize_name(candidate.stem).lower()] = candidate
    return index


def never_rename_violation(
    *,
    proposed_name: str,
    staged_path: Path,
    library_dir: Path,
) -> str | None:
    """Return the colliding published filename stem, or ``None`` if safe.

    A violation exists when *proposed_name* matches (case-insensitively) an
    already-published document in *library_dir* whose content differs from
    *staged_path*. Re-admitting byte-identical content under its own
    published name is not a violation (idempotent no-op).
    """

    index = _library_name_index(library_dir)
    existing = index.get(_normalize_name(proposed_name).lower())
    if existing is None:
        return None
    if _sha256_of_file(existing) == _sha256_of_file(staged_path):
        return None
    return existing.stem


def _backlog_by_url(
    inventory_items: Iterable[InventoryItem],
) -> dict[str, list[InventoryItem]]:
    """Group inventory Items lacking a ``Datasheet Name`` by their URL.

    Mirrors the jBOM#348 structural backlog signal (``Datasheet`` URL
    populated, ``Datasheet Name`` empty) already used by
    :mod:`jbom.services.datasheet_staging`.
    """

    backlog: dict[str, list[InventoryItem]] = {}
    for item in inventory_items:
        if is_admitted(item):
            continue
        url = str(item.datasheet or "").strip()
        if not url:
            continue
        backlog.setdefault(url, []).append(item)
    return backlog


def propose_admit_manifest(
    *,
    staging_dir: Path,
    library_dir: Path,
    inventory_items: Iterable[InventoryItem],
) -> list[AdmitManifestRow]:
    """Scan *staging_dir* and build a proposed admit manifest.

    Args:
        staging_dir: Resolved staging directory (jBOM#355); only verified
            (``.pdf`` suffix) files are considered -- unverified/flagged
            files are never proposed for admission.
        library_dir: The library's ``datasheets/`` directory (may not exist
            yet; only read for collision/dupe detection).
        inventory_items: Loaded inventory rows, used to build the backlog
            (URL -> member Items) and to derive proposed names.

    Returns:
        One :class:`AdmitManifestRow` per verified staged file, ordered by
        filename for determinism.
    """

    backlog = _backlog_by_url(inventory_items)
    # Precompute the staged stem for every backlog URL once, so each staged
    # file can be resolved back to its URL without re-deriving per file.
    stem_to_url: dict[str, str] = {
        staged_filename_for_url(url): url for url in backlog.keys()
    }

    rows: list[AdmitManifestRow] = []
    if not staging_dir.is_dir():
        return rows

    staged_files = sorted(
        p for p in staging_dir.glob(f"*{VERIFIED_SUFFIX}") if p.is_file()
    )
    for staged_path in staged_files:
        stem = staged_path.stem
        url = stem_to_url.get(stem, "")
        members = backlog.get(url, []) if url else []
        member_ipns = tuple(
            (m.ipn or "").strip() for m in members if (m.ipn or "").strip()
        )

        if not url or not members:
            rows.append(
                AdmitManifestRow(
                    action=ACTION_SKIP,
                    proposed_name="",
                    disposition=DISPOSITION_UNRESOLVABLE,
                    dupe_of="",
                    staged_file=staged_path.name,
                    source_url=url,
                    member_ipns=member_ipns,
                )
            )
            continue

        category = members[0].category
        manufacturer = members[0].manufacturer
        mfgpns = [m.mfgpn for m in members]
        proposed_name = propose_document_name(
            category=category, manufacturer=manufacturer, mfgpn_candidates=mfgpns
        )

        index = _library_name_index(library_dir)
        existing = index.get(_normalize_name(proposed_name).lower())
        if existing is not None and _sha256_of_file(existing) == _sha256_of_file(
            staged_path
        ):
            rows.append(
                AdmitManifestRow(
                    action=ACTION_ADMIT,
                    proposed_name=existing.stem,
                    disposition=DISPOSITION_DUPE_OF,
                    dupe_of=existing.stem,
                    staged_file=staged_path.name,
                    source_url=url,
                    member_ipns=member_ipns,
                )
            )
            continue

        if existing is not None:
            rows.append(
                AdmitManifestRow(
                    action=ACTION_SKIP,
                    proposed_name=proposed_name,
                    disposition=DISPOSITION_COLLISION,
                    dupe_of="",
                    staged_file=staged_path.name,
                    source_url=url,
                    member_ipns=member_ipns,
                )
            )
            continue

        rows.append(
            AdmitManifestRow(
                action=ACTION_ADMIT,
                proposed_name=proposed_name,
                disposition=DISPOSITION_NEW,
                dupe_of="",
                staged_file=staged_path.name,
                source_url=url,
                member_ipns=member_ipns,
            )
        )

    return rows


def write_admit_manifest(rows: Iterable[AdmitManifestRow], out: TextIO) -> None:
    """Write manifest rows as CSV to *out*."""

    writer = csv.DictWriter(out, fieldnames=list(MANIFEST_COLUMNS))
    writer.writeheader()
    for row in rows:
        writer.writerow(row.to_csv_row())


def read_admit_manifest(handle: TextIO) -> list[AdmitManifestRow]:
    """Read a (possibly human-edited) manifest CSV from *handle*."""

    reader = csv.DictReader(handle)
    return [AdmitManifestRow.from_csv_row(row) for row in reader]


def apply_admit_manifest(
    rows: Iterable[AdmitManifestRow],
    *,
    staging_dir: Path,
    library_dir: Path,
) -> AdmitApplyResult:
    """Apply a human-edited manifest: move accepted PDFs into the library.

    Only rows with ``Action == "ADMIT"`` are processed. Rows commit
    independently and in manifest order: each row's safety checks (invalid
    name, then never-rename) run before any filesystem mutation *for that
    row*, and a refusal skips only that row -- it never aborts or rolls
    back rows already admitted earlier in the same batch. Successfully
    admitted rows contribute one paste-file entry per member IPN, all
    carrying the row's proposed name (family docs name every member the
    same way).

    Args:
        rows: Manifest rows, typically from :func:`read_admit_manifest`.
        staging_dir: Directory containing the staged (verified) PDFs.
        library_dir: The library's ``datasheets/`` directory; created if
            needed only when a row is actually admitted.

    Returns:
        Aggregate :class:`AdmitApplyResult`.
    """

    outcomes: list[AdmitApplyOutcome] = []
    paste_rows: list[tuple[str, str]] = []

    for row in rows:
        if row.action.strip().upper() != ACTION_ADMIT:
            outcomes.append(
                AdmitApplyOutcome(
                    row=row,
                    status="skipped",
                    message=f"Action={row.action or '(blank)'}",
                )
            )
            continue

        proposed_name = _normalize_name(row.proposed_name)
        if not proposed_name:
            outcomes.append(
                AdmitApplyOutcome(
                    row=row,
                    status="skipped",
                    message="ADMIT row has no ProposedName; skipped.",
                )
            )
            continue

        # Path-safety guard runs first and unconditionally: the manifest is
        # human-edited free text, so a crafted ProposedName must never reach
        # a filesystem write, regardless of whether the staged file exists.
        invalid_reason = invalid_proposed_name_reason(
            proposed_name, library_dir=library_dir
        )
        if invalid_reason is not None:
            outcomes.append(
                AdmitApplyOutcome(
                    row=row,
                    status="refused-invalid-name",
                    message=(
                        f"Refusing to admit {row.staged_file!r}: {invalid_reason}"
                    ),
                )
            )
            continue

        staged_path = staging_dir / row.staged_file
        if not staged_path.is_file():
            outcomes.append(
                AdmitApplyOutcome(
                    row=row,
                    status="skipped",
                    message=f"Staged file not found: {staged_path}",
                )
            )
            continue

        violation = never_rename_violation(
            proposed_name=proposed_name,
            staged_path=staged_path,
            library_dir=library_dir,
        )
        if violation is not None:
            outcomes.append(
                AdmitApplyOutcome(
                    row=row,
                    status="refused-never-rename",
                    message=(
                        f"Refusing to admit {row.staged_file!r} as "
                        f"{proposed_name!r}: a published document named "
                        f"{violation!r} already exists with different "
                        "content. Never-rename protection: choose a "
                        "different name or resolve the collision by hand."
                    ),
                )
            )
            continue

        # OS-independent idempotent-reuse check: look up the target name in
        # the same case-insensitive/NFC-normalized index never_rename_
        # violation already consulted (never_rename_violation having passed
        # means either no match, or a byte-identical match) rather than
        # target_path.exists(), which only detects a case-variant match on
        # filesystems that happen to be case-insensitive (e.g. macOS).
        existing = _library_name_index(library_dir).get(proposed_name.lower())
        if existing is not None:
            # Idempotent re-admission of byte-identical content: no move
            # needed, but still contributes paste rows.
            status = "already-admitted"
            message = f"{existing.name} already published; no changes made."
        else:
            library_dir.mkdir(parents=True, exist_ok=True)
            target_path = library_dir / f"{proposed_name}.pdf"
            staged_path.replace(target_path)
            status = "admitted"
            message = f"Admitted {row.staged_file!r} as {proposed_name}.pdf"

        outcomes.append(AdmitApplyOutcome(row=row, status=status, message=message))
        for ipn in row.member_ipns:
            paste_rows.append((ipn, proposed_name))

    return AdmitApplyResult(outcomes=outcomes, paste_rows=paste_rows)


def write_paste_file(paste_rows: Iterable[tuple[str, str]], out: TextIO) -> None:
    """Write the full-sheet ``Datasheet Name`` paste-file proposal.

    One row per admitted member Item (``IPN``, ``Datasheet Name``), ready
    for a human to paste the ``Datasheet Name`` column values into the
    canonical inventory at the matching IPN rows. jBOM never writes to the
    inventory directly (jBOM#347/#348).
    """

    writer = csv.DictWriter(out, fieldnames=["IPN", _DATASHEET_NAME_COLUMN])
    writer.writeheader()
    for ipn, name in paste_rows:
        writer.writerow({"IPN": ipn, _DATASHEET_NAME_COLUMN: name})


__all__ = [
    "ACTION_ADMIT",
    "ACTION_SKIP",
    "DISPOSITION_COLLISION",
    "DISPOSITION_DUPE_OF",
    "DISPOSITION_NEW",
    "DISPOSITION_UNRESOLVABLE",
    "MANIFEST_COLUMNS",
    "AdmitApplyOutcome",
    "AdmitApplyResult",
    "AdmitManifestRow",
    "apply_admit_manifest",
    "invalid_proposed_name_reason",
    "never_rename_violation",
    "propose_admit_manifest",
    "propose_document_name",
    "read_admit_manifest",
    "write_admit_manifest",
    "write_paste_file",
]
