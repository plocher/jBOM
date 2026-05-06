"""Supplier configuration loader.

Supplier profiles capture supplier-specific knowledge such as:
- URL templates for direct product links and search pages
- Part-number validation patterns

Profiles are loaded from the search path (project .jbom/, JBOM_PROFILE_PATH,
~/.jbom/, system dirs) before falling back to built-in package profiles.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from jbom.config.profile_search import find_profile
from jbom.config.providers import SearchProviderConfig

import yaml


@dataclass(frozen=True)
class SupplierFieldSynonym:
    """Canonical supplier field naming plus accepted synonym headers."""

    display_name: str
    synonyms: list[str]


@dataclass(frozen=True)
class SupplierConfig:
    """Configuration for a parts supplier/distributor.

    ``supplier_label`` is the value that appears in the ``Supplier`` column of
    the normalized inventory CSV (e.g. ``"LCSC"`` for LCSC Electronics).  It
    is NOT a CSV column name.
    """

    id: str
    name: str
    supplier_label: str  # value matched against the Supplier CSV column
    field_synonyms: dict[str, SupplierFieldSynonym] = field(default_factory=dict)

    description: Optional[str] = None
    website: Optional[str] = None

    url_template: Optional[str] = None
    search_url_template: Optional[str] = None

    part_number_pattern: Optional[str] = None
    part_number_example: Optional[str] = None

    # Search output field selection (applies to console + CSV output).
    search_fields: list[str] = field(default_factory=list)

    # Search provider configuration (ordered fallback chain).
    # Empty means the supplier has no search capability.
    search_providers: list[SearchProviderConfig] = field(default_factory=list)

    # Search behavior tuning (optional).
    search_cache_ttl_hours: Optional[float] = None
    search_timeout_seconds: Optional[float] = None
    search_max_retries: Optional[int] = None
    search_retry_delay_seconds: Optional[float] = None

    # Optional category -> keyword mapping used by inventory-search query construction.
    # Keys should be normalized component category tokens (e.g. RES, CAP, IND).
    search_type_query_keywords: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def from_yaml_dict(data: Dict[str, Any], *, default_id: str) -> "SupplierConfig":
        """Parse a SupplierConfig from a YAML dict.

        Args:
            data: YAML mapping produced by yaml.safe_load().
            default_id: Supplier ID derived from filename when 'id' is not set.

        Raises:
            ValueError: When required fields are missing or schema is invalid.
        """

        if not isinstance(data, dict):
            raise ValueError(f"Supplier '{default_id}' config must be a YAML mapping")

        sid = data.get("id", default_id)
        name = data.get("name", default_id)
        field_synonyms_cfg = data.get("field_synonyms")

        if not isinstance(sid, str) or not sid.strip():
            raise ValueError("Supplier id must be a non-empty string")

        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Supplier '{sid}' name must be a non-empty string")

        if not isinstance(field_synonyms_cfg, dict):
            raise ValueError(
                f"Supplier '{sid}' field_synonyms must be a mapping with supplier_pn"
            )

        parsed_field_synonyms: dict[str, SupplierFieldSynonym] = {}
        for canonical, cfg in field_synonyms_cfg.items():
            if not isinstance(canonical, str) or not canonical.strip():
                raise ValueError(
                    f"Supplier '{sid}' field_synonyms keys must be non-empty strings"
                )
            if not isinstance(cfg, dict):
                raise ValueError(
                    f"Supplier '{sid}' field_synonyms[{canonical!r}] must be a mapping"
                )

            display_name = cfg.get("display_name")
            if not isinstance(display_name, str) or not display_name.strip():
                raise ValueError(
                    f"Supplier '{sid}' field_synonyms[{canonical!r}].display_name must be a non-empty string"
                )

            synonyms_cfg = cfg.get("synonyms") or []
            if not isinstance(synonyms_cfg, list) or not all(
                isinstance(s, str) and s.strip() for s in synonyms_cfg
            ):
                raise ValueError(
                    f"Supplier '{sid}' field_synonyms[{canonical!r}].synonyms must be a list of non-empty strings"
                )

            parsed_field_synonyms[canonical.strip().lower()] = SupplierFieldSynonym(
                display_name=display_name.strip(),
                synonyms=[s.strip() for s in synonyms_cfg],
            )

        supplier_pn_synonym = parsed_field_synonyms.get("supplier_pn")
        if supplier_pn_synonym is None:
            raise ValueError(
                f"Supplier '{sid}' field_synonyms must define canonical 'supplier_pn'"
            )
        supplier_label = supplier_pn_synonym.display_name

        part_number_cfg = data.get("part_number") or {}

        if not isinstance(part_number_cfg, dict):
            raise ValueError(f"Supplier '{sid}' part_number must be a mapping")

        pattern = part_number_cfg.get("pattern")
        example = part_number_cfg.get("example")

        if pattern is not None and (
            not isinstance(pattern, str) or not pattern.strip()
        ):
            raise ValueError(f"Supplier '{sid}' part_number.pattern must be a string")

        if example is not None and (
            not isinstance(example, str) or not example.strip()
        ):
            raise ValueError(f"Supplier '{sid}' part_number.example must be a string")

        url_template = data.get("url_template")
        if url_template is not None and not isinstance(url_template, str):
            raise ValueError(f"Supplier '{sid}' url_template must be a string or null")

        # Optional search behavior tuning.
        search_cfg = data.get("search") or {}
        if not isinstance(search_cfg, dict):
            raise ValueError(f"Supplier '{sid}' search must be a mapping")

        fields_cfg = search_cfg.get("fields") or []
        if not isinstance(fields_cfg, list):
            raise ValueError(f"Supplier '{sid}' search.fields must be a list")

        search_fields: list[str] = []
        for f in fields_cfg:
            if not isinstance(f, str) or not f.strip():
                raise ValueError(
                    f"Supplier '{sid}' search.fields entries must be non-empty strings"
                )
            search_fields.append(f.strip().lower())

        providers_cfg = search_cfg.get("providers") or []
        if not isinstance(providers_cfg, list):
            raise ValueError(f"Supplier '{sid}' search.providers must be a list")

        search_providers: list[SearchProviderConfig] = []
        for p in providers_cfg:
            if not isinstance(p, dict):
                raise ValueError(
                    f"Supplier '{sid}' search.providers entries must be mappings"
                )

            ptype = p.get("type")
            if not isinstance(ptype, str) or not ptype.strip():
                raise ValueError(
                    f"Supplier '{sid}' search.providers entries must include non-empty 'type'"
                )

            extra = {k: v for k, v in p.items() if k != "type"}
            search_providers.append(
                SearchProviderConfig(type=ptype.strip(), extra=dict(extra))
            )

        cache_cfg = search_cfg.get("cache") or {}
        if not isinstance(cache_cfg, dict):
            raise ValueError(f"Supplier '{sid}' search.cache must be a mapping")

        cache_ttl_hours = cache_cfg.get("ttl_hours")
        if cache_ttl_hours is not None and not isinstance(
            cache_ttl_hours, (int, float)
        ):
            raise ValueError(
                f"Supplier '{sid}' search.cache.ttl_hours must be a number or null"
            )

        api_cfg = search_cfg.get("api") or {}
        if not isinstance(api_cfg, dict):
            raise ValueError(f"Supplier '{sid}' search.api must be a mapping")

        type_query_keywords_cfg = search_cfg.get("type_query_keywords") or {}
        if not isinstance(type_query_keywords_cfg, dict):
            raise ValueError(
                f"Supplier '{sid}' search.type_query_keywords must be a mapping"
            )

        type_query_keywords: dict[str, str] = {}
        for k, v in type_query_keywords_cfg.items():
            if not isinstance(k, str) or not k.strip():
                raise ValueError(
                    f"Supplier '{sid}' search.type_query_keywords keys must be non-empty strings"
                )
            if not isinstance(v, str) or not v.strip():
                raise ValueError(
                    f"Supplier '{sid}' search.type_query_keywords[{k!r}] must be a non-empty string"
                )
            type_query_keywords[k.strip().upper()] = v.strip()

        timeout_seconds = api_cfg.get("timeout_seconds")
        if timeout_seconds is not None and not isinstance(
            timeout_seconds, (int, float)
        ):
            raise ValueError(
                f"Supplier '{sid}' search.api.timeout_seconds must be a number or null"
            )

        max_retries = api_cfg.get("max_retries")
        if max_retries is not None and not isinstance(max_retries, int):
            raise ValueError(
                f"Supplier '{sid}' search.api.max_retries must be an int or null"
            )

        retry_delay_seconds = api_cfg.get("retry_delay_seconds")
        if retry_delay_seconds is not None and not isinstance(
            retry_delay_seconds, (int, float)
        ):
            raise ValueError(
                f"Supplier '{sid}' search.api.retry_delay_seconds must be a number or null"
            )

        search_url_template = data.get("search_url_template")
        if search_url_template is not None and not isinstance(search_url_template, str):
            raise ValueError(
                f"Supplier '{sid}' search_url_template must be a string or null"
            )

        description = data.get("description")
        if description is not None and not isinstance(description, str):
            raise ValueError(f"Supplier '{sid}' description must be a string or null")

        website = data.get("website")
        if website is not None and not isinstance(website, str):
            raise ValueError(f"Supplier '{sid}' website must be a string or null")

        # Best-effort validation of regex.
        if isinstance(pattern, str) and pattern.strip():
            try:
                re.compile(pattern)
            except re.error as e:
                raise ValueError(
                    f"Supplier '{sid}' part_number.pattern is not a valid regex: {pattern!r}"
                ) from e

        return SupplierConfig(
            id=sid,
            name=name,
            supplier_label=supplier_label,
            field_synonyms=parsed_field_synonyms,
            description=description,
            website=website,
            url_template=url_template,
            search_url_template=search_url_template,
            part_number_pattern=pattern,
            part_number_example=example,
            search_fields=search_fields,
            search_providers=search_providers,
            search_cache_ttl_hours=(
                float(cache_ttl_hours) if cache_ttl_hours is not None else None
            ),
            search_timeout_seconds=(
                float(timeout_seconds) if timeout_seconds is not None else None
            ),
            search_max_retries=(int(max_retries) if max_retries is not None else None),
            search_retry_delay_seconds=(
                float(retry_delay_seconds) if retry_delay_seconds is not None else None
            ),
            search_type_query_keywords=type_query_keywords,
        )


_BUILTIN_DIR = Path(__file__).parent / "suppliers"


def list_suppliers() -> list[str]:
    """List available supplier IDs by scanning the built-in config directory."""

    if not _BUILTIN_DIR.exists():
        return []

    # Filename: <id>.supplier.yaml
    return sorted(
        p.stem.replace(".supplier", "") for p in _BUILTIN_DIR.glob("*.supplier.yaml")
    )


def get_available_suppliers() -> list[str]:
    """Get list of available suppliers with a stable fallback."""

    suppliers = list_suppliers()
    return suppliers if suppliers else ["generic"]


def load_supplier(sid: str) -> SupplierConfig:
    """Load supplier configuration from YAML file.

    Searches the profile search path (project .jbom/, repo root, JBOM_PROFILE_PATH,
    ~/.jbom/, system dirs) before falling back to the built-in package directory.

    Args:
        sid: Supplier ID (filename without .supplier.yaml extension)

    Returns:
        Parsed SupplierConfig.

    Raises:
        ValueError: If supplier not found or schema is invalid.
    """

    path = find_profile(sid, "supplier", builtin_dir=_BUILTIN_DIR)
    if path is None:
        raise ValueError(f"Unknown supplier: {sid}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Supplier '{sid}' config must be a YAML mapping")

    return SupplierConfig.from_yaml_dict(data, default_id=sid)


def validate_part_number(supplier: SupplierConfig, pn: str) -> bool:
    """Validate part number using the supplier's regex, when available.

    Validation is advisory: if the supplier has no pattern, validation passes.

    Args:
        supplier: SupplierConfig used to validate.
        pn: Part number string.

    Returns:
        True if pn matches the supplier pattern (or no pattern is defined).
    """

    pn_norm = (pn or "").strip()
    if not pn_norm:
        return False

    pattern = (supplier.part_number_pattern or "").strip()
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
    """Return the SPN from raw_data when the Supplier column matches this supplier.

    Returns the SPN value when ``raw_data['Supplier']`` matches the supplier's
    ``supplier_label`` (case-insensitive), empty string otherwise.
    """
    item_supplier = str(raw_data.get("Supplier", "")).strip().lower()
    if item_supplier == supplier.id or item_supplier == supplier.supplier_label.lower():
        return str(raw_data.get("SPN", "")).strip()
    return ""
