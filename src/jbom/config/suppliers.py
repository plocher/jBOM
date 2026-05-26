"""Supplier configuration loader.

Supplier profiles capture supplier-specific knowledge such as:
- URL templates for direct product links and search pages
- Part-number validation patterns
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    computed_field,
    field_validator,
    model_validator,
)

from jbom.config.field_synonyms import FieldSynonym, parse_field_synonyms
from jbom.config.profile_search import profile_search_dirs
from jbom.config.providers import SearchProviderConfig
from jbom.config.unified import (
    UnifiedProfileNotFoundError,
    list_unified_stanza_ids,
    load_unified,
    resolve_profile_name_for_stanza_id,
    supplier_stanza,
)


SupplierFieldSynonym = FieldSynonym


class SupplierPartNumberConfig(BaseModel):
    """Supplier part-number validation config."""

    model_config = ConfigDict(extra="ignore")

    pattern: Optional[str] = None
    example: Optional[str] = None

    @field_validator("pattern", "example", mode="before")
    @classmethod
    def _normalize_optional_string(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        normalized = str(value).strip()
        if not normalized:
            return None
        return normalized


class SupplierSearchCacheConfig(BaseModel):
    """Supplier search cache tuning options."""

    model_config = ConfigDict(extra="ignore")

    ttl_hours: Optional[float] = None

    @field_validator("ttl_hours", mode="before")
    @classmethod
    def _validate_ttl_hours(cls, value: Any) -> Optional[float]:
        if value is None:
            return None
        if not isinstance(value, (int, float)):
            raise ValueError("search.cache.ttl_hours must be a number or null")
        return float(value)


class SupplierSearchApiConfig(BaseModel):
    """Supplier search API tuning options."""

    model_config = ConfigDict(extra="ignore")

    timeout_seconds: Optional[float] = None
    max_retries: Optional[int] = None
    retry_delay_seconds: Optional[float] = None

    @field_validator("timeout_seconds", mode="before")
    @classmethod
    def _validate_timeout_seconds(cls, value: Any) -> Optional[float]:
        if value is None:
            return None
        if not isinstance(value, (int, float)):
            raise ValueError("search.api.timeout_seconds must be a number or null")
        return float(value)

    @field_validator("max_retries", mode="before")
    @classmethod
    def _validate_max_retries(cls, value: Any) -> Optional[int]:
        if value is None:
            return None
        if not isinstance(value, int):
            raise ValueError("search.api.max_retries must be an int or null")
        return int(value)

    @field_validator("retry_delay_seconds", mode="before")
    @classmethod
    def _validate_retry_delay_seconds(cls, value: Any) -> Optional[float]:
        if value is None:
            return None
        if not isinstance(value, (int, float)):
            raise ValueError("search.api.retry_delay_seconds must be a number or null")
        return float(value)


class SupplierSearchConfig(BaseModel):
    """Supplier `search:` stanza."""

    model_config = ConfigDict(extra="ignore")

    providers: list[SearchProviderConfig] = Field(default_factory=list)
    fields: list[str] = Field(default_factory=list)
    cache: SupplierSearchCacheConfig = Field(default_factory=SupplierSearchCacheConfig)
    api: SupplierSearchApiConfig = Field(default_factory=SupplierSearchApiConfig)
    type_query_keywords: dict[str, str] = Field(default_factory=dict)

    @field_validator("providers", mode="before")
    @classmethod
    def _parse_providers(cls, value: Any) -> list[SearchProviderConfig]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("search.providers must be a list")

        providers: list[SearchProviderConfig] = []
        for provider_cfg in value:
            if not isinstance(provider_cfg, dict):
                raise ValueError("search.providers entries must be mappings")

            ptype = provider_cfg.get("type")
            if not isinstance(ptype, str) or not ptype.strip():
                raise ValueError(
                    "search.providers entries must include non-empty 'type'"
                )

            extra = {key: val for key, val in provider_cfg.items() if key != "type"}
            providers.append(
                SearchProviderConfig.model_validate(
                    {"type": ptype.strip(), "extra": dict(extra)}
                )
            )

        return providers

    @field_validator("fields", mode="before")
    @classmethod
    def _normalize_fields(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("search.fields must be a list")

        fields: list[str] = []
        for field_name in value:
            token = str(field_name or "").strip()
            if not token:
                raise ValueError("search.fields entries must be non-empty strings")
            fields.append(token.lower())
        return list(dict.fromkeys(fields).keys())

    @field_validator("type_query_keywords", mode="before")
    @classmethod
    def _normalize_type_query_keywords(cls, value: Any) -> dict[str, str]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("search.type_query_keywords must be a mapping")

        normalized: dict[str, str] = {}
        for key, val in value.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError(
                    "search.type_query_keywords keys must be non-empty strings"
                )
            if not isinstance(val, str) or not val.strip():
                raise ValueError(
                    f"search.type_query_keywords[{key!r}] must be a non-empty string"
                )
            normalized[key.strip().upper()] = val.strip()
        return normalized


class SupplierConfig(BaseModel):
    """Configuration for a parts supplier/distributor."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    field_synonyms: dict[str, SupplierFieldSynonym] = Field(default_factory=dict)
    description: Optional[str] = None
    website: Optional[str] = None
    url_template: Optional[str] = None
    search_url_template: Optional[str] = None
    part_number: SupplierPartNumberConfig = Field(
        default_factory=SupplierPartNumberConfig
    )
    search: SupplierSearchConfig = Field(default_factory=SupplierSearchConfig)

    @model_validator(mode="before")
    @classmethod
    def _normalize_input(cls, raw: Any, info: ValidationInfo) -> Dict[str, Any]:
        if not isinstance(raw, dict):
            raise ValueError("Supplier config must be a YAML mapping")

        data = dict(raw)

        default_id = ""
        if isinstance(info.context, dict):
            default_id = str(info.context.get("default_id", "")).strip()
        if "id" not in data and default_id:
            data["id"] = default_id
        if "name" not in data and default_id:
            data["name"] = default_id

        return data

    @field_validator("id", "name")
    @classmethod
    def _validate_required_strings(cls, value: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("Supplier id/name must be non-empty strings")
        return normalized

    @field_validator("field_synonyms", mode="before")
    @classmethod
    def _parse_field_synonyms(cls, value: Any) -> dict[str, SupplierFieldSynonym]:
        return parse_field_synonyms(
            value,
            context="field_synonyms",
            strict=True,
            default_display_name_from_key=False,
            normalize_canonical_key=lambda key: key.strip().lower(),
        )

    @field_validator(
        "description", "website", "url_template", "search_url_template", mode="before"
    )
    @classmethod
    def _normalize_optional_strings(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Supplier string fields must be strings or null")
        return value

    @model_validator(mode="after")
    def _validate_relationships(self) -> "SupplierConfig":
        supplier_pn_synonym = self.field_synonyms.get("supplier_pn")
        if supplier_pn_synonym is None:
            raise ValueError(
                f"Supplier '{self.id}' field_synonyms must define canonical 'supplier_pn'"
            )

        pattern = self.part_number.pattern
        if pattern:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(
                    f"Supplier '{self.id}' part_number.pattern is not a valid regex: {pattern!r}"
                ) from exc

        return self

    @computed_field
    @property
    def supplier_label(self) -> str:
        """Display value matched against the Supplier CSV column."""

        return self.field_synonyms["supplier_pn"].display_name

    @computed_field
    @property
    def part_number_pattern(self) -> Optional[str]:
        return self.part_number.pattern

    @computed_field
    @property
    def part_number_example(self) -> Optional[str]:
        return self.part_number.example

    @computed_field
    @property
    def search_fields(self) -> list[str]:
        return list(self.search.fields)

    @computed_field
    @property
    def search_providers(self) -> list[SearchProviderConfig]:
        return list(self.search.providers)

    @computed_field
    @property
    def search_cache_ttl_hours(self) -> Optional[float]:
        return self.search.cache.ttl_hours

    @computed_field
    @property
    def search_timeout_seconds(self) -> Optional[float]:
        return self.search.api.timeout_seconds

    @computed_field
    @property
    def search_max_retries(self) -> Optional[int]:
        return self.search.api.max_retries

    @computed_field
    @property
    def search_retry_delay_seconds(self) -> Optional[float]:
        return self.search.api.retry_delay_seconds

    @computed_field
    @property
    def search_type_query_keywords(self) -> dict[str, str]:
        return dict(self.search.type_query_keywords)


_BUILTIN_DIR = Path(__file__).parent / "suppliers"


def list_suppliers() -> list[str]:
    """List available supplier IDs by scanning the built-in config directory."""
    return list(_list_suppliers_cached())


def get_available_suppliers() -> list[str]:
    """Get list of available suppliers with a stable fallback."""

    suppliers = list_suppliers()
    return suppliers if suppliers else ["generic"]


def load_supplier(sid: str) -> SupplierConfig:
    """Load supplier configuration from YAML file."""
    normalized_sid = str(sid or "").strip().lower()
    config = _load_supplier_cached(normalized_sid)
    return config.model_copy(deep=True)


def clear_supplier_config_caches() -> None:
    """Clear memoized supplier config caches."""

    _list_suppliers_cached.cache_clear()
    _load_supplier_cached.cache_clear()


@lru_cache(maxsize=1)
def _list_suppliers_cached() -> tuple[str, ...]:
    legacy_ids: list[str] = []
    if _BUILTIN_DIR.exists():
        legacy_ids = sorted(
            p.stem.replace(".supplier", "")
            for p in _BUILTIN_DIR.glob("*.supplier.yaml")
        )
    unified_ids = list_unified_stanza_ids("supplier")
    return tuple(sorted(set([*legacy_ids, *unified_ids])))


@lru_cache(maxsize=128)
def _load_supplier_cached(normalized_sid: str) -> SupplierConfig:
    if not normalized_sid:
        raise ValueError("Unknown supplier: ")
    try:
        merged = load_unified(normalized_sid)
        return supplier_stanza(merged, default_id=normalized_sid)
    except UnifiedProfileNotFoundError:
        mapped_profile_name = resolve_profile_name_for_stanza_id(
            "supplier", normalized_sid
        )
        if mapped_profile_name:
            merged = load_unified(mapped_profile_name)
            return supplier_stanza(merged, default_id=normalized_sid)
        path = _find_legacy_profile(normalized_sid, suffix="supplier")
        if path is None:
            raise ValueError(f"Unknown supplier: {normalized_sid}") from None

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return SupplierConfig.model_validate(data, context={"default_id": normalized_sid})


def _find_legacy_profile(name: str, *, suffix: str) -> Path | None:
    filename = f"{name}.{suffix}.yaml"
    search_dirs = list(profile_search_dirs())
    search_dirs.append(_BUILTIN_DIR)
    for directory in search_dirs:
        candidate = directory / filename
        if candidate.is_file():
            return candidate
    return None


def validate_part_number(supplier: SupplierConfig, pn: str) -> bool:
    """Validate part number using the supplier's regex, when available."""

    pn_norm = (pn or "").strip()
    if not pn_norm:
        return False

    pattern = (supplier.part_number.pattern or "").strip()
    if not pattern:
        return True

    return re.fullmatch(pattern, pn_norm) is not None


def normalize_supplier_id(supplier_id: str) -> str:
    """Normalize supplier id for case-insensitive lookups."""

    return (supplier_id or "").strip().lower()


def resolve_supplier_by_id(supplier_id: str) -> Optional[SupplierConfig]:
    """Load a supplier config, returning None if it is unknown."""

    try:
        return load_supplier(normalize_supplier_id(supplier_id))
    except ValueError:
        return None


def get_spn_for_item(raw_data: Mapping[str, str], supplier: SupplierConfig) -> str:
    """Return the SPN from raw_data when the Supplier column matches this supplier."""

    item_supplier = str(raw_data.get("Supplier", "")).strip().lower()
    if item_supplier == supplier.id or item_supplier == supplier.supplier_label.lower():
        return str(raw_data.get("SPN", "")).strip()
    return ""
