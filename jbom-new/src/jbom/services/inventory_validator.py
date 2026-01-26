"""
Inventory validation service for electrical specification consistency checking.
"""

from typing import List, Dict
from dataclasses import dataclass
from collections import defaultdict

from jbom.common.types import InventoryItem


@dataclass
class ElectricalConflictWarning:
    """Warning for IPN electrical specification conflicts."""

    ipn: str
    conflicting_fields: List[str]
    items: List[InventoryItem]
    message: str


class InventoryValidator:
    """Validates inventory for electrical specification consistency within IPN groups."""

    # Fields that should be consistent within an IPN group (electrical characteristics)
    ELECTRICAL_FIELDS = [
        "value",
        "tolerance",
        "voltage",
        "amperage",
        "wattage",
        "package",
        "category",
        "type",
    ]

    # Fields that are expected to differ between suppliers (sourcing information)
    SUPPLIER_FIELDS = [
        "manufacturer",
        "mfgpn",
        "distributor",
        "distributor_part_number",
        "lcsc",
        "priority",
        "source",
        "source_file",
        "datasheet",
    ]

    def __init__(self):
        """Initialize validator."""
        pass

    def validate_supplier_alternatives(
        self, items: List[InventoryItem]
    ) -> List[ElectricalConflictWarning]:
        """
        Validate electrical consistency within IPN supplier alternative groups.

        Args:
            items: List of inventory items to validate

        Returns:
            List of warnings for electrical specification conflicts
        """
        warnings = []
        ipn_groups = self._group_by_ipn(items)

        for ipn, group in ipn_groups.items():
            if len(group) > 1:
                conflicts = self._find_electrical_conflicts(group)
                if conflicts:
                    warning = ElectricalConflictWarning(
                        ipn=ipn,
                        conflicting_fields=conflicts,
                        items=group,
                        message=self._generate_conflict_message(ipn, conflicts, group),
                    )
                    warnings.append(warning)

        return warnings

    def _group_by_ipn(
        self, items: List[InventoryItem]
    ) -> Dict[str, List[InventoryItem]]:
        """Group inventory items by IPN."""
        groups = defaultdict(list)
        for item in items:
            if item.ipn:  # Only group items with IPNs
                groups[item.ipn].append(item)
        return dict(groups)

    def _find_electrical_conflicts(self, group: List[InventoryItem]) -> List[str]:
        """
        Find electrical specification conflicts within an IPN group.

        Args:
            group: List of items with the same IPN

        Returns:
            List of field names that have conflicts
        """
        conflicts = []

        if not group:
            return conflicts

        # Use first item as reference
        reference = group[0]

        for field in self.ELECTRICAL_FIELDS:
            reference_value = self._get_field_value(reference, field)

            # Skip empty reference values
            if not reference_value:
                continue

            for item in group[1:]:
                item_value = self._get_field_value(item, field)

                # Only flag as conflict if both values are non-empty and different
                if item_value and reference_value != item_value:
                    if field not in conflicts:
                        conflicts.append(field)
                    break

        return conflicts

    def _get_field_value(self, item: InventoryItem, field: str) -> str:
        """Get field value from inventory item, normalizing for comparison."""
        value = getattr(item, field, "") or ""
        # Normalize whitespace and case for comparison
        return str(value).strip().lower()

    def _generate_conflict_message(
        self, ipn: str, conflicts: List[str], items: List[InventoryItem]
    ) -> str:
        """Generate human-readable conflict message."""
        conflict_details = []

        for field in conflicts:
            values = []
            for item in items:
                value = getattr(item, field, "")
                source = getattr(item, "source_file", "Unknown")
                if value:
                    values.append(f"{value} ({source})")

            if values:
                conflict_details.append(f"{field}: {', '.join(values)}")

        return (
            f"IPN '{ipn}' has conflicting electrical specifications - "
            f"same IPN should have consistent characteristics. "
            f"Conflicts: {'; '.join(conflict_details)}"
        )
