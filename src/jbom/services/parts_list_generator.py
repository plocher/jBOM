"""Pure Parts List generator service with electro-mechanical aggregation."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from jbom.common.types import Component
from jbom.common.component_filters import apply_component_filters


@dataclass
class PartsListEntry:
    """Aggregated component entry for parts list output."""

    refs: List[str]  # Component references collapsed into one row
    value: str  # Component value
    footprint: str  # Footprint identifier
    package: str = ""  # Normalized package identity (falls back to footprint)
    part_type: str = ""  # Electrical type (e.g., X7R, Thick Film)
    tolerance: str = ""  # Tolerance field if present
    voltage: str = ""  # Voltage rating if present
    dielectric: str = ""  # Dielectric field if present
    lib_id: str = ""  # Library ID for component type
    attributes: Dict[str, Any] = field(default_factory=dict)  # Component properties

    @property
    def refs_csv(self) -> str:
        """Return comma-separated reference designators for CSV output."""
        return ",".join(self.refs)


@dataclass
class PartsListData:
    """Complete Parts List dataset."""

    project_name: str  # Project name for output files
    entries: List[PartsListEntry]  # Aggregated parts entries
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata

    @property
    def total_components(self) -> int:
        """Total number of component references represented in the parts list."""
        return sum(len(entry.refs) for entry in self.entries)

    @property
    def total_groups(self) -> int:
        """Total number of electro-mechanical groups in the parts list."""
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
            PartsListData object with electro-mechanically aggregated entries
        """
        # Apply filters using common logic
        filtered_components = apply_component_filters(components, filters or {})
        # Create grouped entries by electro-mechanical identity
        entries = self._create_grouped_entries(filtered_components)

        # Sort groups by first reference in natural order
        entries.sort(key=lambda e: self._natural_sort_key(e.refs[0] if e.refs else ""))

        return PartsListData(
            project_name=project_name,
            entries=entries,
            metadata={
                "total_input_components": len(components),
                "filtered_components": len(filtered_components),
                "aggregated_groups": len(entries),
            },
        )

    def _create_grouped_entries(
        self, components: List[Component]
    ) -> List[PartsListEntry]:
        """Create aggregated PartsListEntry objects from unique components.

        Multi-unit components (e.g. dual op-amps) produce multiple symbol
        instances with the same reference. We deduplicate by reference so
        each physical component appears only once.
        """
        unique_components: Dict[str, Component] = {}
        for component in components:
            unique_components.setdefault(component.reference, component)

        grouped_components: Dict[
            tuple[str, str, str, str, str, str], List[Component]
        ] = {}
        for component in unique_components.values():
            key = self._electro_mechanical_key(component)
            grouped_components.setdefault(key, []).append(component)

        entries: List[PartsListEntry] = []
        for group in grouped_components.values():
            representative = group[0]
            refs = sorted(
                [component.reference for component in group],
                key=self._natural_sort_key,
            )
            entry = PartsListEntry(
                refs=refs,
                value=representative.value,
                footprint=representative.footprint,
                package=self._component_property(
                    representative, ["Package"], fallback=representative.footprint
                ),
                part_type=self._component_property(representative, ["Type"]),
                tolerance=self._component_property(representative, ["Tolerance"]),
                voltage=self._component_property(representative, ["Voltage", "V"]),
                dielectric=self._component_property(representative, ["Dielectric"]),
                lib_id=representative.lib_id,
                attributes=representative.properties.copy(),
            )
            entries.append(entry)

        return entries

    def _electro_mechanical_key(
        self, component: Component
    ) -> tuple[str, str, str, str, str, str]:
        """Create normalized grouping key for electro-mechanical identity."""
        value = component.value.strip().casefold()
        package = (
            self._component_property(
                component, ["Package"], fallback=component.footprint
            )
            .strip()
            .casefold()
        )
        part_type = self._component_property(component, ["Type"]).strip().casefold()
        tolerance = (
            self._component_property(component, ["Tolerance"]).strip().casefold()
        )
        voltage = (
            self._component_property(component, ["Voltage", "V"]).strip().casefold()
        )
        dielectric = (
            self._component_property(component, ["Dielectric"]).strip().casefold()
        )
        return (value, package, part_type, tolerance, voltage, dielectric)

    def _component_property(
        self, component: Component, keys: List[str], fallback: str = ""
    ) -> str:
        """Fetch a component property by case-insensitive key with fallback."""
        property_map = {k.casefold(): v for k, v in component.properties.items()}
        for key in keys:
            value = property_map.get(key.casefold())
            if value:
                return value
        return fallback

    def _natural_sort_key(self, reference: str) -> List[Any]:
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
