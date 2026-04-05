"""POS (Position) file generation service.

This service generates component placement files from PCB data.
"""
import re
from typing import List

from jbom.common.fields import normalize_field_name
from jbom.common.pcb_types import BoardModel, PcbComponent
from jbom.common.options import PlacementOptions


class POSGenerator:
    """Service for generating position files from PCB data."""

    def __init__(self, options: PlacementOptions = None):
        """Initialize POS generator.

        Args:
            options: Placement generation options
        """
        self.options = options or PlacementOptions()

    def generate_pos_data(self, board: BoardModel) -> List[dict]:
        """Generate position data from board model.

        Args:
            board: Loaded PCB board model

        Returns:
            List of position entries
        """
        pos_entries = []

        for component in board.footprints:
            if self._should_include_component(component):
                normalized_attributes = self._normalize_component_attributes(
                    component.attributes
                )
                entry = {
                    "reference": component.reference,
                    "x_mm": component.center_x_mm,
                    "y_mm": component.center_y_mm,
                    "rotation": component.rotation_deg,
                    "side": component.side,
                    "footprint": component.footprint_name,
                    "package": component.package_token,
                    # Raw tokens (if available) to preserve author-intended formatting
                    "x_raw": component.center_x_raw,
                    "y_raw": component.center_y_raw,
                    "rotation_raw": component.rotation_raw,
                }

                # Extract additional attributes that may be requested in field selection
                # Include value if available from component attributes
                if "Value" in component.attributes:
                    entry["value"] = component.attributes["Value"]
                elif hasattr(component, "value") and component.value:
                    entry["value"] = component.value
                else:
                    entry["value"] = ""

                # Include other common attributes that might be requested
                entry["fabricator_part_number"] = normalized_attributes.get(
                    "fabricator_part_number",
                    "",
                )
                for attribute_key, attribute_value in normalized_attributes.items():
                    entry.setdefault(attribute_key, attribute_value)

                pos_entries.append(entry)
        pos_entries.sort(
            key=lambda entry: self._natural_sort_key(str(entry.get("reference", "")))
        )

        return pos_entries

    def _should_include_component(self, component: PcbComponent) -> bool:
        """Determine if component should be included in position file."""
        # Apply SMD-only filter if requested
        if self.options.smd_only:
            mount_type = component.attributes.get("mount_type", "")
            if mount_type != "smd":
                return False

        # Apply layer filter if requested
        if self.options.layer_filter:
            if component.side.upper() != self.options.layer_filter:
                return False
        if self._is_excluded_from_position_files(component):
            return False

        return True

    def _is_excluded_from_position_files(self, component: PcbComponent) -> bool:
        """Return True if PCB metadata marks the component as position-file excluded."""

        normalized_attributes = self._normalize_component_attributes(
            component.attributes
        )
        return any(
            self._is_truthy_marker(normalized_attributes.get(flag_name))
            for flag_name in ("exclude_from_pos_files", "exclude_from_position_files")
        )

    @staticmethod
    def _is_truthy_marker(value: object) -> bool:
        """Return True when a marker value should be interpreted as enabled."""

        if isinstance(value, bool):
            return value
        normalized = str(value or "").strip().lower()
        if not normalized:
            return False
        return normalized in {"1", "true", "t", "yes", "y", "x"}

    @staticmethod
    def _natural_sort_key(reference: str) -> list[object]:
        """Return natural sort key for component references (R1, R2, R10)."""

        parts = re.split(r"(\d+)", reference)
        result: list[object] = []
        for part in parts:
            if part.isdigit():
                result.append(int(part))
            else:
                result.append(part)
        return result

    @staticmethod
    def _normalize_component_attributes(attributes: dict[str, str]) -> dict[str, str]:
        """Normalize component attributes to canonical field IDs."""

        normalized: dict[str, str] = {}
        for key, value in attributes.items():
            normalized_key = normalize_field_name(key)
            if not normalized_key:
                continue
            normalized[normalized_key] = value

        return normalized
