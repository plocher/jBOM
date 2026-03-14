"""Component merge scaffolding for canonical namespace-aware workflows.

Phase-1 scope:
- define stable input/output contracts for project-component merge
- load field precedence policy metadata from defaults configuration
- provide deterministic placeholder merge + mismatch artifacts
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
    """Phase-1 placeholder merge service for canonical namespace contracts."""

    def __init__(
        self, *, defaults_profile: str = "generic", cwd: Path | None = None
    ) -> None:
        """Initialize merge scaffolding and load defaults-backed policy metadata."""

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
        canonical_fields = self._build_canonical_fields(project_record, source_fields)
        mismatches = self._build_mismatches(project_record, canonical_fields)
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

        schematic_component = (
            project_record.schematic_components[0]
            if project_record.schematic_components
            else None
        )
        pcb_component = (
            project_record.pcb_components[0] if project_record.pcb_components else None
        )

        if schematic_component is not None:
            if schematic_component.value:
                source_fields["s:value"] = schematic_component.value
            if schematic_component.footprint:
                source_fields["s:footprint"] = schematic_component.footprint

        if pcb_component is not None:
            if pcb_component.footprint_name:
                source_fields["p:footprint"] = pcb_component.footprint_name
            if pcb_component.package_token:
                source_fields["p:package"] = pcb_component.package_token

        return source_fields

    def _build_canonical_fields(
        self,
        project_record: ProjectReferenceRecord,
        source_fields: dict[str, str],
    ) -> dict[str, str]:
        """Build canonical `c:*` placeholder fields from source namespaces."""

        canonical_fields: dict[str, str] = {}

        schematic_component = (
            project_record.schematic_components[0]
            if project_record.schematic_components
            else None
        )
        pcb_component = (
            project_record.pcb_components[0] if project_record.pcb_components else None
        )

        if schematic_component is not None and schematic_component.value:
            canonical_fields["c:value"] = schematic_component.value

        schematic_footprint = source_fields.get("s:footprint", "")
        pcb_footprint = source_fields.get("p:footprint", "")
        if (
            schematic_footprint
            and pcb_footprint
            and schematic_footprint != pcb_footprint
        ):
            if "footprint" in self._policy.pcb_biased_fields:
                canonical_fields["c:footprint"] = pcb_footprint
            else:
                canonical_fields["c:footprint"] = schematic_footprint
        elif schematic_footprint:
            canonical_fields["c:footprint"] = schematic_footprint
        elif pcb_footprint:
            canonical_fields["c:footprint"] = pcb_footprint
        elif pcb_component is not None and pcb_component.footprint_name:
            canonical_fields["c:footprint"] = pcb_component.footprint_name

        if pcb_component is not None and pcb_component.package_token:
            canonical_fields["c:package"] = pcb_component.package_token

        return canonical_fields

    def _build_mismatches(
        self,
        project_record: ProjectReferenceRecord,
        canonical_fields: dict[str, str],
    ) -> list[MergeMismatchRecord]:
        """Build placeholder mismatch records for explicit source disagreement."""

        mismatches: list[MergeMismatchRecord] = []
        if not project_record.schematic_components or not project_record.pcb_components:
            return mismatches

        schematic_footprint = project_record.schematic_components[0].footprint
        pcb_footprint = project_record.pcb_components[0].footprint_name
        if (
            schematic_footprint
            and pcb_footprint
            and schematic_footprint != pcb_footprint
        ):
            mismatches.append(
                MergeMismatchRecord(
                    reference=project_record.reference,
                    field_key="footprint",
                    severity="warning",
                    decision_reason="phase1_placeholder_precedence_resolution",
                    source_values={"s": schematic_footprint, "p": pcb_footprint},
                    canonical_value=canonical_fields.get("c:footprint", ""),
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
