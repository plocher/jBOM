"""Pure Parts List generator service that converts components to individual entries."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from jbom.common.types import Component


@dataclass
class PartsListEntry:
    """Individual component entry for parts list (1:1 with components)."""

    reference: str  # Single component reference (e.g., "R1")
    value: str  # Component value
    footprint: str  # Footprint identifier
    lib_id: str = ""  # Library ID for component type
    attributes: Dict[str, Any] = field(default_factory=dict)  # Component properties


@dataclass
class PartsListData:
    """Complete Parts List dataset."""

    project_name: str  # Project name for output files
    entries: List[PartsListEntry]  # Individual parts list entries (no aggregation)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata

    @property
    def total_components(self) -> int:
        """Total number of components in the parts list."""
        return len(self.entries)


class PartsListGenerator:
    """Pure service that generates Parts List data from component lists."""

    def __init__(self):
        """Initialize Parts List generator."""
        pass

    def generate_parts_list_data(
        self,
        components: List[Component],
        project_name: str = "Project",
        filters: Optional[Dict[str, Any]] = None,
    ) -> PartsListData:
        """Generate Parts List data from component list.

        Args:
            components: List of KiCad Component objects
            project_name: Project name for metadata
            filters: Optional filtering criteria

        Returns:
            PartsListData object with individual component entries
        """
        # Apply filters (same logic as BOMGenerator)
        filtered_components = self._apply_filters(components, filters or {})

        # Create individual entries (no aggregation)
        entries = self._create_individual_entries(filtered_components)

        # Sort entries by reference in natural order
        entries.sort(key=lambda e: self._natural_sort_key(e.reference))

        return PartsListData(
            project_name=project_name,
            entries=entries,
            metadata={
                "total_input_components": len(components),
                "filtered_components": len(filtered_components),
            },
        )

    def _apply_filters(
        self, components: List[Component], filters: Dict[str, Any]
    ) -> List[Component]:
        """Apply filtering criteria to components (same as BOMGenerator)."""
        filtered = []

        # Default: exclude DNP and components not in BOM
        exclude_dnp = filters.get("exclude_dnp", True)
        include_only_bom = filters.get("include_only_bom", True)

        for component in components:
            # Apply DNP filter
            if exclude_dnp and component.dnp:
                continue

            # Apply include only BOM components filter
            if include_only_bom and not component.in_bom:
                continue

            # Skip power symbols (references starting with #)
            if component.reference.startswith("#"):
                continue

            filtered.append(component)

        return filtered

    def _create_individual_entries(
        self, components: List[Component]
    ) -> List[PartsListEntry]:
        """Create individual PartsListEntry objects (1:1 with components)."""
        entries = []

        for component in components:
            entry = PartsListEntry(
                reference=component.reference,
                value=component.value,
                footprint=component.footprint,
                lib_id=component.lib_id,
                attributes=component.properties.copy(),
            )
            entries.append(entry)

        return entries

    def _natural_sort_key(self, reference: str):
        """Generate natural sort key for references (R1, R2, R10 not R1, R10, R2)."""
        import re

        # Split reference into prefix and numeric parts
        # E.g., "R10" -> ["R", "10"] -> ["R", 10]
        parts = re.split(r"(\d+)", reference)
        result = []
        for part in parts:
            if part.isdigit():
                result.append(int(part))
            else:
                result.append(part)
        return result
