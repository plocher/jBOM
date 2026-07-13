"""Pure helpers for datasheet document-library hygiene checks (jBOM#357).

These helpers back the read-only, offline lints ``jbom audit`` grows for the
shared ``SPCoast-inventory`` datasheet document library (see jBOM#342).
"""

from __future__ import annotations

import difflib
import re
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Iterable

from jbom.common.types import InventoryItem

DATASHEET_NAME_COLUMN = "Datasheet Name"
DATASHEETS_SUBDIR = "datasheets"
NAME_NEAR_COLLISION_RATIO = 0.90
NAME_NEAR_COLLISION_MIN_LENGTH = 6


def get_datasheet_name(item: InventoryItem) -> str:
    """Return *item*'s curated ``Datasheet Name``, or ``""`` when absent."""

    raw = item.raw_data or {}
    return str(raw.get(DATASHEET_NAME_COLUMN, "") or "").strip()


def normalize_token(text: str) -> str:
    """Normalize a manufacturer/tech token for canonical-spelling comparison."""

    return re.sub(r"[^A-Za-z0-9]+", "", text or "").upper()


def resolve_canonical_spellings(values: Iterable[str]) -> dict[str, str]:
    """Map each normalized token to its canonical most-common spelling."""

    groups: OrderedDict[str, list[str]] = OrderedDict()
    for value in values:
        cleaned = str(value or "").strip()
        if not cleaned:
            continue
        key = normalize_token(cleaned)
        if not key:
            continue
        groups.setdefault(key, []).append(cleaned)

    canonical: dict[str, str] = {}
    for key, spellings in groups.items():
        counts = Counter(spellings)
        best_count = max(counts.values())
        for spelling in spellings:
            if counts[spelling] == best_count:
                canonical[key] = spelling
                break
    return canonical


def find_near_collisions(names: Iterable[str]) -> list[tuple[str, str, float]]:
    """Return suspiciously similar, non-identical ``Datasheet Name`` pairs."""

    unique = sorted({n for n in names if n})
    pairs: list[tuple[str, str, float]] = []
    for i, name_a in enumerate(unique):
        for name_b in unique[i + 1 :]:
            if name_a.lower() == name_b.lower():
                continue
            if (
                len(name_a) < NAME_NEAR_COLLISION_MIN_LENGTH
                or len(name_b) < NAME_NEAR_COLLISION_MIN_LENGTH
            ):
                continue
            ratio = difflib.SequenceMatcher(
                None, name_a.lower(), name_b.lower()
            ).ratio()
            if ratio >= NAME_NEAR_COLLISION_RATIO:
                pairs.append((name_a, name_b, ratio))
    return pairs


def group_case_insensitive_variants(names: Iterable[str]) -> dict[str, set[str]]:
    """Group Datasheet Names by lowercase form, revealing casing drift."""

    groups: dict[str, set[str]] = {}
    for name in names:
        if not name:
            continue
        groups.setdefault(name.lower(), set()).add(name)
    return groups


def extract_name_tokens(name: str) -> list[str]:
    """Split a curated Datasheet Name into its hyphen/underscore tokens."""

    return [tok for tok in re.split(r"[-_]", name or "") if tok]


def datasheet_filename(name: str) -> str:
    """Return the library filename for a curated Datasheet Name."""

    return f"{name}.pdf"


def scan_library_pdfs(library_dir: Path) -> list[str]:
    """Return sorted PDF filename stems found in ``<library_dir>/datasheets/``."""

    datasheets_dir = Path(library_dir) / DATASHEETS_SUBDIR
    if not datasheets_dir.is_dir():
        return []
    return sorted(p.stem for p in datasheets_dir.glob("*.pdf"))


__all__ = [
    "DATASHEET_NAME_COLUMN",
    "DATASHEETS_SUBDIR",
    "NAME_NEAR_COLLISION_RATIO",
    "NAME_NEAR_COLLISION_MIN_LENGTH",
    "get_datasheet_name",
    "normalize_token",
    "resolve_canonical_spellings",
    "find_near_collisions",
    "group_case_insensitive_variants",
    "extract_name_tokens",
    "datasheet_filename",
    "scan_library_pdfs",
]
