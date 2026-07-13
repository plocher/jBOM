"""Defaults profile loader for jBOM component attribute configuration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    ValidationInfo,
    computed_field,
    field_validator,
    model_validator,
)

from jbom.common.component_id import KNOWN_OPTIONAL_FIELD_NAMES
from jbom.config.field_synonyms import FieldSynonym, parse_field_synonyms
from jbom.config.profile_search import profile_search_dirs
from jbom.config.unified import (
    UnifiedProfileNotFoundError,
    defaults_stanza,
    load_unified,
    resolve_profile_name_for_stanza_id,
)

log = logging.getLogger(__name__)

_BUILTIN_DIR = Path(__file__).parent / "defaults"
_ACTIVE_DEFAULTS_PROFILE = "generic"


def _normalize_field_synonym_canonical_key(canonical: str) -> str:
    """Normalize field-synonym canonical keys."""

    return str(canonical).strip().lower()


def _normalize_defaults_profile_name(name: str) -> str:
    """Normalize a defaults profile name, falling back to 'generic'."""

    normalized = str(name or "").strip().lower()
    return normalized or "generic"


class EnrichmentCategoryConfig(BaseModel):
    """Camp 2/3 attribute classification for one component category."""

    model_config = ConfigDict(extra="ignore")

    show_in_mode_a: tuple[str, ...] = Field(default_factory=tuple)
    suppress: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("show_in_mode_a", "suppress", mode="before")
    @classmethod
    def _normalize_attribute_lists(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return tuple()
        if not isinstance(value, (list, tuple)):
            return tuple()
        return tuple(str(item).strip() for item in value if str(item).strip())


FieldSynonymConfig = FieldSynonym


class InventorySchemaConfig(BaseModel):
    """Canonical inventory overlay schema and source-field bindings."""

    model_config = ConfigDict(extra="ignore")

    canonical_fields: tuple[str, ...]
    field_synonyms: dict[str, FieldSynonym] = Field(default_factory=dict)
    enrichment_bindings: dict[str, str] = Field(default_factory=dict)

    @field_validator("canonical_fields", mode="before")
    @classmethod
    def _normalize_canonical_fields(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return tuple()
        if not isinstance(value, (list, tuple)):
            return tuple()
        normalized: list[str] = []
        for field_name in value:
            token = str(field_name or "").strip().lower()
            if token:
                normalized.append(token)
        return tuple(dict.fromkeys(normalized).keys())

    @field_validator("enrichment_bindings", mode="before")
    @classmethod
    def _normalize_enrichment_bindings(cls, value: Any) -> dict[str, str]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            return {}
        out: dict[str, str] = {}
        for raw_canonical, raw_source in value.items():
            canonical_key = str(raw_canonical or "").strip().lower()
            source_key = str(raw_source or "").strip()
            if canonical_key and source_key:
                out[canonical_key] = source_key
        return out

    @staticmethod
    def default() -> "InventorySchemaConfig":
        """Return the built-in canonical inventory schema contract."""

        return InventorySchemaConfig.model_validate(
            {
                "canonical_fields": [
                    "inventory_ipn",
                    "manufacturer",
                    "manufacturer_part",
                    "description",
                    "datasheet",
                    "supplier",
                    "spn",
                    "tolerance",
                    "voltage",
                    "wattage",
                    "package",
                    "smd",
                    "fabricator_part_number",
                ],
                "field_synonyms": {
                    "inventory_ipn": {
                        "display_name": "IPN",
                        "synonyms": ["ipn"],
                    },
                    "manufacturer_part": {
                        "display_name": "Manufacturer Part Number",
                        "synonyms": ["mfgpn", "mpn", "manufacturer_part_number"],
                    },
                    "wattage": {
                        "display_name": "Power",
                        "synonyms": ["power"],
                    },
                    "fabricator_part_number": {
                        "display_name": "Fabricator Part Number",
                        "synonyms": ["fab_pn", "supplier_pn"],
                    },
                },
                "enrichment_bindings": {
                    "inventory_ipn": "ipn",
                    "manufacturer": "manufacturer",
                    "manufacturer_part": "mfgpn",
                    "description": "description",
                    "datasheet": "datasheet",
                    "supplier": "supplier",
                    "spn": "spn",
                    "tolerance": "tolerance",
                    "voltage": "voltage",
                    "wattage": "wattage",
                    "package": "package",
                    "smd": "smd",
                    "fabricator_part_number": "__resolved_fabricator_part_number__",
                },
            }
        )


class DefaultsSearchOutputFieldsConfig(BaseModel):
    """Search output field configuration section."""

    model_config = ConfigDict(extra="ignore")

    default: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("default", mode="before")
    @classmethod
    def _normalize_default_output_fields(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return tuple()
        if not isinstance(value, list):
            return tuple()
        normalized: list[str] = []
        for field_name in value:
            token = str(field_name).strip().lower()
            if token:
                normalized.append(token)
        return tuple(dict.fromkeys(normalized).keys())


class DefaultsSearchConfig(BaseModel):
    """Defaults profile `search:` stanza."""

    model_config = ConfigDict(extra="ignore")

    output_fields: DefaultsSearchOutputFieldsConfig = Field(
        default_factory=DefaultsSearchOutputFieldsConfig
    )
    package_tokens: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("package_tokens", mode="before")
    @classmethod
    def _normalize_package_tokens(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return tuple()
        if not isinstance(value, list):
            return tuple()
        normalized: list[str] = []
        for token in value:
            package = str(token).strip().upper()
            if package:
                normalized.append(package)
        return tuple(dict.fromkeys(normalized).keys())


class DatasheetStagingConfig(BaseModel):
    """Defaults profile ``datasheet_staging:`` stanza (jBOM#355).

    Governs the always-on staging fetch that rides ``jbom search`` and
    ``jbom inventory --supplier``. See ``docs/reference/configuration.md``
    for the full write-up.

    Per jBOM convention, business-meaningful defaults are declared in the
    ``generic.jbom.yaml`` profile (``max_fetches_per_run``,
    ``fetch_time_budget_seconds``), not hardcoded here -- the Python-level
    fallbacks below are structurally neutral ("unconfigured"), reachable
    only if profile loading fails entirely. ``staging_dir`` is a
    user-machine binding (it names a local SPCoast-inventory checkout) and
    is deliberately never declared in the shipped ``generic.jbom.yaml``;
    users set it in their own ``~/.jbom/common.jbom.yaml``.
    """

    model_config = ConfigDict(extra="ignore")

    staging_dir: str = ""
    max_fetches_per_run: int = 0
    fetch_time_budget_seconds: float = 0.0
    # Test-only escape hatch: when non-empty, default_fetch() resolves URLs
    # against a local ``{url: file_path}`` JSON manifest instead of the
    # network. Never set this in a production profile.
    fetch_fixtures_manifest: str = ""

    @field_validator("staging_dir", "fetch_fixtures_manifest", mode="before")
    @classmethod
    def _normalize_optional_path_strings(cls, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @field_validator("max_fetches_per_run", mode="before")
    @classmethod
    def _validate_max_fetches_per_run(cls, value: Any) -> int:
        if value is None:
            return 0
        return max(0, int(value))

    @field_validator("fetch_time_budget_seconds", mode="before")
    @classmethod
    def _validate_fetch_time_budget_seconds(cls, value: Any) -> float:
        if value is None:
            return 0.0
        return max(0.0, float(value))


class DefaultsConfig(BaseModel):
    """Loaded defaults profile."""

    model_config = ConfigDict(extra="ignore")

    domain_defaults: dict[str, dict[str, str]] = Field(default_factory=dict)
    package_power: dict[str, str] = Field(default_factory=dict)
    package_voltage: dict[str, str] = Field(default_factory=dict)
    parametric_query_fields: dict[str, list[str]] = Field(default_factory=dict)
    category_route_rules: dict[str, dict[str, str]] = Field(default_factory=dict)
    enrichment_attributes: dict[str, EnrichmentCategoryConfig] = Field(
        default_factory=dict
    )
    field_synonyms: dict[str, FieldSynonym] = Field(default_factory=dict)
    inventory_schema: InventorySchemaConfig = Field(
        default_factory=InventorySchemaConfig.default
    )
    search: DefaultsSearchConfig = Field(default_factory=DefaultsSearchConfig)
    datasheet_staging: DatasheetStagingConfig = Field(
        default_factory=DatasheetStagingConfig
    )
    search_excluded_categories: frozenset[str] = Field(default_factory=frozenset)
    component_id_fields: dict[str, frozenset[str]] = Field(default_factory=dict)
    field_precedence_policy: dict[str, tuple[str, ...]] = Field(default_factory=dict)

    _profile_name: str = PrivateAttr(default="generic")

    @model_validator(mode="after")
    def _set_profile_name(self, info: ValidationInfo) -> "DefaultsConfig":
        profile_name = "generic"
        if isinstance(info.context, dict):
            profile_name = _normalize_defaults_profile_name(
                str(info.context.get("profile_name", "generic"))
            )
        self._profile_name = profile_name
        return self

    @computed_field
    @property
    def name(self) -> str:
        """Profile name resolved from load context."""

        return self._profile_name

    @field_validator("domain_defaults", mode="before")
    @classmethod
    def _normalize_domain_defaults(cls, value: Any) -> dict[str, dict[str, str]]:
        if value is None or not isinstance(value, dict):
            return {}
        normalized: dict[str, dict[str, str]] = {}
        for category, attrs in value.items():
            if isinstance(attrs, dict):
                normalized[str(category).lower()] = {
                    str(key): str(val) for key, val in attrs.items()
                }
        return normalized

    @field_validator("package_power", "package_voltage", mode="before")
    @classmethod
    def _normalize_package_defaults(cls, value: Any) -> dict[str, str]:
        if value is None or not isinstance(value, dict):
            return {}
        return {str(key).upper(): str(val) for key, val in value.items()}

    @field_validator("parametric_query_fields", mode="before")
    @classmethod
    def _normalize_parametric_query_fields(cls, value: Any) -> dict[str, list[str]]:
        if value is None or not isinstance(value, dict):
            return {}
        normalized: dict[str, list[str]] = {}
        for category, fields_list in value.items():
            if isinstance(fields_list, list):
                normalized[str(category).lower()] = [
                    str(field_name) for field_name in fields_list
                ]
        return normalized

    @field_validator("category_route_rules", mode="before")
    @classmethod
    def _normalize_category_route_rules(cls, value: Any) -> dict[str, dict[str, str]]:
        if value is None or not isinstance(value, dict):
            return {}
        normalized: dict[str, dict[str, str]] = {}
        for category, rules in value.items():
            if isinstance(rules, dict):
                normalized[str(category).lower()] = {
                    str(key): str(val) for key, val in rules.items()
                }
        return normalized

    @field_validator("enrichment_attributes", mode="before")
    @classmethod
    def _normalize_enrichment_attributes(
        cls, value: Any
    ) -> dict[str, EnrichmentCategoryConfig]:
        if value is None or not isinstance(value, dict):
            return {}
        normalized: dict[str, EnrichmentCategoryConfig] = {}
        for category, cfg in value.items():
            if isinstance(cfg, dict):
                normalized[
                    str(category).lower()
                ] = EnrichmentCategoryConfig.model_validate(cfg)
        return normalized

    @field_validator("field_synonyms", mode="before")
    @classmethod
    def _parse_field_synonyms(cls, value: Any) -> dict[str, FieldSynonym]:
        return parse_field_synonyms(
            value,
            context="field_synonyms",
            strict=False,
            default_display_name_from_key=True,
            normalize_canonical_key=_normalize_field_synonym_canonical_key,
            logger=log,
        )

    @field_validator("inventory_schema", mode="before")
    @classmethod
    def _parse_inventory_schema(cls, value: Any) -> InventorySchemaConfig:
        default_schema = InventorySchemaConfig.default()
        if value is None:
            return default_schema
        if isinstance(value, InventorySchemaConfig):
            return value
        if not isinstance(value, dict):
            log.warning(
                "inventory_schema must be a mapping; found %r",
                type(value).__name__,
            )
            return default_schema

        canonical_fields_cfg = value.get("canonical_fields")
        parsed_canonical_fields = list(default_schema.canonical_fields)
        if isinstance(canonical_fields_cfg, list):
            normalized_canonical: list[str] = []
            for field_name in canonical_fields_cfg:
                token = str(field_name or "").strip().lower()
                if token:
                    normalized_canonical.append(token)
            if normalized_canonical:
                parsed_canonical_fields = list(
                    dict.fromkeys(normalized_canonical).keys()
                )
        elif canonical_fields_cfg is not None:
            log.warning(
                "inventory_schema.canonical_fields must be a list; found %r",
                type(canonical_fields_cfg).__name__,
            )

        parsed_schema_field_synonyms = parse_field_synonyms(
            value.get("field_synonyms"),
            context="inventory_schema.field_synonyms",
            strict=False,
            default_display_name_from_key=True,
            normalize_canonical_key=_normalize_field_synonym_canonical_key,
            logger=log,
        )
        if parsed_schema_field_synonyms:
            schema_field_synonyms = parsed_schema_field_synonyms
        else:
            schema_field_synonyms = dict(default_schema.field_synonyms)

        bindings_cfg = value.get("enrichment_bindings")
        parsed_bindings = dict(default_schema.enrichment_bindings)
        if isinstance(bindings_cfg, dict):
            parsed_bindings = {}
            for raw_canonical, raw_source in bindings_cfg.items():
                canonical_key = str(raw_canonical or "").strip().lower()
                source_key = str(raw_source or "").strip()
                if canonical_key and source_key:
                    parsed_bindings[canonical_key] = source_key
        elif bindings_cfg is not None:
            log.warning(
                "inventory_schema.enrichment_bindings must be a mapping; found %r",
                type(bindings_cfg).__name__,
            )

        for canonical_key in schema_field_synonyms.keys():
            if canonical_key not in parsed_canonical_fields:
                parsed_canonical_fields.append(canonical_key)
        for canonical_key in parsed_bindings.keys():
            if canonical_key not in parsed_canonical_fields:
                parsed_canonical_fields.append(canonical_key)

        return InventorySchemaConfig.model_validate(
            {
                "canonical_fields": parsed_canonical_fields,
                "field_synonyms": schema_field_synonyms,
                "enrichment_bindings": parsed_bindings,
            }
        )

    @field_validator("search", mode="before")
    @classmethod
    def _parse_search_config(cls, value: Any) -> DefaultsSearchConfig:
        if value is None:
            return DefaultsSearchConfig()
        if isinstance(value, DefaultsSearchConfig):
            return value
        if not isinstance(value, dict):
            log.warning("search must be a mapping; found %r", type(value).__name__)
            return DefaultsSearchConfig()
        return DefaultsSearchConfig.model_validate(value)

    @field_validator("datasheet_staging", mode="before")
    @classmethod
    def _parse_datasheet_staging_config(cls, value: Any) -> DatasheetStagingConfig:
        if value is None:
            return DatasheetStagingConfig()
        if isinstance(value, DatasheetStagingConfig):
            return value
        if not isinstance(value, dict):
            log.warning(
                "datasheet_staging must be a mapping; found %r", type(value).__name__
            )
            return DatasheetStagingConfig()
        return DatasheetStagingConfig.model_validate(value)

    @field_validator("search_excluded_categories", mode="before")
    @classmethod
    def _normalize_search_excluded_categories(cls, value: Any) -> frozenset[str]:
        if value is None or not isinstance(value, list):
            return frozenset()
        return frozenset(
            str(category).upper().strip() for category in value if str(category).strip()
        )

    @field_validator("component_id_fields", mode="before")
    @classmethod
    def _normalize_component_id_fields(cls, value: Any) -> dict[str, frozenset[str]]:
        if value is None or not isinstance(value, dict):
            return {}

        normalized: dict[str, frozenset[str]] = {}
        for category, fields_list in value.items():
            if not isinstance(fields_list, list):
                continue

            validated: list[str] = []
            for field_name in fields_list:
                token = str(field_name).strip().lower()
                if token in KNOWN_OPTIONAL_FIELD_NAMES:
                    validated.append(token)
                else:
                    log.warning(
                        "component_id_fields[%r]: unknown field name %r (valid names: %s)",
                        category,
                        token,
                        ", ".join(sorted(KNOWN_OPTIONAL_FIELD_NAMES)),
                    )
            normalized[str(category).lower()] = frozenset(validated)

        return normalized

    @field_validator("field_precedence_policy", mode="before")
    @classmethod
    def _normalize_field_precedence_policy(
        cls, value: Any
    ) -> dict[str, tuple[str, ...]]:
        if value is None or not isinstance(value, dict):
            return {}

        normalized_policy: dict[str, tuple[str, ...]] = {}
        for policy_key, raw_fields in value.items():
            normalized_key = str(policy_key or "").strip().lower()
            if not normalized_key:
                continue
            if not isinstance(raw_fields, list):
                log.warning(
                    "field_precedence_policy[%r] must be a list; found %r",
                    normalized_key,
                    type(raw_fields).__name__,
                )
                continue
            normalized_fields: list[str] = []
            for field_name in raw_fields:
                token = str(field_name or "").strip().lower()
                if token:
                    normalized_fields.append(token)
            normalized_policy[normalized_key] = tuple(
                dict.fromkeys(normalized_fields).keys()
            )

        return normalized_policy

    def get_domain_default(
        self, category: str, attribute: str, *, fallback: str = ""
    ) -> str:
        """Return the domain default for a category/attribute pair."""

        return self.domain_defaults.get(category.lower(), {}).get(attribute, fallback)

    def get_package_power(self, package: str) -> str:
        """Return the default power rating for an SMD package, or ''."""

        return self.package_power.get(package.upper(), "")

    def get_package_voltage(self, package: str) -> str:
        """Return the default voltage rating for an SMD package, or ''."""

        return self.package_voltage.get(package.upper(), "")

    def get_parametric_query_fields(self, category: str) -> list[str]:
        """Return the ordered list of parametric query fields for a category."""

        return list(self.parametric_query_fields.get(category.lower(), []))

    def get_category_route_rules(self, category: str) -> dict[str, str]:
        """Return the JLCPCB taxonomy routing rules for a category."""

        return dict(self.category_route_rules.get(category.lower(), {}))

    def get_field_synonym_config(self, canonical: str) -> FieldSynonymConfig | None:
        """Return field synonym config for a canonical key."""

        return self.field_synonyms.get(
            _normalize_field_synonym_canonical_key(canonical)
        )

    def get_inventory_schema(self) -> InventorySchemaConfig:
        """Return canonical inventory schema config for overlay/matcher workflows."""

        return InventorySchemaConfig.model_validate(self.inventory_schema.model_dump())

    def get_search_excluded_categories(self) -> frozenset[str]:
        """Return the set of component categories excluded from supplier search."""

        return self.search_excluded_categories

    def get_search_output_fields_default(self) -> list[str]:
        """Return default search output fields from the active defaults profile."""

        return list(self.search.output_fields.default)

    def get_search_package_tokens(self) -> list[str]:
        """Return configured package tokens used for search package intent signals."""

        return list(self.search.package_tokens)

    def get_component_id_fields(self, category: str) -> frozenset[str] | None:
        """Return the optional-field allowlist for *category*, or ``None``."""

        return self.component_id_fields.get(category.lower())

    def get_field_precedence_policy(self) -> dict[str, tuple[str, ...]]:
        """Return configured canonical field precedence policy entries."""

        return dict(self.field_precedence_policy)

    def get_datasheet_staging_config(self) -> DatasheetStagingConfig:
        """Return the datasheet staging fetch config (jBOM#355)."""

        return self.datasheet_staging


def load_defaults(name: str, *, cwd: Path | None = None) -> DefaultsConfig:
    """Load a named defaults profile from the search path."""
    normalized_name = _normalize_defaults_profile_name(name)
    try:
        merged = load_unified(normalized_name, cwd=cwd)
        return defaults_stanza(merged, default_id=normalized_name)
    except UnifiedProfileNotFoundError:
        mapped_profile_name = resolve_profile_name_for_stanza_id(
            "defaults", normalized_name, cwd=cwd
        )
        if mapped_profile_name:
            merged = load_unified(mapped_profile_name, cwd=cwd)
            return defaults_stanza(merged, default_id=normalized_name)
        data = _load_yaml_resolved(normalized_name, cwd=cwd)
        return DefaultsConfig.model_validate(
            data, context={"profile_name": normalized_name}
        )


def get_defaults(name: str | None = None, *, cwd: Path | None = None) -> DefaultsConfig:
    """Load a defaults profile, returning built-in generic on any error."""

    resolved_name = _normalize_defaults_profile_name(
        name if name is not None else _ACTIVE_DEFAULTS_PROFILE
    )
    try:
        return load_defaults(resolved_name, cwd=cwd)
    except Exception:
        log.warning(
            "Could not load defaults profile %r; using built-in generic", resolved_name
        )
        return _load_builtin_generic()


def get_active_defaults_profile() -> str:
    """Return the active defaults profile name used by get_defaults()."""

    return _ACTIVE_DEFAULTS_PROFILE


def set_active_defaults_profile(name: str) -> None:
    """Set the active defaults profile name used by get_defaults()."""

    global _ACTIVE_DEFAULTS_PROFILE
    _ACTIVE_DEFAULTS_PROFILE = _normalize_defaults_profile_name(name)


def _load_yaml_resolved(name: str, *, cwd: Path | None = None) -> dict[str, Any]:
    """Load YAML for a profile, recursively resolving 'extends:' chains."""
    path = _find_legacy_profile(name, suffix="defaults", cwd=cwd)
    if path is None:
        raise ValueError(
            f"Defaults profile not found: {name!r}. "
            f"Place {name}.defaults.yaml in a .jbom/ directory or $JBOM_PROFILE_PATH."
        )

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    if not isinstance(raw, dict):
        raise ValueError(f"Defaults profile '{name}' must be a YAML mapping")

    extends = raw.pop("extends", None)
    if isinstance(extends, str) and extends.strip():
        parent_data = _load_yaml_resolved(extends.strip(), cwd=cwd)
        raw = _deep_merge(parent_data, raw)

    return raw


def _find_legacy_profile(
    name: str, *, suffix: str, cwd: Path | None = None
) -> Path | None:
    filename = f"{name}.{suffix}.yaml"
    search_dirs = list(profile_search_dirs(cwd=cwd))
    search_dirs.append(_BUILTIN_DIR)
    for directory in search_dirs:
        candidate = directory / filename
        if candidate.is_file():
            return candidate
    return None


def _load_builtin_generic() -> DefaultsConfig:
    """Load the built-in generic profile directly (no search path)."""
    try:
        merged = load_unified("generic")
        return defaults_stanza(merged, default_id="generic")
    except Exception:
        # Legacy fallback retained for compatibility if a built-in
        # generic.defaults.yaml exists in older installations.
        path = _BUILTIN_DIR / "generic.defaults.yaml"
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return DefaultsConfig.model_validate(data, context={"profile_name": "generic"})


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge override onto base."""

    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


__all__ = [
    "DatasheetStagingConfig",
    "DefaultsConfig",
    "EnrichmentCategoryConfig",
    "FieldSynonymConfig",
    "InventorySchemaConfig",
    "get_active_defaults_profile",
    "get_defaults",
    "load_defaults",
    "set_active_defaults_profile",
]
