"""POS (Position) file generation service.

This service generates component placement files from PCB data.
"""
from typing import List

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
                entry = {
                    "reference": component.reference,
                    "x_mm": component.center_x_mm,
                    "y_mm": component.center_y_mm,
                    "rotation": component.rotation_deg,
                    "side": component.side,
                    "footprint": component.footprint_name,
                    "package": component.package_token,
                }
                pos_entries.append(entry)

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

        return True
