"""Component merge service for canonical namespace-aware workflows.

Current scope:
- load field precedence policy metadata from defaults configuration
- build deterministic source/canonical/annotation fields (`s:*`, `p:*`, `c:*`, `a:*`)
- emit structured mismatch metadata with canonical decision reasons
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from jbom.config.defaults import get_defaults
from jbom.services.project_component_collector import (
    ProjectComponentGraph,
    ProjectReferenceRecord,
)

MismatchSeverity = Literal["warning", "error"]

_DEFAULT_SCHEMATIC_BIASED_FIELDS: tuple[str, ...] = (
    "value",
    "tolerance",
    "voltage",
    "current",
    "wavelength",
)
_DEFAULT_PCB_BIASED_FIELDS: tuple[str, ...] = (
    "footprint",
    "package",
    "mount_type",
    "side",
    "x",
    "y",
    "rotation",
)
_DEFAULT_INVENTORY_BIASED_FIELDS: tuple[str, ...] = (
    "manufacturer",
    "manufacturer_part",
    "fabricator_part_number",
    "lcsc",
)


@dataclass(frozen=True)
class MergePrecedencePolicy:
    """Field precedence policy loaded from defaults configuration."""

    profile_name: str
    schematic_biased_fields: tuple[str, ...] = tuple()
    pcb_biased_fields: tuple[str, ...] = tuple()
    inventory_biased_fields: tuple[str, ...] = tuple()


@dataclass(frozen=True)
class MergeMismatchRecord:
    """Structured mismatch metadata for one merged field decision."""

    reference: str
    field_key: str
    severity: MismatchSeverity
    decision_reason: str
    source_values: dict[str, str] = field(default_factory=dict)
    canonical_value: str = ""


@dataclass(frozen=True)
class MergedReferenceRecord:
    """Merged namespace-aware record for a single reference."""

    reference: str
    source_fields: dict[str, str] = field(default_factory=dict)
    canonical_fields: dict[str, str] = field(default_factory=dict)
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

    `s:*` and `c:*` fields are emitted only when grouped references agree.
    `a:*` fields are always human-oriented: when grouped references disagree on
    annotation text, render a deterministic reference-indexed summary.
    """

    resolved_fields: dict[str, str] = {}
    for namespace_field in ("source_fields", "canonical_fields", "annotated_fields"):
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
      `S: and P: differ\\np:<value> chosen\\ns:<value>`.
    - Non-mismatch summaries collapse to the canonical value when available.
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
    canonical_value = str(record.canonical_fields.get(f"c:{field_name}", "")).strip()
    explicit_annotation = str(record.annotated_fields.get(field_key, "")).strip()

    if source_s and source_p and source_s != source_p:
        return _format_mismatch_annotation_summary(
            source_s=source_s,
            source_p=source_p,
            canonical_value=canonical_value,
        )

    if canonical_value:
        return canonical_value
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
    canonical_value: str,
) -> str:
    """Render concise mismatch annotation text for grouped `a:*` output."""

    chosen_prefix, chosen_value = _resolve_annotation_choice(
        source_s=source_s,
        source_p=source_p,
        canonical_value=canonical_value,
    )
    lines: list[str] = ["S: and P: differ"]
    if chosen_prefix and chosen_value:
        lines.append(f"{chosen_prefix}:{chosen_value} chosen")

    candidate_lines: list[tuple[str, str]] = [
        ("s", source_s),
        ("p", source_p),
        ("c", canonical_value),
    ]
    seen_values: set[tuple[str, str]] = set()
    for prefix, value in candidate_lines:
        normalized_value = str(value or "").strip()
        if not normalized_value:
            continue
        if chosen_value and normalized_value == chosen_value:
            continue
        pair = (prefix, normalized_value)
        if pair in seen_values:
            continue
        seen_values.add(pair)
        lines.append(f"{prefix}:{normalized_value}")

    return "\n".join(lines)


