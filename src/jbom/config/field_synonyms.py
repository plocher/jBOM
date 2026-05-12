"""Shared field-synonym schema + parser helpers for config models."""

from __future__ import annotations

import logging
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FieldSynonym(BaseModel):
    """Canonical field naming plus accepted synonym headers."""

    model_config = ConfigDict(extra="ignore")

    display_name: str
    synonyms: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("display_name")
    @classmethod
    def _validate_display_name(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("display_name must be a non-empty string")
        return value.strip()

    @field_validator("synonyms", mode="before")
    @classmethod
    def _normalize_synonyms(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return tuple()
        if not isinstance(value, (list, tuple)):
            raise ValueError("synonyms must be a list/tuple of non-empty strings")

        normalized: list[str] = []
        for synonym in value:
            if not isinstance(synonym, str) or not synonym.strip():
                raise ValueError("synonyms must be a list/tuple of non-empty strings")
            normalized.append(synonym.strip())

        return tuple(dict.fromkeys(normalized).keys())


def parse_field_synonyms(
    raw: Any,
    *,
    context: str,
    strict: bool,
    normalize_canonical_key: Callable[[str], str] | None = None,
    default_display_name_from_key: bool,
    logger: logging.Logger | None = None,
) -> dict[str, FieldSynonym]:
    """Parse YAML field-synonym maps into ``FieldSynonym`` models."""

    log = logger or logging.getLogger(__name__)

    if raw is None:
        return {}

    if not isinstance(raw, dict):
        if strict:
            raise ValueError(f"{context} must be a mapping")
        log.warning("%s must be a mapping; found %r", context, type(raw).__name__)
        return {}

    parsed: dict[str, FieldSynonym] = {}
    for raw_canonical, cfg in raw.items():
        if not isinstance(raw_canonical, str):
            if strict:
                raise ValueError(f"{context} keys must be non-empty strings")
            continue

        canonical = raw_canonical.strip()
        if normalize_canonical_key is not None:
            canonical = normalize_canonical_key(canonical)
        if not canonical:
            if strict:
                raise ValueError(f"{context} keys must be non-empty strings")
            continue

        if not isinstance(cfg, dict):
            if strict:
                raise ValueError(f"{context}[{raw_canonical!r}] must be a mapping")
            continue

        display_name_raw = cfg.get("display_name")
        if display_name_raw is None and default_display_name_from_key:
            display_name = canonical
        elif isinstance(display_name_raw, str) and display_name_raw.strip():
            display_name = display_name_raw.strip()
        else:
            if strict:
                raise ValueError(
                    f"{context}[{raw_canonical!r}].display_name must be a non-empty string"
                )
            display_name = canonical

        synonyms_raw = cfg.get("synonyms")
        if synonyms_raw is None:
            synonyms_raw = []

        if not isinstance(synonyms_raw, list):
            if strict:
                raise ValueError(
                    f"{context}[{raw_canonical!r}].synonyms must be a list of non-empty strings"
                )
            log.warning(
                "%s[%r].synonyms must be a list; found %r",
                context,
                raw_canonical,
                type(synonyms_raw).__name__,
            )
            synonyms_raw = []

        synonyms: list[str] = []
        invalid_synonym = False
        for synonym in synonyms_raw:
            if not isinstance(synonym, str) or not synonym.strip():
                if strict:
                    invalid_synonym = True
                    break
                continue
            synonyms.append(synonym.strip())

        if invalid_synonym:
            raise ValueError(
                f"{context}[{raw_canonical!r}].synonyms must be a list of non-empty strings"
            )

        current = FieldSynonym.model_validate(
            {"display_name": display_name, "synonyms": synonyms}
        )
        existing = parsed.get(canonical)
        if existing is None:
            parsed[canonical] = current
            continue

        merged_synonyms = list(
            dict.fromkeys([*existing.synonyms, *current.synonyms]).keys()
        )
        parsed[canonical] = FieldSynonym.model_validate(
            {
                "display_name": existing.display_name or current.display_name,
                "synonyms": merged_synonyms,
            }
        )

    return parsed


__all__ = ["FieldSynonym", "parse_field_synonyms"]
