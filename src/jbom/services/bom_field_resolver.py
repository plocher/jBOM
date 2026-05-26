"""BOM field value resolution service.

Extracts and resolves individual field values from BOM entries, applying
fabricator-specific projection and namespace-aware source selection.
"""
from __future__ import annotations
from functools import lru_cache
from typing import Any, Mapping, Optional

from jbom.common.fields import normalize_field_name
from jbom.common.component_utils import derive_package_from_footprint
from jbom.services.bom_generator import BOMEntry
from jbom.services.field_listing_service import resolve_field
from jbom.config.field_expr import (
    FieldExpressionEvaluator,
    TransformCallable,
)
from jbom.config.field_ref import FieldContext, FieldRefResolver
from jbom.config.fields import (
    ANNOTATION_NAMESPACE,
    INV_NAMESPACE,
    PCB_NAMESPACE,
    SCH_NAMESPACE,
)
from jbom.config.fabricators import FabricatorConfig
from jbom.config.unified import load_unified

# Source priority: PCB first, then inventory, then schematic
_BOM_SOURCE_PRIORITY = [PCB_NAMESPACE, INV_NAMESPACE, SCH_NAMESPACE]


def resolve_bom_field_value(
    entry: BOMEntry,
    field: str,
    *,
    fabricator_id: str = "generic",
    fabricator_config: Optional[FabricatorConfig] = None,
) -> str:
    """Resolve one BOM field token through canonical field-reference semantics."""

    raw_field = str(field or "").strip()
    if not raw_field:
        return ""

    field_resolver = _field_ref_resolver_for_fabricator(fabricator_id)
    parsed_input = field_resolver.parse(raw_field)
    resolved_field_token = (
        raw_field
        if parsed_input.is_expression
        else field_resolver.normalize_reference_token(raw_field)
    )
    field_context = _build_field_context(
        entry,
        fabricator_id=fabricator_id,
        fabricator_config=fabricator_config,
    )
    if not parsed_input.is_expression and resolved_field_token == "mfgpn":
        manufacturer_part = field_resolver.resolve("manufacturer_part", field_context)
        if manufacturer_part:
            return manufacturer_part
    parsed_field = field_resolver.parse(resolved_field_token)
    resolved_value = field_resolver.resolve(resolved_field_token, field_context)
    if resolved_value:
        return resolved_value

    if parsed_field.is_expression or parsed_field.namespace:
        return resolved_value
    if resolved_field_token == "dnp":
        # dnp is a bool attribute; return "DNP" or "" without going through
        # _get_attribute_value which would coerce False -> "No".
        return "DNP" if entry.attributes.get("dnp") else ""
    if resolved_field_token == "package":
        return derive_package_from_footprint(entry.footprint)
    if resolved_field_token == "lcsc":
        return _get_attribute_value(entry, "LCSC")
    return _get_attribute_value(entry, resolved_field_token)


@lru_cache(maxsize=32)
def _field_ref_resolver_for_fabricator(fabricator_id: str) -> FieldRefResolver:
    """Return a cached field resolver with transforms for one fabricator profile."""

    return FieldRefResolver(
        builtin_transforms=_compiled_transform_functions_for_fabricator(fabricator_id)
    )


@lru_cache(maxsize=32)
def _compiled_transform_functions_for_fabricator(
    fabricator_id: str,
) -> dict[str, TransformCallable]:
    """Load and compile profile transform definitions for expression evaluation."""
    normalized_fabricator_id = str(fabricator_id or "generic").strip().lower()
    if not normalized_fabricator_id:
        return {}

    try:
        merged_profile = load_unified(normalized_fabricator_id)
    except Exception:
        return {}

    transforms_stanza = merged_profile.get("transforms")
    if not isinstance(transforms_stanza, Mapping):
        return {}

    compilation_result = FieldExpressionEvaluator().compile_transforms(
        transforms_stanza,
        source_name=f"{normalized_fabricator_id}.jbom.yaml",
    )
    if any(
        diagnostic.severity == "error" for diagnostic in compilation_result.diagnostics
    ):
        return {}
    return compilation_result.transforms


def _build_field_context(
    entry: BOMEntry,
    *,
    fabricator_id: str,
    fabricator_config: Optional[FabricatorConfig],
) -> FieldContext:
    """Build resolver context for one BOM row."""

    row_sources = _build_bom_row_sources(entry, include_unqualified_fallback=True)
    computed_fields = _build_computed_field_values(
        entry,
        fabricator_id=fabricator_id,
        fabricator_config=fabricator_config,
    )
    annotation_fields = _build_annotation_field_values(entry, row_sources)
    return FieldContext.from_row_sources(
        row_sources,
        computed=computed_fields,
        annotations=annotation_fields,
        source_priority=(PCB_NAMESPACE, INV_NAMESPACE, SCH_NAMESPACE),
    )


