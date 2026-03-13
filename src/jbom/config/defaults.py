"""Defaults profile loader for jBOM component attribute configuration.

Loads *.defaults.yaml profiles from the search path defined in profile_search.
Supports 'extends: <name>' for single-value overrides without full file copies.

The defaults profile captures:
  - domain_defaults: Camp 2 electrical attribute defaults per component category
  - package_power / package_voltage: SMD package-level electrical defaults
  - parametric_query_fields: JLCPCB/LCSC spec fields per category (Phase 4)
  - category_route_rules: JLCPCB taxonomy routing (Phase 4)
  - enrichment_attributes: Camp 2/3 attribute classification per category (#99)
  - component_id_fields: optional ComponentID fields included per category

See docs/dev/architecture/component-attribute-enrichment.md for the design model.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from jbom.common.component_id import KNOWN_OPTIONAL_FIELD_NAMES
from jbom.config.profile_search import find_profile

log = logging.getLogger(__name__)

_BUILTIN_DIR = Path(__file__).parent / "defaults"
_ACTIVE_DEFAULTS_PROFILE = "generic"


def _normalize_field_synonym_canonical_key(canonical: str) -> str:
    """Normalize field-synonym canonical keys."""

    return str(canonical).strip().lower()


def _normalize_defaults_profile_name(name: str) -> str:
    """Normalize a defaults profile name, falling back to 'generic'."""

    normalized = str(name or "").strip()
    return normalized or "generic"


@dataclass(frozen=True)
class EnrichmentCategoryConfig:
    """Camp 2/3 attribute classification for one component category."""

    show_in_mode_a: tuple[str, ...]
    suppress: tuple[str, ...]


@dataclass(frozen=True)
class FieldSynonymConfig:
    """Canonical field naming plus accepted synonym headers."""

    display_name: str
    synonyms: tuple[str, ...]


@dataclass
class DefaultsConfig:
    """Loaded defaults profile.

    Contains domain defaults, package-level electrical defaults, JLCPCB
    parametric query shaping, and enrichment attribute classification (Camp 2/3).
    """

    name: str
    domain_defaults: dict[str, dict[str, str]] = field(default_factory=dict)
    package_power: dict[str, str] = field(default_factory=dict)
    package_voltage: dict[str, str] = field(default_factory=dict)
    parametric_query_fields: dict[str, list[str]] = field(default_factory=dict)
    category_route_rules: dict[str, dict[str, str]] = field(default_factory=dict)
    enrichment_attributes: dict[str, EnrichmentCategoryConfig] = field(
        default_factory=dict
    )
    field_synonyms: dict[str, FieldSynonymConfig] = field(default_factory=dict)
    search_output_fields_default: tuple[str, ...] = field(default_factory=tuple)
    search_excluded_categories: frozenset[str] = field(default_factory=frozenset)
    component_id_fields: dict[str, frozenset[str]] = field(default_factory=dict)

    @staticmethod
    def from_yaml_dict(data: dict[str, Any], *, name: str) -> "DefaultsConfig":
        """Parse a DefaultsConfig from a resolved (extends-merged) YAML dict.

        Args:
            data: Merged YAML mapping (extends chain already resolved).
            name: Profile name for identification.

        Returns:
            Parsed DefaultsConfig.
        """
        domain_defaults: dict[str, dict[str, str]] = {}
        for category, attrs in (data.get("domain_defaults") or {}).items():
            if isinstance(attrs, dict):
                domain_defaults[str(category).lower()] = {
                    str(k): str(v) for k, v in attrs.items()
                }

        package_power: dict[str, str] = {
            str(k).upper(): str(v) for k, v in (data.get("package_power") or {}).items()
        }
        package_voltage: dict[str, str] = {
            str(k).upper(): str(v)
            for k, v in (data.get("package_voltage") or {}).items()
        }

        parametric_query_fields: dict[str, list[str]] = {}
        for category, fields_list in (
            data.get("parametric_query_fields") or {}
        ).items():
            if isinstance(fields_list, list):
                parametric_query_fields[str(category).lower()] = [
                    str(f) for f in fields_list
                ]

        category_route_rules: dict[str, dict[str, str]] = {}
        for category, rules in (data.get("category_route_rules") or {}).items():
            if isinstance(rules, dict):
                category_route_rules[str(category).lower()] = {
                    str(k): str(v) for k, v in rules.items()
                }

        enrichment_attributes: dict[str, EnrichmentCategoryConfig] = {}
        for category, cfg in (data.get("enrichment_attributes") or {}).items():
            if isinstance(cfg, dict):
                show = tuple(str(f) for f in (cfg.get("show_in_mode_a") or []))
                suppress = tuple(str(f) for f in (cfg.get("suppress") or []))
                enrichment_attributes[str(category).lower()] = EnrichmentCategoryConfig(
                    show_in_mode_a=show,
                    suppress=suppress,
                )

        field_synonyms: dict[str, FieldSynonymConfig] = {}
        for canonical, cfg in (data.get("field_synonyms") or {}).items():
            if not isinstance(cfg, dict):
                continue
            display_name = str(cfg.get("display_name") or canonical).strip()
            synonyms_cfg = cfg.get("synonyms") or []
            if isinstance(synonyms_cfg, list):
                synonyms = tuple(str(s).strip() for s in synonyms_cfg if str(s).strip())
            else:
                synonyms = tuple()
            canonical_key = _normalize_field_synonym_canonical_key(canonical)

            existing = field_synonyms.get(canonical_key)
            if existing is not None:
                merged_synonyms = tuple(
                    dict.fromkeys([*existing.synonyms, *synonyms]).keys()
                )
                field_synonyms[canonical_key] = FieldSynonymConfig(
                    display_name=existing.display_name or display_name or canonical_key,
                    synonyms=merged_synonyms,
                )
            else:
                field_synonyms[canonical_key] = FieldSynonymConfig(
                    display_name=display_name or canonical_key,
                    synonyms=synonyms,
                )

        search_cfg = data.get("search") or {}
        search_output_fields_default: tuple[str, ...] = tuple()
        if isinstance(search_cfg, dict):
            output_fields_cfg = search_cfg.get("output_fields") or {}
            if isinstance(output_fields_cfg, dict):
                default_output_fields = output_fields_cfg.get("default") or []
                if isinstance(default_output_fields, list):
                    normalized_fields: list[str] = []
                    for field_name in default_output_fields:
                        normalized = str(field_name).strip().lower()
                        if normalized:
                            normalized_fields.append(normalized)
                    search_output_fields_default = tuple(
                        dict.fromkeys(normalized_fields).keys()
                    )
                else:
                    log.warning(
                        "search.output_fields.default must be a list; found %r",
                        type(default_output_fields).__name__,
                    )
            else:
                log.warning(
                    "search.output_fields must be a mapping; found %r",
                    type(output_fields_cfg).__name__,
                )
        else:
            log.warning(
                "search must be a mapping; found %r",
                type(search_cfg).__name__,
            )

        raw_excluded = data.get("search_excluded_categories") or []
        search_excluded_categories: frozenset[str] = frozenset(
            str(c).upper().strip() for c in raw_excluded if str(c).strip()
        )

        component_id_fields: dict[str, frozenset[str]] = {}
        for category, fields_list in (data.get("component_id_fields") or {}).items():
            if not isinstance(fields_list, list):
                continue
            validated: list[str] = []
            for fname in fields_list:
                fname_str = str(fname).strip().lower()
                if fname_str in KNOWN_OPTIONAL_FIELD_NAMES:
                    validated.append(fname_str)
                else:
                    log.warning(
                        "component_id_fields[%r]: unknown field name %r "
                        "(valid names: %s)",
                        category,
                        fname_str,
                        ", ".join(sorted(KNOWN_OPTIONAL_FIELD_NAMES)),
                    )
            component_id_fields[str(category).lower()] = frozenset(validated)

        return DefaultsConfig(
            name=name,
            domain_defaults=domain_defaults,
            package_power=package_power,
            package_voltage=package_voltage,
            parametric_query_fields=parametric_query_fields,
            category_route_rules=category_route_rules,
            enrichment_attributes=enrichment_attributes,
            field_synonyms=field_synonyms,
            search_output_fields_default=search_output_fields_default,
            search_excluded_categories=search_excluded_categories,
            component_id_fields=component_id_fields,
        )

    def get_domain_default(
        self, category: str, attribute: str, *, fallback: str = ""
    ) -> str:
        """Return the domain default for a category/attribute pair.

        Args:
            category: Normalized component category (e.g. 'resistor').
            attribute: Attribute name (e.g. 'tolerance').
            fallback: Value to return when no default is configured.
        """
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
        return self.field_synonyms.get(canonical.strip().lower())

    def get_search_excluded_categories(self) -> frozenset[str]:
        """Return the set of component categories excluded from supplier search."""

        return self.search_excluded_categories

    def get_search_output_fields_default(self) -> list[str]:
        """Return default search output fields from the active defaults profile."""

        return list(self.search_output_fields_default)

    def get_component_id_fields(self, category: str) -> frozenset[str] | None:
        """Return the optional-field allowlist for *category*, or ``None``.

        ``None`` means the category is not configured — the caller should fall
        back to including all optional fields (conservative / backward-compatible).

        Args:
            category: Component category token, any case (e.g. ``"LED"``,
                ``"res"``, ``"Cap"``).

        Returns:
            A ``frozenset`` of ``profile_name`` strings (e.g.
            ``frozenset({"type"})``) when the category is explicitly configured,
            or ``None`` when it is not.
        """
        return self.component_id_fields.get(category.lower())


def load_defaults(name: str, *, cwd: Path | None = None) -> DefaultsConfig:
    """Load a named defaults profile from the search path.

    Args:
        name: Profile name (e.g. 'generic', 'aerospace').
        cwd: Working directory for project-local search.

    Returns:
        Parsed DefaultsConfig.

    Raises:
        ValueError: If the profile is not found anywhere in the search path.
    """
    data = _load_yaml_resolved(name, cwd=cwd)
    return DefaultsConfig.from_yaml_dict(data, name=name)


def get_defaults(name: str | None = None, *, cwd: Path | None = None) -> DefaultsConfig:
    """Load a defaults profile, returning built-in generic on any error.

    Safe wrapper for callers that must not fail (e.g. query building).

    Args:
        name: Profile name to load. When omitted, uses the active profile.
        cwd: Working directory for project-local search.
    """
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
    """Load YAML for a profile, recursively resolving 'extends:' chains.

    Merge semantics:
    - Dict sections: deep-merged (child keys override parent, recursively)
    - List sections: replaced entirely by child (not appended)
    """
    path = find_profile(name, "defaults", cwd=cwd, builtin_dir=_BUILTIN_DIR)
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


def _load_builtin_generic() -> DefaultsConfig:
    """Load the built-in generic profile directly (no search path)."""
    path = _BUILTIN_DIR / "generic.defaults.yaml"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return DefaultsConfig.from_yaml_dict(data, name="generic")


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge override onto base.

    - Dict values: merged recursively (child keys overlay parent)
    - All other values (including lists): child replaces parent entirely
    """
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


__all__ = [
    "DefaultsConfig",
    "EnrichmentCategoryConfig",
    "FieldSynonymConfig",
    "get_active_defaults_profile",
    "get_defaults",
    "load_defaults",
    "set_active_defaults_profile",
]
