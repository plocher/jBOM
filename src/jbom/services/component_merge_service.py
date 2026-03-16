"""Component merge service for source namespace-aware workflows.

Current scope:
- build deterministic source and annotation fields (`s:*`, `p:*`, `a:*`)
- emit structured mismatch metadata for source disagreements
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from jbom.services.project_component_collector import (
    ProjectComponentGraph,
    ProjectReferenceRecord,
)

MismatchSeverity = Literal["warning", "error"]


@dataclass(frozen=True)
class MergeMismatchRecord:
    """Structured mismatch metadata for one merged field disagreement."""

    reference: str
    field_key: str
    severity: MismatchSeverity
    source_values: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class MergedReferenceRecord:
    """Merged namespace-aware record for a single reference."""

    reference: str
    source_fields: dict[str, str] = field(default_factory=dict)
    annotated_fields: dict[str, str] = field(default_factory=dict)
    mismatches: tuple[MergeMismatchRecord, ...] = tuple()


@dataclass(frozen=True)
class ComponentMergeResult:
    """Container for merged reference records and mismatch metadata."""

    records: dict[str, MergedReferenceRecord] = field(default_factory=dict)
    mismatches: tuple[MergeMismatchRecord, ...] = tuple()
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def reference_count(self) -> int:
        """Return the number of merged reference records."""

        return len(self.records)


def resolve_grouped_merge_namespace_values(
    reference_records: list[MergedReferenceRecord],
) -> dict[str, str]:
    """Resolve grouped namespace values for one aggregated output entry.

    `s:*` and `p:*` fields are emitted only when grouped references agree.
    `a:*` fields are always human-oriented: when grouped references disagree on
    annotation text, render a deterministic reference-indexed summary.
    """

    resolved_fields: dict[str, str] = {}
    for namespace_field in ("source_fields", "annotated_fields"):
        field_keys = sorted(
            {
                field_key
                for record in reference_records
                for field_key in getattr(record, namespace_field).keys()
            }
        )
        for field_key in field_keys:
            if namespace_field == "annotated_fields":
                resolved_value = _resolve_grouped_annotation_field_value(
                    reference_records,
                    field_key=field_key,
                )
            else:
                resolved_value = _resolve_uniform_group_field_value(
                    reference_records,
                    namespace_field=namespace_field,
                    field_key=field_key,
                )
            if resolved_value:
                resolved_fields[field_key] = resolved_value
    return resolved_fields


def _resolve_uniform_group_field_value(
    reference_records: list[MergedReferenceRecord],
    *,
    namespace_field: str,
    field_key: str,
) -> str:
    """Resolve one namespace field only when grouped references agree."""

    resolved_value = ""
    for record in reference_records:
        namespace_values = getattr(record, namespace_field)
        candidate_value = str(namespace_values.get(field_key, "")).strip()
        if not candidate_value:
            continue
        if not resolved_value:
            resolved_value = candidate_value
            continue
        if candidate_value != resolved_value:
            return ""
    return resolved_value


def _resolve_grouped_annotation_field_value(
    reference_records: list[MergedReferenceRecord],
    *,
    field_key: str,
) -> str:
    """Resolve grouped `a:*` annotation text for one field key.

    Contract:
    - If all grouped references resolve to one summary, return only the summary.
    - If grouped references resolve to multiple summaries, render deterministic
      reference-indexed segments joined by ` || `.
    - Mismatch summaries prefer concise diagnostic wording:
      `S: and P: differ\\ns:<value>\\np:<value>`.
    - Non-mismatch summaries collapse to one source value when available.
    """

    field_name = _annotation_field_name(field_key)
    summary_groups: dict[str, list[str]] = {}
    for record in reference_records:
        summary = _build_grouped_annotation_summary(
            record,
            field_key=field_key,
            field_name=field_name,
        )
        if not summary:
            continue
        summary_groups.setdefault(summary, []).append(record.reference)

    if not summary_groups:
        return ""
    if len(summary_groups) == 1:
        return next(iter(summary_groups))

    grouped_segments: list[str] = []
    sorted_groups = sorted(
        summary_groups.items(),
        key=lambda item: _group_reference_sort_key(item[1]),
    )
    for summary, references in sorted_groups:
        ordered_references = sorted(
            {str(reference or "").strip() for reference in references if reference},
            key=_natural_reference_sort_key,
        )
        if not ordered_references:
            continue
        grouped_segments.append(f"{','.join(ordered_references)} -> {summary}")
    return " || ".join(grouped_segments)


def _annotation_field_name(field_key: str) -> str:
    """Return the unprefixed field name for an annotation key."""

    prefix, separator, remainder = str(field_key or "").partition(":")
    if separator and prefix == "a" and remainder:
        return remainder
    return str(field_key or "")


def _build_grouped_annotation_summary(
    record: MergedReferenceRecord,
    *,
    field_key: str,
    field_name: str,
) -> str:
    """Build one grouped annotation summary for a merged reference record."""

    source_s = str(record.source_fields.get(f"s:{field_name}", "")).strip()
    source_p = str(record.source_fields.get(f"p:{field_name}", "")).strip()
    explicit_annotation = str(record.annotated_fields.get(field_key, "")).strip()

    if source_s and source_p and source_s != source_p:
        return _format_mismatch_annotation_summary(source_s=source_s, source_p=source_p)
    if source_s and source_p and source_s == source_p:
        return source_s
    if source_s:
        return source_s
    if source_p:
        return source_p
    if explicit_annotation:
        return explicit_annotation
    return ""


def _format_mismatch_annotation_summary(
    *,
    source_s: str,
    source_p: str,
) -> str:
    """Render concise mismatch annotation text for grouped `a:*` output."""
    lines: list[str] = ["S: and P: differ"]
    lines.append(f"s:{source_s}")
    lines.append(f"p:{source_p}")

    return "\n".join(lines)


def _group_reference_sort_key(references: list[str]) -> list[object]:
    """Sort annotation groups by their first natural-sorted reference."""

    if not references:
        return []
    ordered_references = sorted(
        {str(reference or "").strip() for reference in references if reference},
        key=_natural_reference_sort_key,
    )
    if not ordered_references:
        return []
    return _natural_reference_sort_key(ordered_references[0])


def _natural_reference_sort_key(reference: str) -> list[object]:
    """Generate natural sort keys for reference designators."""

    import re

    parts = re.split(r"(\d+)", str(reference or ""))
    key: list[object] = []
    for part in parts:
        if part.isdigit():
            key.append(int(part))
        else:
            key.append(part)
    return key


class ComponentMergeService:
    """Merge project component graphs into source namespace-aware records."""

    def __init__(self) -> None:
        """Initialize the merge service."""

    def merge(self, project_graph: ProjectComponentGraph) -> ComponentMergeResult:
        """Merge collected project graph into source namespace-rich records."""

        merged_records: dict[str, MergedReferenceRecord] = {}
        mismatch_records: list[MergeMismatchRecord] = []

        for reference in sorted(project_graph.references.keys()):
            project_record = project_graph.references[reference]
            merged_record = self._merge_reference_record(project_record)
            merged_records[reference] = merged_record
            mismatch_records.extend(merged_record.mismatches)

        metadata: dict[str, object] = {"mismatch_count": len(mismatch_records)}
        return ComponentMergeResult(
            records=merged_records,
            mismatches=tuple(mismatch_records),
            metadata=metadata,
        )

    def _merge_reference_record(
        self, project_record: ProjectReferenceRecord
    ) -> MergedReferenceRecord:
        """Merge one reference record into source/annotated namespaces."""

        source_fields = self._build_source_fields(project_record)
        mismatches = self._build_mismatches(project_record.reference, source_fields)
        annotated_fields = self._build_annotated_fields(mismatches)

        return MergedReferenceRecord(
            reference=project_record.reference,
            source_fields=source_fields,
            annotated_fields=annotated_fields,
            mismatches=tuple(mismatches),
        )

    def _build_source_fields(
        self, project_record: ProjectReferenceRecord
    ) -> dict[str, str]:
        """Build source namespace fields (`s:*`, `p:*`) for one reference."""

        source_fields: dict[str, str] = {}
        schematic_fields = self._extract_schematic_fields(project_record)
        pcb_fields = self._extract_pcb_fields(project_record)
        for field_name, field_value in schematic_fields.items():
            source_fields[f"s:{field_name}"] = field_value
        for field_name, field_value in pcb_fields.items():
            source_fields[f"p:{field_name}"] = field_value
        return source_fields

    def _build_mismatches(
        self,
        reference: str,
        source_fields: dict[str, str],
    ) -> list[MergeMismatchRecord]:
        """Build mismatch records for source namespace disagreements."""

        mismatches: list[MergeMismatchRecord] = []
        for field_name in self._iter_source_field_names(source_fields):
            schematic_value = source_fields.get(f"s:{field_name}", "")
            pcb_value = source_fields.get(f"p:{field_name}", "")
            if not schematic_value or not pcb_value or schematic_value == pcb_value:
                continue
            mismatches.append(
                MergeMismatchRecord(
                    reference=reference,
                    field_key=field_name,
                    severity="warning",
                    source_values={"s": schematic_value, "p": pcb_value},
                )
            )
        return mismatches

    def _build_annotated_fields(
        self, mismatches: list[MergeMismatchRecord]
    ) -> dict[str, str]:
        """Build `a:*` annotation cells from mismatch records."""

        annotated: dict[str, str] = {}
        for mismatch in mismatches:
            source_lines = []
            if mismatch.source_values.get("s"):
                source_lines.append(f"s:{mismatch.source_values['s']}")
            if mismatch.source_values.get("p"):
                source_lines.append(f"p:{mismatch.source_values['p']}")
            if source_lines:
                annotated[f"a:{mismatch.field_key}"] = "\n".join(source_lines)
        return annotated

    def _extract_schematic_fields(
        self, project_record: ProjectReferenceRecord
    ) -> dict[str, str]:
        """Extract canonical schematic source fields for one reference."""

        if not project_record.schematic_components:
            return {}

        component = project_record.schematic_components[0]
        schematic_fields: dict[str, str] = {}

        self._set_if_present(schematic_fields, "value", component.value)
        self._set_if_present(schematic_fields, "footprint", component.footprint)
        self._set_if_present(
            schematic_fields,
            "package",
            self._get_component_property(component, ("Package",)),
        )
        self._set_if_present(
            schematic_fields,
            "tolerance",
            self._get_component_property(component, ("Tolerance",)),
        )
        self._set_if_present(
            schematic_fields,
            "voltage",
            self._get_component_property(component, ("Voltage",)),
        )
        self._set_if_present(
            schematic_fields,
            "current",
            self._get_component_property(component, ("Current", "Amperage")),
        )
        self._set_if_present(
            schematic_fields,
            "wavelength",
            self._get_component_property(component, ("Wavelength",)),
        )
        self._set_if_present(
            schematic_fields,
            "manufacturer",
            self._get_component_property(component, ("Manufacturer",)),
        )
        self._set_if_present(
            schematic_fields,
            "manufacturer_part",
            self._get_component_property(
                component,
                ("MFGPN", "MPN", "Manufacturer Part Number"),
            ),
        )
        self._set_if_present(
            schematic_fields,
            "fabricator_part_number",
            self._get_component_property(component, ("fabricator_part_number",)),
        )
        self._set_if_present(
            schematic_fields,
            "lcsc",
            self._get_component_property(component, ("LCSC", "lcsc")),
        )

        return schematic_fields

    def _extract_pcb_fields(
        self, project_record: ProjectReferenceRecord
    ) -> dict[str, str]:
        """Extract canonical PCB source fields for one reference."""

        if not project_record.pcb_components:
            return {}

        component = project_record.pcb_components[0]
        pcb_fields: dict[str, str] = {}

        self._set_if_present(pcb_fields, "footprint", component.footprint_name)
        self._set_if_present(pcb_fields, "package", component.package_token)
        self._set_if_present(pcb_fields, "side", component.side)
        self._set_if_present(
            pcb_fields,
            "mount_type",
            component.attributes.get("mount_type", ""),
        )
        self._set_if_present(
            pcb_fields,
            "value",
            self._get_pcb_attribute(component, ("Value", "value")),
        )
        self._set_if_present(
            pcb_fields,
            "x",
            component.center_x_raw
            if component.center_x_raw is not None
            else f"{component.center_x_mm:.4f}",
        )
        self._set_if_present(
            pcb_fields,
            "y",
            component.center_y_raw
            if component.center_y_raw is not None
            else f"{component.center_y_mm:.4f}",
        )
        self._set_if_present(
            pcb_fields,
            "rotation",
            component.rotation_raw
            if component.rotation_raw is not None
            else f"{component.rotation_deg:.1f}",
        )

        return pcb_fields

    def _iter_source_field_names(
        self, source_fields: dict[str, str]
    ) -> tuple[str, ...]:
        """Return sorted source field names without namespace prefixes."""

        field_names: set[str] = set()
        for prefixed_name in source_fields:
            if prefixed_name.startswith("s:") or prefixed_name.startswith("p:"):
                field_names.add(prefixed_name[2:])
        return tuple(sorted(field_names))

    def _get_component_property(
        self,
        component: object,
        aliases: tuple[str, ...],
    ) -> str:
        """Return the first populated schematic property matching aliases."""

        properties = getattr(component, "properties", {}) or {}
        normalized_properties = {
            str(key or "").strip().lower(): self._normalize_value(value)
            for key, value in properties.items()
        }
        for alias in aliases:
            direct_value = self._normalize_value(properties.get(alias, ""))
            if direct_value:
                return direct_value
            lowered = normalized_properties.get(alias.strip().lower(), "")
            if lowered:
                return lowered
        return ""

    def _get_pcb_attribute(
        self,
        component: object,
        aliases: tuple[str, ...],
    ) -> str:
        """Return the first populated PCB attribute value matching aliases."""

        attributes = getattr(component, "attributes", {}) or {}
        normalized_attributes = {
            str(key or "").strip().lower(): self._normalize_value(value)
            for key, value in attributes.items()
        }
        for alias in aliases:
            direct_value = self._normalize_value(attributes.get(alias, ""))
            if direct_value:
                return direct_value
            lowered = normalized_attributes.get(alias.strip().lower(), "")
            if lowered:
                return lowered
        return ""

    def _set_if_present(
        self,
        container: dict[str, str],
        key: str,
        raw_value: object,
    ) -> None:
        """Set a container key only when the normalized value is present."""

        value = self._normalize_value(raw_value)
        if value:
            container[key] = value

    def _normalize_value(self, raw_value: object) -> str:
        """Normalize scalar values to stripped string form."""

        return str(raw_value or "").strip()
