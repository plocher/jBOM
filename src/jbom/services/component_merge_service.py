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
