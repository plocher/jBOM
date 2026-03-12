"""Shared helpers for robust synonym matching across config and intake paths."""

from __future__ import annotations

from typing import Mapping, Sequence


def normalize_synonym_token(token: str) -> str:
    """Normalize a synonym token for forgiving comparisons.

    Normalization is case-insensitive and treats underscores/hyphens as spaces.
    """

    if not token:
        return ""

    normalized = str(token).replace("_", " ").replace("-", " ")
    return " ".join(normalized.split()).strip().lower()


def first_non_empty_alias_value(row: Mapping[str, str], aliases: Sequence[str]) -> str:
    """Return first non-empty row value matching any alias token.

    Matching first attempts exact key lookup, then normalized-token lookup.
    """

    if not row:
        return ""

    normalized_row_keys: dict[str, str] = {}
    for row_key in row.keys():
        normalized = normalize_synonym_token(str(row_key))
        if normalized and normalized not in normalized_row_keys:
            normalized_row_keys[normalized] = str(row_key)

    for alias in aliases:
        alias_key = str(alias).strip()
        if not alias_key:
            continue

        exact_value = str(row.get(alias_key, "")).strip()
        if exact_value:
            return exact_value

        normalized_alias = normalize_synonym_token(alias_key)
        matched_key = normalized_row_keys.get(normalized_alias)
        if matched_key is None:
            continue

        normalized_value = str(row.get(matched_key, "")).strip()
        if normalized_value:
            return normalized_value

    return ""
