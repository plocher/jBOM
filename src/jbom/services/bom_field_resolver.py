"""BOM field value resolution service.

Extracts and resolves individual field values from BOM entries, applying
fabricator-specific projection and namespace-aware source selection.
"""
from __future__ import annotations

from typing import Any, Optional

from jbom.common.fields import normalize_field_name, split_kicad_strip_field
from jbom.common.component_utils import derive_package_from_footprint
from jbom.services.bom_generator import BOMEntry
from jbom.services.field_listing_service import resolve_field
from jbom.config.fabricators import FabricatorConfig

# Source priority: PCB first, then inventory, then schematic
_BOM_SOURCE_PRIORITY = ["p", "i", "s"]


def resolve_bom_field_value(
    entry: BOMEntry,
    field: str,
    *,
    fabricator_id: str = "generic",
    fabricator_config: Optional[FabricatorConfig] = None,
) -> str:
    """Extract and resolve a field value from a BOM entry.

    Handles standard fields, namespaced fields (s:, p:, i:, a:), and
    KiCad strip modifiers (k:). Applies fabricator-specific projection
    and source precedence rules.

    Args:
        entry: BOM entry object
        field: Field name to resolve (standard, namespaced, or with modifier)
        fabricator_id: Fabricator ID for projection logic
        fabricator_config: Optional fabricator configuration

    Returns:
        String value for the field
    """
    import logging

    # Handle k: modifier — KiCad LIBRARY:NAME → NAME (strip library nickname).
    # "k:footprint" defaults to inventory source; use "i:k:", "s:k:", "p:k:" explicitly.
    kicad_parts = split_kicad_strip_field(field)
    if kicad_parts is not None:
        source, inner = kicad_parts
        if field.startswith("k:"):
            logging.getLogger(__name__).debug(
                "k:%s: no source prefix specified, defaulting to i: (inventory). "
                "Use i:k:, s:k:, or p:k: to be explicit.",
                inner,
            )
        raw = _resolve_namespaced_field_value(
            entry,
            source,
            inner,
            fabricator_id=fabricator_id,
            fabricator_config=fabricator_config,
        )
        return derive_package_from_footprint(raw)

    # Handle namespaced fields
    if field.startswith("i:"):
        return _resolve_namespaced_field_value(
            entry,
            "i",
            field[2:],
            fabricator_id=fabricator_id,
            fabricator_config=fabricator_config,
        )

    if field.startswith("s:"):
        return _resolve_namespaced_field_value(
            entry,
            "s",
            field[2:],
            fabricator_id=fabricator_id,
            fabricator_config=fabricator_config,
        )

    if field.startswith("p:"):
        return _resolve_namespaced_field_value(
            entry,
            "p",
            field[2:],
            fabricator_id=fabricator_id,
            fabricator_config=fabricator_config,
        )

    if field.startswith("a:"):
        return _resolve_annotation_field_value(
            entry,
            field[2:],
            fabricator_id=fabricator_id,
            fabricator_config=fabricator_config,
        )

    # Handle standard BOM fields
    return _resolve_standard_field_value(
        entry,
        field,
        fabricator_id=fabricator_id,
        fabricator_config=fabricator_config,
    )


def _resolve_standard_field_value(
    entry: BOMEntry,
    field: str,
    *,
    fabricator_id: str,
    fabricator_config: Optional[FabricatorConfig],
) -> str:
    """Resolve a standard (non-prefixed) BOM field."""
    if field == "reference":
        return entry.references_string
    if field == "quantity":
        return str(entry.quantity)
    if field == "fabricator_part_number":
        return _resolve_fabricator_part_number(
            entry,
            fabricator_id=fabricator_id,
            fabricator_config=fabricator_config,
        )
    if field == "smd":
        return _resolve_smd_indicator(entry)

    row_sources = _build_bom_row_sources(entry, include_unqualified_fallback=True)
    if field == "mfgpn":
        return resolve_field(
            "manufacturer_part",
            row_sources,
            priority=_BOM_SOURCE_PRIORITY,
        ) or resolve_field(
            "mfgpn",
            row_sources,
            priority=_BOM_SOURCE_PRIORITY,
        )
    if field == "package":
        return resolve_field(
            "package",
            row_sources,
            priority=_BOM_SOURCE_PRIORITY,
        ) or derive_package_from_footprint(entry.footprint)
    if field == "lcsc":
        return resolve_field(
            "lcsc",
            row_sources,
            priority=_BOM_SOURCE_PRIORITY,
        ) or _get_attribute_value(entry, "LCSC")
    resolved_value = resolve_field(
        field,
        row_sources,
        priority=_BOM_SOURCE_PRIORITY,
    )
    if resolved_value:
        return resolved_value

    return _get_attribute_value(entry, field)


