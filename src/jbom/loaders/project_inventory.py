"""
Loader for generating inventory from KiCad project components.
"""

from typing import List, Tuple, Dict, Set

from jbom.common.types import Component, InventoryItem, DEFAULT_PRIORITY
from jbom.processors.component_types import get_component_type
from jbom.common.constants import CommonFields
from jbom.common.packages import PackageType


class ProjectInventoryLoader:
    """Generates inventory items from project components."""

    def __init__(self, components: List[Component]):
        """Initialize with list of components from schematic."""
        self.components = components
        self.inventory: List[InventoryItem] = []
        self.inventory_fields: Set[str] = set()

    def load(self) -> Tuple[List[InventoryItem], List[str]]:
        """Generate inventory items from components.

        Returns:
            Tuple of (inventory items list, field names list)
        """
        # Group components by Value, Footprint, and relevant properties to deduplicate
        grouped_components: Dict[str, List[Component]] = {}

        for comp in self.components:
            # Skip components not in BOM or DNP if desired?
            # Usually we want all components to be in inventory even if DNP in this specific project,
            # but if they are DNP, maybe they aren't "inventory candidates"?
            # For now, include everything.

            key = self._generate_group_key(comp)
            if key not in grouped_components:
                grouped_components[key] = []
            grouped_components[key].append(comp)

        self.inventory = []
        # Standard fields that we always want
        self.inventory_fields = {
            "IPN",
            "Category",
            "Value",
            "Package",
            "Description",
            "Keywords",
            "Manufacturer",
            "MFGPN",
            "Datasheet",
            "LCSC",
            "UUID",
        }

        for key, comps in grouped_components.items():
            # Use the first component as representative
            representative = comps[0]
            # Collect all UUIDs in the group
            uuids = [c.uuid for c in comps if c.uuid]
            uuid_str = ",".join(uuids)

            item = self._create_inventory_item(representative, uuid_str)
            self.inventory.append(item)

            # Add any extra fields found in properties
            for prop in representative.properties.keys():
                self.inventory_fields.add(prop)

        return self.inventory, sorted(list(self.inventory_fields))

    def _generate_group_key(self, component: Component) -> str:
        """Generate a unique key for grouping components."""
        # We group by Value, Footprint, and relevant properties to deduplicate
        # We also need to consider properties that affect part selection (Tolerance, Voltage, etc.)

        # Add key properties to the group key
        props = component.properties
        prop_key = f"{props.get('Tolerance','')}|{props.get('Voltage','')}|{props.get('Rating','')}"

        return f"{component.value}|{component.footprint}|{component.lib_id}|{prop_key}"

    def _create_inventory_item(
        self, component: Component, uuid_str: str = ""
    ) -> InventoryItem:
        """Create an InventoryItem from a Component."""

        # Determine category
        comp_type = get_component_type(component.lib_id, component.footprint)
        category = comp_type if comp_type else "Unknown"

        # Extract package from footprint
        package = self._extract_package(component.footprint)

        # Generate a pseudo-IPN
        # We can use the Value and Package as a base
        ipn = f"{component.value}_{package}" if package else component.value
        # Cleanup IPN
        ipn = ipn.replace(" ", "_").upper()

        # Map properties to InventoryItem fields
        props = component.properties

        return InventoryItem(
            ipn=ipn,
            keywords=props.get("Keywords", ""),
            category=category,
            description=props.get(
                "Description", f"{category} {component.value} {package}"
            ),
            smd=props.get("SMD", ""),  # Maybe infer from footprint?
            value=component.value,
            type=props.get("Type", ""),
            tolerance=props.get(CommonFields.TOLERANCE, props.get("Tolerance", "")),
            voltage=props.get(CommonFields.VOLTAGE, props.get("Voltage", "")),
            amperage=props.get(CommonFields.AMPERAGE, props.get("Amperage", "")),
            wattage=props.get(CommonFields.WATTAGE, props.get("Wattage", "")),
            lcsc=props.get("LCSC", ""),
            manufacturer=props.get("Manufacturer", ""),
            mfgpn=props.get("MFGPN", props.get("MPN", "")),
            datasheet=props.get("Datasheet", ""),
            package=package,
            uuid=uuid_str,
            priority=DEFAULT_PRIORITY,
            source="Project",
            raw_data=props,
        )

    def _extract_package(self, footprint: str) -> str:
        """Extract package name from footprint."""
        if not footprint:
            return ""

        fp_lower = footprint.lower()

        # Simple extraction logic mirroring InventoryMatcher._extract_package_from_footprint
        # but simplified since we don't have an inventory to match against.
        # We just want to extract a recognizable package name.

        for pattern in sorted(PackageType.SMD_PACKAGES, key=len, reverse=True):
            if pattern in fp_lower:
                return pattern

        # If no SMD package found, maybe return the whole footprint name or last part?
        # Often footprint names are like "Resistor_SMD:R_0603_1608Metric"
        # We might want "0603" or "R_0603_1608Metric"

        if ":" in footprint:
            return footprint.split(":")[-1]

        return footprint
