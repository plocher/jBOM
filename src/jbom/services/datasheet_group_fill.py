"""Output-time Datasheet URL group-fill for Datasheet Name families (jBOM#374).

Inventory keeps the one-URL-per-Name provenance rule: exactly one row in a
``Datasheet Name`` family carries the canonical source URL and siblings leave
``Datasheet`` blank. Generated BOM/PARTS output group-fills those blanks from
the family's single distinct non-empty URL. The inventory file is never
modified — this is a derived emit-time value only.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Mapping

from jbom.common.types import InventoryItem
from jbom.services.datasheet_library import get_datasheet_name


def build_datasheet_family_url_map(
    items: Iterable[InventoryItem],
) -> dict[str, str]:
    """Map lowercased Datasheet Name → URL when the family has one distinct URL.

    Rows without a Datasheet Name are ignored. Blank Datasheet cells do not
    contribute URLs. When a family has zero non-empty URLs or two or more
    distinct non-empty URLs, that family is omitted from the map so callers
    emit blank (no guessing; audit owns those states).
    """

    urls_by_name: dict[str, set[str]] = defaultdict(set)
    for item in items:
        name = get_datasheet_name(item)
        if not name:
            continue
        url = str(item.datasheet or "").strip()
        if not url:
            continue
        urls_by_name[name.lower()].add(url)

    family_map: dict[str, str] = {}
    for name_key, urls in urls_by_name.items():
        if len(urls) == 1:
            family_map[name_key] = next(iter(urls))
    return family_map


def resolve_output_datasheet(
    item: InventoryItem,
    family_urls: Mapping[str, str],
) -> str:
    """Return the Datasheet URL to emit for *item* (verbatim or family fill).

    Populated ``item.datasheet`` cells pass through unchanged. Blank cells with
    a Datasheet Name take the family's mapped URL when present; otherwise the
    result is blank.
    """

    own_url = str(item.datasheet or "").strip()
    if own_url:
        return own_url

    name = get_datasheet_name(item)
    if not name:
        return ""
    return str(family_urls.get(name.lower(), "") or "").strip()


__all__ = [
    "build_datasheet_family_url_map",
    "resolve_output_datasheet",
]