def _resolve_namespaced_field_value(
    entry: BOMEntry,
    namespace: str,
    namespaced_field: str,
    *,
    fabricator_id: str,
    fabricator_config: Optional[FabricatorConfig],
) -> str:
    """Resolve a namespace-qualified field under strict source semantics."""
    row_sources = _build_bom_row_sources(entry, include_unqualified_fallback=False)
    return resolve_field(
        f"{namespace}:{namespaced_field}",
        row_sources,
        priority=_BOM_SOURCE_PRIORITY,
    )


def _resolve_annotation_field_value(
    entry: BOMEntry,
    annotation_field: str,
    *,
    fabricator_id: str,
    fabricator_config: Optional[FabricatorConfig],
) -> str:
    """Render `a:*` fields as deterministic source annotation lines."""
    explicit = _get_attribute_value(entry, f"a:{annotation_field}")
    if explicit:
        return explicit

    lines: list[tuple[str, str]] = []

    for namespace in ("s", "p"):
        value = _resolve_namespaced_field_value(
            entry,
            namespace,
            annotation_field,
            fabricator_id=fabricator_id,
            fabricator_config=fabricator_config,
        )
        if value:
            lines.append((namespace, value))

    inventory_value = _resolve_namespaced_field_value(
        entry,
        "i",
        annotation_field,
        fabricator_id=fabricator_id,
        fabricator_config=fabricator_config,
    )
    if inventory_value:
        lines.append(("i", inventory_value))

    if not lines:
        return ""

    unique_lines: list[tuple[str, str]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for namespace_value in lines:
        if namespace_value in seen_pairs:
            continue
        seen_pairs.add(namespace_value)
        unique_lines.append(namespace_value)

    return "\n".join(f"{namespace}:{value}" for namespace, value in unique_lines)


def _resolve_fabricator_part_number(
    entry: BOMEntry,
    *,
    fabricator_id: str,
    fabricator_config: Optional[FabricatorConfig],
) -> str:
    """Resolve fabricator part number using projection service."""
    from jbom.services.fabricator_projection_service import FabricatorProjectionService

    return FabricatorProjectionService.resolve_fabricator_part_number(
        entry.attributes,
        fabricator_id=fabricator_id,
        fabricator_config=fabricator_config,
    )


def _resolve_smd_indicator(entry: BOMEntry) -> str:
    """Resolve SMD mount type indicator from component attributes."""
    from jbom.common.package_matching import PackageType

    def _is_smd_token(value: str) -> bool:
        """Return True when a token contains known SMD package patterns."""
        token = (value or "").strip().lower()
        if not token:
            return False
        for pattern in sorted(PackageType.SMD_PACKAGES, key=len, reverse=True):
            if pattern in token:
                return True
        return False

    raw = entry.attributes.get("smd", "")
    if isinstance(raw, bool):
        return "Yes" if raw else "No"

    raw_text = str(raw).strip().lower()
    if raw_text in {"yes", "y", "true", "1", "smd"}:
        return "Yes"
    if raw_text in {"no", "n", "false", "0", "tht", "through_hole", "through-hole"}:
        return "No"

    package = str(entry.attributes.get("package", "")).strip()
    if _is_smd_token(package):
        return "Yes"

    derived_package = derive_package_from_footprint(entry.footprint)
    if _is_smd_token(derived_package):
        return "Yes"

    if _is_smd_token(entry.footprint):
        return "Yes"

    return "No"


def _build_bom_row_sources(
    entry: BOMEntry,
    *,
    include_unqualified_fallback: bool,
) -> dict[str, dict[str, object]]:
    """Build source field maps for one BOM row (`s`, `p`, `i`)."""
    row_sources: dict[str, dict[str, object]] = {"s": {}, "p": {}, "i": {}}
    for attr_key, attr_value in entry.attributes.items():
        normalized_key = normalize_field_name(str(attr_key or ""))
        prefix, separator, remainder = normalized_key.partition(":")
        if separator and prefix in {"s", "p", "i"} and remainder:
            row_sources[prefix][remainder] = attr_value

    if include_unqualified_fallback:
        # Keep unqualified behavior stable when merge enrichment is absent.
        if entry.value:
            row_sources["s"].setdefault("value", entry.value)
        if entry.footprint:
            row_sources["s"].setdefault("footprint", entry.footprint)
        package_value = _get_attribute_value(entry, "package")
        if package_value:
            row_sources["s"].setdefault("package", package_value)

    return row_sources


def _get_attribute_value(entry: BOMEntry, key: str) -> str:
    """Return a normalized attribute value from a BOM entry."""
    return _coerce_output_value(entry.attributes.get(key, ""))


def _coerce_output_value(raw_value: Any) -> str:
    """Convert raw values to output-ready strings while preserving empties."""
    if isinstance(raw_value, str):
        return raw_value if raw_value.strip() else ""

    if raw_value is None:
        return ""

    if isinstance(raw_value, bool):
        return "Yes" if raw_value else "No"

    return str(raw_value)


__all__ = [
    "resolve_bom_field_value",
]
