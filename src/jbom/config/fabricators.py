"""Fabricator configuration loader.

Loads fabricator definitions from built-in config files.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import yaml

from jbom.config.suppliers import resolve_supplier_by_id

log = logging.getLogger(__name__)


_SUPPORTED_TIER_OPERATORS = {"exists", "truthy", "equals", "not_empty"}


@dataclass(frozen=True)
class FieldSynonym:
    """Defines acceptable column-name variants for a canonical inventory field."""

    synonyms: List[str]
    display_name: str


@dataclass(frozen=True)
class TierCondition:
    """One condition used to decide whether an inventory item belongs in a tier."""

    field: str
    operator: str
    value: Optional[str] = None

    def matches(self, raw_data: Mapping[str, str]) -> bool:
        """Return True if this condition matches against the provided raw data."""
        if self.operator not in _SUPPORTED_TIER_OPERATORS:
            raise ValueError(
                f"Unsupported tier operator: {self.operator!r}. "
                f"Supported: {sorted(_SUPPORTED_TIER_OPERATORS)}"
            )

        field_value = str(raw_data.get(self.field, ""))

        if self.operator == "exists":
            return bool(field_value)

        if self.operator == "not_empty":
            return bool(field_value.strip())

        if self.operator == "equals":
            if self.value is None:
                raise ValueError("equals operator requires 'value'")
            return field_value == self.value

        if self.operator == "truthy":
            return _is_truthy(field_value)

        raise AssertionError(f"Unhandled operator: {self.operator!r}")


@dataclass(frozen=True)
class TierRule:
    """A set of conditions used to assign an item to a preference tier.

    All conditions must match (AND semantics).
    """

    conditions: List[TierCondition]

    def matches(self, raw_data: Mapping[str, str]) -> bool:
        """Return True if all conditions match.

        An empty condition list matches everything.
        """
        return all(c.matches(raw_data) for c in self.conditions)


def _is_truthy(value: str) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return False

    # Common spreadsheet/csv truthy values.
    return normalized in {"1", "true", "t", "yes", "y", "x"}


@dataclass
class FabricatorConfig:
    """Configuration for a PCB fabricator.

    Defines column mappings, part number preferences, presets, and CLI aliases
    for fabricator-specific BOM and position file generation.
    """

    id: str
    name: str
    pos_columns: Dict[str, str]  # Header -> internal field mapping

    # Phase 1 schema: ordered supplier profile IDs.
    # Position encodes priority (first entry is most preferred).
    suppliers: list[str] = field(default_factory=list)

    # Phase 2 schema: field synonyms + explicit tier rules.
    field_synonyms: Dict[str, FieldSynonym] = field(default_factory=dict)
    tier_rules: Dict[int, TierRule] = field(default_factory=dict)

    description: Optional[str] = None
    bom_columns: Optional[Dict[str, str]] = None  # Header -> internal field mapping
    part_number: Optional[Dict[str, Any]] = None  # Part number configuration
    presets: Optional[Dict[str, Any]] = None  # Field presets
    cli_aliases: Optional[Dict[str, List[str]]] = None  # CLI flags and presets
    pcb_manufacturing: Optional[Dict[str, Any]] = None  # Manufacturing info
    pcb_assembly: Optional[Dict[str, Any]] = None  # Assembly info
    website: Optional[str] = None  # Fabricator website

    @staticmethod
    def from_yaml_dict(data: Dict[str, Any], *, default_id: str) -> "FabricatorConfig":
        """Parse a FabricatorConfig from a YAML dict.

        Args:
            data: YAML mapping produced by yaml.safe_load().
            default_id: Fabricator ID derived from filename when 'id' is not set.

        Raises:
            ValueError: When required fields are missing or schema is invalid.
        """
        pid = data.get("id", default_id)
        name = data.get("name", default_id)

        pos_columns = data.get("pos_columns", {}) or {}
        if not isinstance(pos_columns, dict) or not pos_columns:
            raise ValueError(f"Fabricator '{default_id}' missing pos_columns")

        # Optional fields
        description = data.get("description")
        bom_columns = data.get("bom_columns")
        part_number = data.get("part_number")
        presets = data.get("presets")
        cli_aliases = data.get("cli_aliases")
        pcb_manufacturing = data.get("pcb_manufacturing")
        pcb_assembly = data.get("pcb_assembly")
        website = data.get("website")

        # Phase 1: ordered supplier profile IDs.
        suppliers_cfg = data.get("suppliers") or []
        if not isinstance(suppliers_cfg, list):
            raise ValueError("suppliers must be a list")

        suppliers: list[str] = []
        for raw_sid in suppliers_cfg:
            if not isinstance(raw_sid, str) or not raw_sid.strip():
                raise ValueError("suppliers entries must be non-empty strings")
            sid = raw_sid.strip().lower()
            suppliers.append(sid)

            # Advisory validation: warn on unknown supplier IDs but do not error.
            if resolve_supplier_by_id(sid) is None:
                log.warning(
                    "Unknown supplier profile id %r referenced by fabricator %r",
                    sid,
                    pid,
                )

        # Schema migration guardrail: priority_fields has been replaced by
        # field_synonyms + tier_rules (Issue #59).
        if isinstance(part_number, dict) and "priority_fields" in part_number:
            raise ValueError(
                "Fabricator config uses deprecated part_number.priority_fields. "
                "Migrate to 'field_synonyms' + 'tier_rules'."
            )

        field_synonyms = _parse_field_synonyms(data.get("field_synonyms") or {})
        tier_rules = _parse_tier_rules(data.get("tier_rules") or {})

        return FabricatorConfig(
            id=pid,
            name=name,
            pos_columns=pos_columns,
            suppliers=suppliers,
            field_synonyms=field_synonyms,
            tier_rules=tier_rules,
            description=description,
            bom_columns=bom_columns,
            part_number=part_number,
            presets=presets,
            cli_aliases=cli_aliases,
            pcb_manufacturing=pcb_manufacturing,
            pcb_assembly=pcb_assembly,
            website=website,
        )

    def resolve_field_synonym(self, field_name: str) -> Optional[str]:
        """Resolve a field name variant to its canonical name.

        Matching is forgiving (case-insensitive, ignores surrounding whitespace).
        Returns None when the field name is unknown.
        """
        field_normalized = field_name.strip().lower()

        for canonical, config in self.field_synonyms.items():
            if canonical.strip().lower() == field_normalized:
                return canonical

            for synonym in config.synonyms:
                if synonym.strip().lower() == field_normalized:
                    return canonical

        return None


def _parse_field_synonyms(raw: Any) -> Dict[str, FieldSynonym]:
    if raw is None:
        return {}

    if not isinstance(raw, dict):
        raise ValueError("field_synonyms must be a mapping")

    parsed: Dict[str, FieldSynonym] = {}

    for canonical, cfg in raw.items():
        if not isinstance(canonical, str) or not canonical.strip():
            raise ValueError("field_synonyms keys must be non-empty strings")
        if not isinstance(cfg, dict):
            raise ValueError(f"field_synonyms[{canonical!r}] must be a mapping")

        synonyms = cfg.get("synonyms")
        if not isinstance(synonyms, list) or not all(
            isinstance(s, str) for s in synonyms
        ):
            raise ValueError(
                f"field_synonyms[{canonical!r}].synonyms must be a list of strings"
            )

        display_name = cfg.get("display_name")
        if not isinstance(display_name, str) or not display_name.strip():
            raise ValueError(
                f"field_synonyms[{canonical!r}].display_name must be a non-empty string"
            )

        parsed[canonical] = FieldSynonym(synonyms=synonyms, display_name=display_name)

    return parsed


def _parse_tier_rules(raw: Any) -> Dict[int, TierRule]:
    if raw is None:
        return {}

    if not isinstance(raw, dict):
        raise ValueError("tier_rules must be a mapping")

    parsed: Dict[int, TierRule] = {}

    for tier_key, rule_cfg in raw.items():
        try:
            tier_num = int(tier_key)
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"tier_rules key must be int-like, got: {tier_key!r}"
            ) from e

        if not isinstance(rule_cfg, dict):
            raise ValueError(f"tier_rules[{tier_key!r}] must be a mapping")

        conditions_cfg = rule_cfg.get("conditions", [])
        if not isinstance(conditions_cfg, list):
            raise ValueError(f"tier_rules[{tier_key!r}].conditions must be a list")

        conditions: List[TierCondition] = []
        for cond_cfg in conditions_cfg:
            if not isinstance(cond_cfg, dict):
                raise ValueError(
                    f"tier_rules[{tier_key!r}].conditions entries must be mappings"
                )

            field_name = cond_cfg.get("field")
            operator = cond_cfg.get("operator")
            value = cond_cfg.get("value")

            if not isinstance(field_name, str) or not field_name.strip():
                raise ValueError("TierCondition.field must be a non-empty string")

            if (
                not isinstance(operator, str)
                or operator not in _SUPPORTED_TIER_OPERATORS
            ):
                raise ValueError(
                    f"TierCondition.operator must be one of {sorted(_SUPPORTED_TIER_OPERATORS)}, "
                    f"got: {operator!r}"
                )

            if value is not None and not isinstance(value, str):
                raise ValueError("TierCondition.value must be a string when provided")

            conditions.append(
                TierCondition(field=field_name, operator=operator, value=value)
            )

        parsed[tier_num] = TierRule(conditions=conditions)

    return parsed


_BUILTIN_DIR = Path(__file__).parent / "fabricators"


def list_fabricators() -> list[str]:
    """List available fabricator IDs by scanning config directory.

    Returns:
        Sorted list of fabricator IDs (config filenames without .fab.yaml)
    """
    if not _BUILTIN_DIR.exists():
        return []
    return sorted(p.stem.replace(".fab", "") for p in _BUILTIN_DIR.glob("*.fab.yaml"))


def get_available_fabricators() -> list[str]:
    """Get list of available fabricators with fallback for consistency.

    This is the preferred function for CLI and BDD tests to ensure
    consistent fabricator discovery across the codebase.

    Returns:
        List of fabricator IDs, falling back to ["generic"] if none found
    """
    fabricators = list_fabricators()
    return fabricators if fabricators else ["generic"]


def load_fabricator(fid: str) -> FabricatorConfig:
    """Load fabricator configuration from YAML file.

    Args:
        fid: Fabricator ID (filename without .fab.yaml extension)

    Returns:
        FabricatorConfig with all parsed fields

    Raises:
        ValueError: If fabricator not found or missing required fields
    """
    path = _BUILTIN_DIR / f"{fid}.fab.yaml"
    if not path.exists():
        raise ValueError(f"Unknown fabricator: {fid}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Fabricator '{fid}' config must be a YAML mapping")

    return FabricatorConfig.from_yaml_dict(data, default_id=fid)


def headers_for_fields(fab: Optional[FabricatorConfig], fields: list[str]) -> list[str]:
    """Map internal field names to headers using fabricator mapping when available.

    If a fabricator is active, use its headers (reverse map). Otherwise use defaults.
    """
    # Default header mapping to match legacy format
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
        # reverse map internal -> header, prefer first occurrence order in fab file
        rev: Dict[str, str] = {}
        for header, internal in fab.pos_columns.items():
            rev.setdefault(internal, header)
        # Use fabricator mapping, falling back to defaults for unmapped fields
        return [rev.get(f, default_headers.get(f, f)) for f in fields]

    return [default_headers.get(f, f) for f in fields]


def get_fabricator_presets(fabricator_id: str) -> Optional[Dict[str, Any]]:
    """Load field presets from fabricator configuration.

    Args:
        fabricator_id: ID of fabricator to load presets for

    Returns:
        Dict of presets if available, None if fabricator not found or no presets
    """
    try:
        config = load_fabricator(fabricator_id)
        return config.presets
    except ValueError:
        return None


def get_fabricator_column_mapping(
    fabricator_id: str, output_type: str
) -> Optional[Dict[str, str]]:
    """Get column mapping from fabricator configuration.

    Args:
        fabricator_id: ID of fabricator
        output_type: Either 'bom' or 'pos' for the type of output

    Returns:
        Dict mapping headers to internal field names, or None if not found
    """
    try:
        config = load_fabricator(fabricator_id)
        if output_type == "bom":
            return config.bom_columns
        elif output_type == "pos":
            return config.pos_columns
        else:
            raise ValueError(
                f"Unknown output_type: {output_type}. Must be 'bom' or 'pos'"
            )
    except ValueError:
        return None


def apply_fabricator_column_mapping(
    fabricator_id: str, output_type: str, fields: List[str]
) -> List[str]:
    """Apply fabricator-specific column mapping to field list.

    Args:
        fabricator_id: ID of fabricator
        output_type: Either 'bom' or 'pos'
        fields: List of internal field names

    Returns:
        List of headers using fabricator-specific mapping
    """
    column_mapping = get_fabricator_column_mapping(fabricator_id, output_type)

    if not column_mapping:
        # No fabricator mapping available, convert field names to proper headers
        from ..common.fields import field_to_header

        return [field_to_header(internal_field) for internal_field in fields]

    # Create reverse mapping: internal field -> header
    reverse_mapping = {v: k for k, v in column_mapping.items()}

    # Apply mapping, falling back to formatted field name if no mapping exists
    headers = []
    for internal_field in fields:
        if internal_field in reverse_mapping:
            header = reverse_mapping[internal_field]
        else:
            # No specific mapping - format the field name nicely
            from ..common.fields import field_to_header

            header = field_to_header(internal_field)
        headers.append(header)

    return headers


def get_fabricator_default_fields(
    fabricator_id: str, output_type: str
) -> Optional[List[str]]:
    """Get default fields for a fabricator based on its column mapping.

    Args:
        fabricator_id: ID of fabricator
        output_type: Either 'bom' or 'pos'

    Returns:
        List of default field names based on fabricator config, or None
    """
    column_mapping = get_fabricator_column_mapping(fabricator_id, output_type)

    if column_mapping:
        # Return the internal field names from the column mapping
        return list(column_mapping.values())

    return None
