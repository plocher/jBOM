"""Pure BOM generator service that converts components to BOM data structures."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from jbom.common.types import Component


@dataclass
class BOMEntry:
    """Aggregated BOM line item."""

    references: List[str]  # Component references ["R1", "R2", "R3"]
    value: str  # Component value
    footprint: str  # Footprint identifier
    quantity: int  # Total quantity needed
    lib_id: str = ""  # Library ID for component type
    attributes: Dict[str, Any] = field(default_factory=dict)  # Merged attributes

    @property
    def references_string(self) -> str:
        """Comma-separated string of references for display."""
        return ", ".join(BOMGenerator._natural_sort_references(self.references))


@dataclass
class BOMData:
    """Complete BOM dataset."""

    project_name: str  # Project name for output files
    entries: List[BOMEntry]  # Aggregated BOM entries
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata

    @property
    def total_components(self) -> int:
        """Total number of individual components in the BOM."""
        return sum(entry.quantity for entry in self.entries)

    @property
    def total_line_items(self) -> int:
        """Total number of unique line items in the BOM."""
        return len(self.entries)


class BOMGenerator:
    """Pure service that generates BOM data from component lists."""

    def __init__(self, aggregation_strategy: str = "value_footprint"):
        """Initialize BOM generator.

        Args:
            aggregation_strategy: How to group components ("value_footprint", "value_only", etc.)
        """
        self.aggregation_strategy = aggregation_strategy

    def generate_bom_data(
        self,
        components: List[Component],
        project_name: str = "Project",
        filters: Optional[Dict[str, Any]] = None,
    ) -> BOMData:
        """Generate BOM data from component list.

        Args:
            components: List of KiCad Component objects
            project_name: Project name for metadata
            filters: Optional filtering criteria

        Returns:
            BOMData object with aggregated entries
        """
        # Apply filters
        filtered_components = self._apply_filters(components, filters or {})

        # Aggregate components into BOM entries
        entries = self._aggregate_components(filtered_components)

        # Sort entries by first reference for consistent output
        entries.sort(key=lambda e: e.references[0])

        return BOMData(
            project_name=project_name,
            entries=entries,
            metadata={
                "aggregation_strategy": self.aggregation_strategy,
                "total_input_components": len(components),
                "filtered_components": len(filtered_components),
            },
        )

    def _apply_filters(
        self, components: List[Component], filters: Dict[str, Any]
    ) -> List[Component]:
        """Apply filtering criteria to components."""
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

    def _aggregate_components(self, components: List[Component]) -> List[BOMEntry]:
        """Aggregate components into BOM entries."""
        # Group components by aggregation key
        groups: Dict[tuple, List[Component]] = {}

        for component in components:
            key = self._get_aggregation_key(component)
            if key not in groups:
                groups[key] = []
            groups[key].append(component)

        # Create BOM entries from groups
        entries = []
        for component_group in groups.values():
            entry = self._create_bom_entry(component_group)
            entries.append(entry)

        return entries

    def _get_aggregation_key(self, component: Component) -> tuple:
        """Get aggregation key for grouping components."""
        if self.aggregation_strategy == "value_footprint":
            return (component.value, component.footprint)
        elif self.aggregation_strategy == "value_only":
            return (component.value,)
        elif self.aggregation_strategy == "lib_id_value":
            return (component.lib_id, component.value)
        else:
            # Default to value_footprint
            return (component.value, component.footprint)

    def _create_bom_entry(self, components: List[Component]) -> BOMEntry:
        """Create a BOM entry from a group of similar components."""
        # Use the first component as the base
        base_component = components[0]

        # Collect all references
        references = [comp.reference for comp in components]

        # Merge properties from all components
        merged_attributes = {}
        for comp in components:
            for key, value in comp.properties.items():
                if value and value.strip():  # Only add non-empty values
                    if key not in merged_attributes or not merged_attributes[key]:
                        merged_attributes[key] = value.strip()

        return BOMEntry(
            references=references,
            value=base_component.value,
            footprint=base_component.footprint,
            lib_id=base_component.lib_id,
            quantity=len(references),
            attributes=merged_attributes,
        )

    @staticmethod
    def _natural_sort_references(references: List[str]) -> List[str]:
        """Sort component references in natural order (R1, R2, R10 not R1, R10, R2)."""
        import re

        def natural_key(ref: str):
            # Split reference into prefix and numeric parts
            # E.g., "R10" -> [("R", 0), ("", 10)]
            parts = re.split(r"(\d+)", ref)
            result = []
            for part in parts:
                if part.isdigit():
                    result.append(int(part))
                else:
                    result.append(part)
            return result

        return sorted(references, key=natural_key)
