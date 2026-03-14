"""Project component collection scaffolding for canonical merge pipeline.

Phase-1 goal:
- collect schematic and PCB component records keyed by reference designator
- expose a stable, typed contract for downstream merge services
- keep behavior non-breaking by not changing existing BOM/audit outputs
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from jbom.common.pcb_types import PcbComponent
from jbom.common.types import Component
from jbom.services.pcb_reader import DefaultKiCadReaderService
from jbom.services.schematic_reader import SchematicReader


@dataclass(frozen=True)
class ProjectReferenceRecord:
    """Raw project records grouped by one reference designator."""

    reference: str
    schematic_components: tuple[Component, ...] = tuple()
    pcb_components: tuple[PcbComponent, ...] = tuple()


@dataclass(frozen=True)
class ProjectComponentGraph:
    """Canonical raw project graph keyed by reference designator."""

    references: dict[str, ProjectReferenceRecord] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def reference_count(self) -> int:
        """Return the number of unique reference keys in this graph."""

        return len(self.references)


class ProjectComponentCollector:
    """Collect schematic + PCB project records into a reference-keyed graph."""

    def __init__(
        self,
        *,
        schematic_reader: SchematicReader | None = None,
        pcb_reader: DefaultKiCadReaderService | None = None,
    ) -> None:
        """Initialize collector with injectable readers for testability."""

        self._schematic_reader = schematic_reader or SchematicReader()
        self._pcb_reader = pcb_reader or DefaultKiCadReaderService()

    def collect(
        self,
        *,
        schematic_components: Sequence[Component],
        pcb_components: Sequence[PcbComponent],
        schematic_files: Sequence[Path] | None = None,
        pcb_file: Path | None = None,
    ) -> ProjectComponentGraph:
        """Build a project graph from already-loaded schematic/PCB components."""
        schematic_by_reference: dict[str, list[Component]] = {}
        pcb_by_reference: dict[str, list[PcbComponent]] = {}

        for component in schematic_components:
            reference = self._normalize_reference(component.reference)
            if not reference:
                continue
            schematic_group = schematic_by_reference.setdefault(reference, [])
            schematic_group.append(component)

        for footprint in pcb_components:
            reference = self._normalize_reference(footprint.reference)
            if not reference:
                continue
            pcb_group = pcb_by_reference.setdefault(reference, [])
            pcb_group.append(footprint)

        sorted_references = sorted(
            set(schematic_by_reference.keys()).union(pcb_by_reference.keys())
        )
        reference_records: dict[str, ProjectReferenceRecord] = {}
        for reference in sorted_references:
            schematic_group = tuple(schematic_by_reference.get(reference, []))
            pcb_group = tuple(pcb_by_reference.get(reference, []))
            reference_records[reference] = ProjectReferenceRecord(
                reference=reference,
                schematic_components=schematic_group,
                pcb_components=pcb_group,
            )

        metadata: dict[str, object] = {
            "schematic_component_count": len(schematic_components),
            "pcb_component_count": len(pcb_components),
            "reference_count": len(reference_records),
        }
        if schematic_files:
            metadata["schematic_files"] = tuple(str(path) for path in schematic_files)
        if pcb_file is not None:
            metadata["pcb_file"] = str(pcb_file)

        return ProjectComponentGraph(references=reference_records, metadata=metadata)

    def collect_from_files(
        self,
        *,
        schematic_files: Sequence[Path],
        pcb_file: Path | None = None,
    ) -> ProjectComponentGraph:
        """Load project files and collect a raw reference-keyed component graph."""

        schematic_components: list[Component] = []
        for schematic_file in schematic_files:
            loaded = self._schematic_reader.load_components(schematic_file)
            schematic_components.extend(loaded)

        pcb_components: list[PcbComponent] = []
        if pcb_file is not None and pcb_file.exists():
            board = self._pcb_reader.read_pcb_file(pcb_file)
            pcb_components = list(board.footprints)

        return self.collect(
            schematic_components=schematic_components,
            pcb_components=pcb_components,
            schematic_files=schematic_files,
            pcb_file=pcb_file,
        )

    def _normalize_reference(self, reference: str) -> str:
        """Normalize and validate reference tokens at intake boundaries."""

        return str(reference or "").strip()