def _build_computed_field_values(
    entry: BOMEntry,
    *,
    fabricator_id: str,
    fabricator_config: Optional[FabricatorConfig],
) -> dict[str, object]:
    """Build computed-field values exposed under `jbom:*` references."""

    fabricator_part_number = _resolve_fabricator_part_number(
        entry,
        fabricator_id=fabricator_id,
        fabricator_config=fabricator_config,
    )
    smd_value = _resolve_smd_indicator(entry)
    dnp_value = "DNP" if entry.attributes.get("dnp") else ""
    return {
        "reference": entry.references_string,
        "quantity": entry.quantity,
        "fabricator_part_number": fabricator_part_number,
        "smd": smd_value,
        "dnp": dnp_value,
        "jbom:quantity": entry.quantity,
        "jbom:fabricator_part_number": fabricator_part_number,
        "jbom:smd": smd_value,
        "jbom:dnp": dnp_value,
    }


def _build_annotation_field_values(
    entry: BOMEntry,
    row_sources: Mapping[str, Mapping[str, object]],
) -> dict[str, str]:
    """Build concrete `ann:*` annotation values from source fields and explicit attrs."""

    annotations: dict[str, str] = {}

    for attribute_key, attribute_value in entry.attributes.items():
        normalized_key = normalize_field_name(str(attribute_key or ""))
        annotation_prefix = f"{ANNOTATION_NAMESPACE}:"
        if not normalized_key.startswith(annotation_prefix):
            continue
        annotation_key = normalized_key[len(annotation_prefix) :]
        if not annotation_key:
            continue
        annotation_value = _coerce_output_value(attribute_value)
        if annotation_value:
            annotations[annotation_key] = annotation_value

    candidate_field_names: set[str] = set()
    for source_fields in row_sources.values():
        for source_field in source_fields.keys():
            normalized_field_name = normalize_field_name(str(source_field or ""))
            if normalized_field_name:
                candidate_field_names.add(normalized_field_name)

    for field_name in sorted(candidate_field_names):
        if field_name in annotations:
            continue
        rendered_annotation = _render_source_annotation_value(field_name, row_sources)
        if rendered_annotation:
            annotations[field_name] = rendered_annotation

    return annotations


def _render_source_annotation_value(
    field_name: str,
    row_sources: Mapping[str, Mapping[str, object]],
) -> str:
    """Render `ann:<field>` output lines in stable source order."""

    lines: list[tuple[str, str]] = []
    for namespace in (SCH_NAMESPACE, PCB_NAMESPACE, INV_NAMESPACE):
        value = resolve_field(
            f"{namespace}:{field_name}",
            row_sources,
            priority=_BOM_SOURCE_PRIORITY,
        )
        if value:
            lines.append((namespace, value))

    if not lines:
        return ""

    unique_lines: list[tuple[str, str]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for namespace, value in lines:
        pair = (namespace, value)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        unique_lines.append(pair)
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
    """Build source field maps for one BOM row (`sch`, `pcb`, `inv`)."""
    row_sources: dict[str, dict[str, object]] = {
        SCH_NAMESPACE: {},
        PCB_NAMESPACE: {},
        INV_NAMESPACE: {},
    }
    for attr_key, attr_value in entry.attributes.items():
        normalized_key = normalize_field_name(str(attr_key or ""))
        prefix, separator, remainder = normalized_key.partition(":")
        if (
            separator
            and prefix in {SCH_NAMESPACE, PCB_NAMESPACE, INV_NAMESPACE}
            and remainder
        ):
            row_sources[prefix][remainder] = attr_value

    if include_unqualified_fallback:
        # Keep unqualified behavior stable when merge enrichment is absent.
        if entry.references_string:
            row_sources[SCH_NAMESPACE].setdefault("reference", entry.references_string)
        if entry.value:
            row_sources[SCH_NAMESPACE].setdefault("value", entry.value)
        if entry.footprint:
            row_sources[SCH_NAMESPACE].setdefault("footprint", entry.footprint)
        package_value = _get_attribute_value(entry, "package")
        if package_value:
            row_sources[SCH_NAMESPACE].setdefault("package", package_value)

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
