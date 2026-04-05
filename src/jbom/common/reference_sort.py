"""Reference designator natural sorting helpers."""

from __future__ import annotations

import re
from typing import Iterable

_NATURAL_TOKEN_SPLIT = re.compile(r"(\d+)")


def natural_reference_sort_key(reference: str) -> list[object]:
    """Return a natural sort key for a component reference designator."""
    normalized_reference = str(reference or "")
    key: list[object] = []
    for token in _NATURAL_TOKEN_SPLIT.split(normalized_reference):
        if token.isdigit():
            key.append(int(token))
        else:
            key.append(token)
    return key


def natural_sort_references(references: Iterable[str]) -> list[str]:
    """Return component references sorted in natural alphanumeric order."""
    normalized_references = [str(reference or "") for reference in references]
    return sorted(normalized_references, key=natural_reference_sort_key)
