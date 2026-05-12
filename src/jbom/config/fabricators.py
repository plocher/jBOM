"""Fabricator configuration loader.

Loads fabricator definitions from built-in config files.
"""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

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

from jbom.common.synonym_normalization import normalize_synonym_token
from jbom.config.field_synonyms import FieldSynonym, parse_field_synonyms
from jbom.config.profile_search import profile_search_dirs
from jbom.config.suppliers import resolve_supplier_by_id
from jbom.config.unified import (
    UnifiedProfileNotFoundError,
    fab_stanza,
    list_unified_stanza_ids,
    load_unified,
    resolve_profile_name_for_stanza_id,
)

log = logging.getLogger(__name__)


class TierOperator(str, Enum):
    """Supported boolean operators for tier matching conditions."""

    EXISTS = "exists"
    TRUTHY = "truthy"
    EQUALS = "equals"
    NOT_EMPTY = "not_empty"


_SUPPORTED_TIER_OPERATORS = sorted(op.value for op in TierOperator)


class TierCondition(BaseModel):
    """One condition used to decide whether an inventory item belongs in a tier."""

    model_config = ConfigDict(extra="ignore")

    field: str
    operator: TierOperator
    value: Optional[str] = None

    @field_validator("field")
    @classmethod
    def _validate_field(cls, value: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("TierCondition.field must be a non-empty string")
        return normalized

    @field_validator("value", mode="before")
    @classmethod
    def _validate_value_type(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("TierCondition.value must be a string when provided")
        return value

    @model_validator(mode="after")
    def _validate_operator_constraints(self) -> "TierCondition":
        if self.operator is TierOperator.EQUALS and self.value is None:
            raise ValueError("equals operator requires 'value'")
        return self

    def matches(self, raw_data: Mapping[str, str]) -> bool:
        """Return True if this condition matches against the provided raw data."""

        field_value = str(raw_data.get(self.field, ""))

        if self.operator is TierOperator.EXISTS:
            return bool(field_value)

        if self.operator is TierOperator.NOT_EMPTY:
            return bool(field_value.strip())

        if self.operator is TierOperator.EQUALS:
            return field_value == (self.value or "")

        if self.operator is TierOperator.TRUTHY:
            return _is_truthy(field_value)

        raise AssertionError(f"Unhandled operator: {self.operator!r}")


class TierRule(BaseModel):
    """A set of conditions used to assign an item to a preference tier.

    All conditions must match (AND semantics).
    """

    model_config = ConfigDict(extra="ignore")

    conditions: list[TierCondition] = Field(default_factory=list)

    def matches(self, raw_data: Mapping[str, str]) -> bool:
        """Return True if all conditions match.

        An empty condition list matches everything.
        """

        return all(condition.matches(raw_data) for condition in self.conditions)


def _is_truthy(value: str) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return False

    # Common spreadsheet/csv truthy values.
    return normalized in {"1", "true", "t", "yes", "y", "x"}


class FabricatorConfig(BaseModel):
    """Configuration for a PCB fabricator.

    Defines column mappings, part number preferences, presets, and CLI aliases
    for fabricator-specific BOM and position file generation.
    """

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    pos_columns: Dict[str, str]  # Header -> internal field mapping
    pos_additive_default_fields: Optional[List[str]] = None
    cpl_rotation_range: Optional[tuple[float, float]] = None  # (lo, hi)
    generate_designators: bool = False

    # Phase 1 schema: ordered supplier profile IDs.
    # Position encodes priority (first entry is most preferred).
    suppliers: list[str] = Field(default_factory=list)

    # Phase 2 schema: field synonyms + ordered tier overrides.
    field_synonyms: Dict[str, FieldSynonym] = Field(default_factory=dict)
    tier_overrides: list[TierRule] = Field(default_factory=list)

    description: Optional[str] = None
    bom_columns: Optional[Dict[str, str]] = None
    part_number: Optional[Dict[str, Any]] = None
    presets: Optional[Dict[str, Any]] = None
    cli_aliases: Optional[Dict[str, List[str]]] = None
    pcb_manufacturing: Optional[Dict[str, Any]] = None
    pcb_assembly: Optional[Dict[str, Any]] = None
    website: Optional[str] = None
    gerbers: Optional[Dict[str, Any]] = None
    dynamic_name: bool = False
    name_source: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_input(cls, raw: Any, info: ValidationInfo) -> Dict[str, Any]:
        if not isinstance(raw, dict):
            raise ValueError("Fabricator config must be a YAML mapping")

        data = dict(raw)

        default_id = ""
        if isinstance(info.context, dict):
            default_id = str(info.context.get("default_id", "")).strip()

        if "id" not in data and default_id:
            data["id"] = default_id
        if "name" not in data and default_id:
            data["name"] = default_id

        if "tier_rules" in data:
            raise ValueError(
                "tier_rules is no longer supported in fab YAMLs; "
                "use derived base tiers + tier_overrides"
            )

        part_number = data.get("part_number")
        if isinstance(part_number, dict) and "priority_fields" in part_number:
            raise ValueError(
                "Fabricator config uses deprecated part_number.priority_fields. "
                "Migrate to 'field_synonyms' + derived tiers."
            )

        return data

    @field_validator("id", "name")
    @classmethod
    def _validate_required_string_fields(cls, value: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("id/name must be non-empty strings")
        return normalized

    @field_validator("pos_columns", mode="before")
    @classmethod
    def _validate_pos_columns(cls, value: Any) -> Dict[str, str]:
        if not isinstance(value, dict) or not value:
            raise ValueError("Fabricator missing pos_columns")
        normalized: Dict[str, str] = {}
        for header, field_name in value.items():
            key = str(header or "").strip()
            mapped = str(field_name or "").strip()
            if not key or not mapped:
                raise ValueError(
                    "pos_columns must map non-empty strings to non-empty strings"
                )
            normalized[key] = mapped
        return normalized

    @field_validator("pos_additive_default_fields", mode="before")
    @classmethod
    def _validate_pos_additive_default_fields(cls, value: Any) -> Optional[List[str]]:
        if value is None:
            return None
        if not isinstance(value, list):
            raise ValueError(
                "pos_additive_default_fields must be a list of non-empty strings"
            )
        normalized: List[str] = []
        for field_name in value:
            token = str(field_name or "").strip()
            if not token:
                raise ValueError(
                    "pos_additive_default_fields must be a list of non-empty strings"
                )
            normalized.append(token)
        return normalized

    @field_validator("suppliers", mode="before")
    @classmethod
    def _validate_suppliers(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("suppliers must be a list")

        suppliers: list[str] = []
        for raw_sid in value:
            sid = str(raw_sid or "").strip().lower()
            if not sid:
                raise ValueError("suppliers entries must be non-empty strings")
            suppliers.append(sid)

        return suppliers

    @field_validator("field_synonyms", mode="before")
    @classmethod
    def _parse_field_synonyms(cls, value: Any) -> Dict[str, FieldSynonym]:
        return parse_field_synonyms(
            value,
            context="field_synonyms",
            strict=True,
            default_display_name_from_key=False,
            normalize_canonical_key=lambda key: key.strip(),
        )

    @field_validator("cpl_rotation_range", mode="before")
    @classmethod
    def _validate_cpl_rotation_range(cls, value: Any) -> Optional[tuple[float, float]]:
        if value is None:
            return None
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ValueError(
                "cpl_rotation_range must be a two-element list spanning exactly 360° "
                "— e.g. [0, 360] or [-180, 180]"
            )

        lo = float(value[0])
        hi = float(value[1])
        if hi - lo != 360:
            raise ValueError(
                "cpl_rotation_range must be a two-element list spanning exactly 360° "
                "— e.g. [0, 360] or [-180, 180]"
            )
        return (lo, hi)

    @model_validator(mode="after")
    def _validate_relationships(self) -> "FabricatorConfig":
        if not self.suppliers:
            raise ValueError(
                f"Fabricator '{self.id}' must declare a non-empty suppliers list"
            )

        for sid in self.suppliers:
            if resolve_supplier_by_id(sid) is None:
                raise ValueError(
                    f"Unknown supplier profile id {sid!r} referenced by fabricator {self.id!r}"
                )

        self.field_synonyms = _derive_part_number_field_synonyms(
            field_synonyms=self.field_synonyms, suppliers=self.suppliers
        )
        required_fields = {"fab_pn", "supplier_pn", "mpn"}
        missing_fields = required_fields - set(self.field_synonyms.keys())
        if missing_fields:
            raise ValueError(
                f"Fabricator '{self.id}' missing required field_synonyms entries: "
                f"{sorted(missing_fields)}"
            )

        return self

    @computed_field
    @property
    def tier_rules(self) -> list[TierRule]:
        """Derived ordered tier rules: overrides first, base tiers appended."""

        return _derive_tier_rules(tier_overrides=self.tier_overrides)

    def resolve_field_synonym(self, field_name: str) -> Optional[str]:
        """Resolve a field name variant to its canonical name.

        Matching is forgiving (case-insensitive, ignores surrounding whitespace).
        Returns None when the field name is unknown.
        """

        field_normalized = normalize_synonym_token(field_name)

        for canonical, config in self.field_synonyms.items():
            if normalize_synonym_token(canonical) == field_normalized:
                return canonical

            for synonym in config.synonyms:
                if normalize_synonym_token(synonym) == field_normalized:
                    return canonical

        return None

    def normalize_header_to_display_name(self, raw_header: str) -> str:
        """Rewrite a raw bom_columns key through field_synonyms to its display_name.

        This is the output-side counterpart of :meth:`resolve_field_synonym`.
        If ``raw_header`` is a recognised synonym (e.g. ``"LCSC"``), it is
        replaced by the canonical display_name (e.g. ``"LCSC Part #"``).
        Otherwise the raw header is returned unchanged.
        """

        canonical = self.resolve_field_synonym(raw_header)
        if canonical and canonical in self.field_synonyms:
            return self.field_synonyms[canonical].display_name
        return raw_header


def _derive_part_number_field_synonyms(
    *,
    field_synonyms: Dict[str, FieldSynonym],
    suppliers: list[str],
) -> Dict[str, FieldSynonym]:
    """Return field_synonyms with validated fab_pn/supplier_pn entries.

    With the normalized Supplier/SPN schema, part-number resolution happens
    via InventoryItem.supplier + InventoryItem.spn at runtime, not via
    CSV column-name synonyms.
    """

    if not suppliers:
        raise ValueError("Cannot derive part-number field synonyms without suppliers")

    for sid in suppliers:
        if resolve_supplier_by_id(sid) is None:
            raise ValueError(f"Unknown supplier profile id: {sid!r}")

    return dict(field_synonyms)


def _derive_tier_rules(*, tier_overrides: list[TierRule]) -> list[TierRule]:
    """Derive ordered tier rules from ordered overrides + base rules."""

    return [
        *tier_overrides,
        TierRule(
            conditions=[
                TierCondition(field="fab_pn", operator=TierOperator.EXISTS),
            ]
        ),
        TierRule(
            conditions=[
                TierCondition(field="supplier_pn", operator=TierOperator.EXISTS),
            ]
        ),
        TierRule(
            conditions=[
                TierCondition(field="mpn", operator=TierOperator.EXISTS),
            ]
        ),
    ]


_BUILTIN_DIR = Path(__file__).parent / "fabricators"


def list_fabricators() -> list[str]:
    """List available fabricator IDs by scanning config directory."""
    legacy_ids: list[str] = []
    if _BUILTIN_DIR.exists():
        legacy_ids = sorted(
            p.stem.replace(".fab", "") for p in _BUILTIN_DIR.glob("*.fab.yaml")
        )
    unified_ids = list_unified_stanza_ids("fab")
    return sorted(set([*legacy_ids, *unified_ids]))


def get_available_fabricators() -> list[str]:
    """Get list of available fabricators with fallback for consistency."""

    fabricators = list_fabricators()
    return fabricators if fabricators else ["generic"]


def get_fabricators_with_names() -> list[tuple[str, str]]:
    """Return (id, display_name) pairs for all available fabricators."""

    result: list[tuple[str, str]] = []
    for fid in get_available_fabricators():
        try:
            display_name = load_fabricator(fid).name
        except (ValueError, Exception):
            display_name = fid.upper() if len(fid) <= 4 else fid.title()
        result.append((fid, display_name))
    return result


def load_fabricator(fid: str) -> FabricatorConfig:
    """Load fabricator configuration from YAML file."""
    normalized_fid = str(fid or "").strip().lower()

    try:
        merged = load_unified(normalized_fid)
        return fab_stanza(merged, default_id=normalized_fid)
    except UnifiedProfileNotFoundError:
        mapped_profile_name = resolve_profile_name_for_stanza_id("fab", normalized_fid)
        if mapped_profile_name:
            merged = load_unified(mapped_profile_name)
            return fab_stanza(merged, default_id=normalized_fid)
        path = _find_legacy_profile(normalized_fid, suffix="fab")
        if path is None:
            raise ValueError(f"Unknown fabricator: {normalized_fid}") from None

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return FabricatorConfig.model_validate(
            data, context={"default_id": normalized_fid}
        )


def _find_legacy_profile(name: str, *, suffix: str) -> Path | None:
    filename = f"{name}.{suffix}.yaml"
    search_dirs = list(profile_search_dirs())
    search_dirs.append(_BUILTIN_DIR)
    for directory in search_dirs:
        candidate = directory / filename
        if candidate.is_file():
            return candidate
    return None


def headers_for_fields(fab: Optional[FabricatorConfig], fields: list[str]) -> list[str]:
    """Map internal field names to headers using fabricator mapping when available."""

    default_headers = {
        "reference": "Designator",
        "value": "Val",
        "package": "Package",
        "footprint": "Footprint",
        "x": "Mid X",
        "y": "Mid Y",
        "rotation": "Rotation",
        "side": "Layer",
        "smd": "SMD",
    }

    if fab:
        rev: Dict[str, str] = {}
        for header, internal in fab.pos_columns.items():
            rev.setdefault(internal, header)
        return [
            rev.get(field_name, default_headers.get(field_name, field_name))
            for field_name in fields
        ]

    return [default_headers.get(field_name, field_name) for field_name in fields]


def get_fabricator_presets(fabricator_id: str) -> Optional[Dict[str, Any]]:
    """Load field presets from fabricator configuration."""

    try:
        config = load_fabricator(fabricator_id)
        return config.presets
    except ValueError:
        return None


def get_fabricator_column_mapping(
    fabricator_id: str, output_type: str
) -> Optional[Dict[str, str]]:
    """Get column mapping from fabricator configuration."""

    try:
        config = load_fabricator(fabricator_id)
        if output_type == "bom":
            return config.bom_columns
        if output_type == "pos":
            return config.pos_columns
        raise ValueError(f"Unknown output_type: {output_type}. Must be 'bom' or 'pos'")
    except ValueError:
        return None


def apply_fabricator_column_mapping(
    fabricator_id: str, output_type: str, fields: List[str]
) -> List[str]:
    """Apply fabricator-specific column mapping to field list."""

    from ..common.fields import field_to_header

    try:
        config = load_fabricator(fabricator_id)
    except ValueError:
        config = None

    column_mapping: Optional[Dict[str, str]] = None
    if config is not None:
        column_mapping = (
            config.bom_columns if output_type == "bom" else config.pos_columns
        )

    if not column_mapping:
        return [field_to_header(internal_field) for internal_field in fields]

    reverse_mapping = {v: k for k, v in column_mapping.items()}

    headers = []
    for internal_field in fields:
        if internal_field in reverse_mapping:
            raw_header = reverse_mapping[internal_field]
            header = (
                config.normalize_header_to_display_name(raw_header)
                if config is not None
                else raw_header
            )
        else:
            header = field_to_header(internal_field)
        headers.append(header)

    return headers


def get_fabricator_default_fields(
    fabricator_id: str,
    output_type: str,
    *,
    mode: str = "standard",
) -> Optional[List[str]]:
    """Get default output fields for a fabricator context."""

    if mode not in {"standard", "additive"}:
        raise ValueError(f"Unknown mode: {mode!r}. Expected 'standard' or 'additive'.")

    try:
        config = load_fabricator(fabricator_id)
    except ValueError:
        return None

    if output_type == "pos" and mode == "additive":
        if config.pos_additive_default_fields:
            return list(config.pos_additive_default_fields)

    if output_type == "bom":
        column_mapping = config.bom_columns
    elif output_type == "pos":
        column_mapping = config.pos_columns
    else:
        raise ValueError(f"Unknown output_type: {output_type}. Must be 'bom' or 'pos'")

    if not column_mapping:
        return None

    return list(column_mapping.values())
