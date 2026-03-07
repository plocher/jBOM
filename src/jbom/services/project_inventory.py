"""Loader for generating inventory from KiCad project components."""

from typing import List, Tuple, Dict, Set

from jbom.common.component_classification import normalize_component_type
from jbom.common.component_id import make_component_id
from jbom.common.types import Component, InventoryItem, DEFAULT_PRIORITY
from jbom.common.component_utils import (
    derive_package_from_footprint,
    get_component_type,
)
from jbom.common.constants import CommonFields
from jbom.common.packages import PackageType
from jbom.common.value_parsing import decode_typed_parametric


class ProjectInventoryGenerator:
    """Generates inventory items from project components."""

    def __init__(self, components: List[Component]):
        """Initialize with list of components from schematic."""
        self.components = components
        self.inventory: List[InventoryItem] = []
        self.inventory_fields: Set[str] = set()

    def load(self) -> Tuple[List[InventoryItem], List[str]]:
        """Generate COMPONENT rows from project requirements.

        Returns:
            Tuple of (inventory items list, field names list)
        """
        # Group by explicit requirement identity so identical requirements collapse.
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
            "RowType",
            "ComponentID",
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
            "footprint_full",
            "symbol_name",
            "ki_keywords",
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

        # Include typed parametric columns when at least one item has a value.
        for attr, field in (
            ("resistance", "Resistance"),
            ("capacitance", "Capacitance"),
            ("inductance", "Inductance"),
        ):
            if any(getattr(item, attr) is not None for item in self.inventory):
                self.inventory_fields.add(field)

        return self.inventory, sorted(list(self.inventory_fields))

    def load_per_instance(self) -> Tuple[List[InventoryItem], List[str]]:
        """Generate one COMPONENT row per component instance for --per-instance output.

        Returns:
            Tuple of (inventory items list, field names list)
        """
        self.inventory = []
        self.inventory_fields = {
            "RowType",
            "ComponentID",
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
            "Footprint",
            "Symbol",
            "footprint_full",
            "symbol_name",
            "ki_keywords",
        }

        for component in self.components:
            item = self._create_inventory_item(component, component.uuid)
            item.raw_data = dict(item.raw_data)
            item.raw_data["Footprint"] = component.footprint
            item.raw_data["Symbol"] = component.lib_id
            item.raw_data["footprint_full"] = component.footprint
            item.raw_data["symbol_name"] = component.lib_id
            item.raw_data["ki_keywords"] = component.properties.get("Keywords", "")

            self.inventory.append(item)
            for prop in component.properties.keys():
                self.inventory_fields.add(prop)

        return self.inventory, sorted(list(self.inventory_fields))

    def _generate_group_key(self, component: Component) -> str:
        """Generate deterministic requirement identity via make_component_id().

        Always delegates to ``make_component_id`` — never constructs the
        ComponentID string directly.
        """
        category_raw = (
            get_component_type(component.lib_id, component.footprint) or "UNK"
        )
        category = normalize_component_type(category_raw)
        props = component.properties or {}

        return make_component_id(
            category=category,
            value=component.value or "",
            package=self._extract_package(component.footprint),
            tolerance=props.get(CommonFields.TOLERANCE, props.get("Tolerance", "")),
            voltage=props.get(CommonFields.VOLTAGE, props.get("Voltage", "")),
            amperage=props.get(CommonFields.AMPERAGE, props.get("Amperage", "")),
            wattage=props.get(CommonFields.WATTAGE, props.get("Wattage", "")),
            component_type=props.get("Type", ""),
        )

    def _create_inventory_item(
        self, component: Component, uuid_str: str = ""
    ) -> InventoryItem:
        """Create an InventoryItem from a Component."""

        # Determine category
        comp_type = get_component_type(component.lib_id, component.footprint)
        category = comp_type if comp_type else "Unknown"

        # Extract package from footprint
        package = self._extract_package(component.footprint)

        # Map properties to InventoryItem fields
        props = component.properties

        # IPN must only come from an explicit 'IPN' schematic property.
        # jBOM has no knowledge of IPN structure or naming conventions.
        # Leave blank so the user can assign their own IPNs.
        ipn = props.get("IPN", "")

        component_id = self._generate_group_key(component)
        # Decode typed parametric fields from schematic properties.
        # props acts as the row: it may carry an explicit Resistance/Capacitance/
        # Inductance property; Value is the fallback.
        row_for_decode: dict[str, str] = dict(props)
        return InventoryItem(
            row_type="COMPONENT",
            component_id=component_id,
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
            voltage=props.get(
                CommonFields.VOLTAGE,
                props.get("Voltage", props.get("V", "")),
            ),
            amperage=props.get(
                CommonFields.AMPERAGE,
                props.get("Current", props.get("Amperage", props.get("A", ""))),
            ),
            wattage=props.get(
                CommonFields.WATTAGE,
                props.get("Power", props.get("Wattage", props.get("W", ""))),
            ),
            lcsc=props.get("LCSC", ""),
            manufacturer=props.get("Manufacturer", ""),
            mfgpn=props.get("MFGPN", props.get("MPN", "")),
            datasheet=props.get("Datasheet", ""),
            package=package,
            uuid=uuid_str,
            priority=DEFAULT_PRIORITY,
            resistance=decode_typed_parametric("RES", component.value, row_for_decode),
            capacitance=decode_typed_parametric("CAP", component.value, row_for_decode),
            inductance=decode_typed_parametric("IND", component.value, row_for_decode),
            source="Project",
            raw_data={
                **props,
                "RowType": "COMPONENT",
                "ComponentID": component_id,
                "footprint_full": component.footprint,
                "symbol_name": component.lib_id,
                "ki_keywords": props.get("Keywords", ""),
            },
        )

    def _extract_package(self, footprint: str) -> str:
        """Extract package name from footprint.

        Tries SMD package pattern matching first for a clean package code
        (e.g. '0603'), then falls back to stripping the library prefix via
        :func:`derive_package_from_footprint`.
        """
        if not footprint:
            return ""

        fp_lower = footprint.lower()

        for pattern in sorted(PackageType.SMD_PACKAGES, key=len, reverse=True):
            if pattern in fp_lower:
                return pattern

        return derive_package_from_footprint(footprint)
