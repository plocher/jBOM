"""
Schematic Annotator.
Updates KiCad schematic files with data from inventory.
"""
from pathlib import Path
from typing import Dict

from jbom.sch_api.model import SCH


class SchematicAnnotator:
    """Updates KiCad schematic files using the Schematic API Shim."""

    def __init__(self, schematic_path: Path):
        self.schematic_path = schematic_path
        self.sch = None
        self.modified = False

    def load(self):
        """Load the schematic file."""
        self.sch = SCH.LoadSchematic(str(self.schematic_path))

    def save(self):
        """Save the schematic file."""
        if self.sch:
            self.sch.Save(str(self.schematic_path))

    def update_component(self, uuid: str, updates: Dict[str, str]) -> bool:
        """Update a component by UUID with new properties."""
        if not self.sch:
            self.load()

        found = False
        symbols = self.sch.GetSymbols()

        # Find symbol by UUID
        # Since schematic structure is flat in terms of GetSymbols (it walks all nodes),
        # we can iterate linearly.
        for symbol in symbols:
            if symbol.GetUUID() == uuid:
                self._apply_updates(symbol, updates)
                found = True
                self.modified = True
                # Don't break if duplicates exist? UUID should be unique.
                break

        return found

    def _apply_updates(self, symbol, updates: Dict[str, str]):
        """Apply property updates to symbol object."""
        for key, val in updates.items():
            if key == "Value":
                symbol.SetValue(val)
            elif key == "Footprint":
                symbol.SetFootprint(val)
            else:
                symbol.SetProperty(key, val)