def _resolve_annotation_choice(
    *,
    source_s: str,
    source_p: str,
    canonical_value: str,
) -> tuple[str, str]:
    """Resolve which source/canonical value should be marked as chosen."""

    if canonical_value and source_p and canonical_value == source_p:
        return "p", source_p
    if canonical_value and source_s and canonical_value == source_s:
        return "s", source_s
    if canonical_value:
        return "c", canonical_value
    if source_p:
        return "p", source_p
    if source_s:
        return "s", source_s
    return "", ""


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
    """Merge project component graphs into canonical namespace-aware records."""

    def __init__(
        self, *, defaults_profile: str = "generic", cwd: Path | None = None
    ) -> None:
        """Initialize merge service and load defaults-backed policy metadata."""

        self._defaults = get_defaults(defaults_profile, cwd=cwd)
        self._policy = self._load_precedence_policy()

    @property
    def precedence_policy(self) -> MergePrecedencePolicy:
        """Return the loaded merge precedence policy."""

        return self._policy

    def merge(self, project_graph: ProjectComponentGraph) -> ComponentMergeResult:
        """Merge collected project graph into canonical namespace-rich records."""

        merged_records: dict[str, MergedReferenceRecord] = {}
        mismatch_records: list[MergeMismatchRecord] = []

        for reference in sorted(project_graph.references.keys()):
            project_record = project_graph.references[reference]
            merged_record = self._merge_reference_record(project_record)
            merged_records[reference] = merged_record
            mismatch_records.extend(merged_record.mismatches)

        metadata: dict[str, object] = {
            "precedence_profile": self._policy.profile_name,
            "schematic_biased_fields": self._policy.schematic_biased_fields,
            "pcb_biased_fields": self._policy.pcb_biased_fields,
            "inventory_biased_fields": self._policy.inventory_biased_fields,
            "mismatch_count": len(mismatch_records),
        }
        return ComponentMergeResult(
            records=merged_records,
            mismatches=tuple(mismatch_records),
            metadata=metadata,
        )

    def _load_precedence_policy(self) -> MergePrecedencePolicy:
        """Load precedence policy from defaults config with deterministic fallback."""

        configured_policy = self._defaults.get_field_precedence_policy()
        schematic_fields = configured_policy.get("schematic_biased")
        pcb_fields = configured_policy.get("pcb_biased")
        inventory_fields = configured_policy.get("inventory_biased")

        return MergePrecedencePolicy(
            profile_name=self._defaults.name,
            schematic_biased_fields=self._dedupe_fields(
                schematic_fields or _DEFAULT_SCHEMATIC_BIASED_FIELDS
            ),
            pcb_biased_fields=self._dedupe_fields(
                pcb_fields or _DEFAULT_PCB_BIASED_FIELDS
            ),
            inventory_biased_fields=self._dedupe_fields(
                inventory_fields or _DEFAULT_INVENTORY_BIASED_FIELDS
            ),
        )

    def _merge_reference_record(
        self, project_record: ProjectReferenceRecord
    ) -> MergedReferenceRecord:
        """Merge one reference record into source/canonical/annotated namespaces."""

        source_fields = self._build_source_fields(project_record)
        canonical_fields = self._build_canonical_fields(source_fields)
        mismatches = self._build_mismatches(
            project_record.reference,
            source_fields,
            canonical_fields,
        )
        annotated_fields = self._build_annotated_fields(mismatches)

        return MergedReferenceRecord(
            reference=project_record.reference,
            source_fields=source_fields,
            canonical_fields=canonical_fields,
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

    def _build_canonical_fields(self, source_fields: dict[str, str]) -> dict[str, str]:
        """Build canonical `c:*` fields using precedence policy resolution."""

        canonical_fields: dict[str, str] = {}
        for field_name in self._iter_source_field_names(source_fields):
            schematic_value = source_fields.get(f"s:{field_name}", "")
            pcb_value = source_fields.get(f"p:{field_name}", "")
            canonical_value, _ = self._resolve_canonical_value(
                field_name,
                schematic_value=schematic_value,
                pcb_value=pcb_value,
            )
            if canonical_value:
                canonical_fields[f"c:{field_name}"] = canonical_value
        return canonical_fields

    def _build_mismatches(
        self,
        reference: str,
        source_fields: dict[str, str],
        canonical_fields: dict[str, str],
    ) -> list[MergeMismatchRecord]:
        """Build structured mismatch records for source namespace disagreements."""

        mismatches: list[MergeMismatchRecord] = []
        for field_name in self._iter_source_field_names(source_fields):
            schematic_value = source_fields.get(f"s:{field_name}", "")
            pcb_value = source_fields.get(f"p:{field_name}", "")
            if not schematic_value or not pcb_value or schematic_value == pcb_value:
                continue

            _, decision_reason = self._resolve_canonical_value(
                field_name,
                schematic_value=schematic_value,
                pcb_value=pcb_value,
            )
            mismatches.append(
                MergeMismatchRecord(
                    reference=reference,
                    field_key=field_name,
                    severity="warning",
                    decision_reason=decision_reason,
                    source_values={"s": schematic_value, "p": pcb_value},
                    canonical_value=canonical_fields.get(f"c:{field_name}", ""),
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
            if mismatch.canonical_value:
                source_lines.append(f"c:{mismatch.canonical_value}")
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

        field_names.update(self._policy.schematic_biased_fields)
        field_names.update(self._policy.pcb_biased_fields)
        field_names.update(self._policy.inventory_biased_fields)
        return tuple(sorted(field_names))

    def _resolve_canonical_value(
        self,
        field_name: str,
        *,
        schematic_value: str,
        pcb_value: str,
    ) -> tuple[str, str]:
        """Resolve canonical value and decision reason for one field."""

        if schematic_value and pcb_value:
            if schematic_value == pcb_value:
                return schematic_value, "sources_agree"
            if field_name in self._policy.pcb_biased_fields:
                return pcb_value, "pcb_biased_precedence"
            if field_name in self._policy.schematic_biased_fields:
                return schematic_value, "schematic_biased_precedence"
            return schematic_value, "schematic_default_precedence"

        if schematic_value:
            return schematic_value, "schematic_only"
        if pcb_value:
            return pcb_value, "pcb_only"
        return "", "no_source_value"

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

    def _dedupe_fields(self, fields: tuple[str, ...] | list[str]) -> tuple[str, ...]:
        """Normalize and deduplicate field tokens while preserving order."""

        seen: set[str] = set()
        deduped: list[str] = []
        for field_name in fields:
            normalized = str(field_name or "").strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)
        return tuple(deduped)
