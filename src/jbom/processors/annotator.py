"""
Schematic Annotator.
Updates KiCad schematic files with data from inventory.
"""
from pathlib import Path
from typing import Dict
import sexpdata
from sexpdata import Symbol

from jbom.common.sexp_parser import load_kicad_file


class SchematicAnnotator:
    """Updates KiCad schematic files."""

    def __init__(self, schematic_path: Path):
        self.schematic_path = schematic_path
        self.sexp = None
        self.modified = False

    def load(self):
        """Load the schematic file."""
        self.sexp = load_kicad_file(self.schematic_path)

    def save(self):
        """Save the schematic file."""
        if not self.sexp:
            return

        # We need a custom dumper or use sexpdata.dumps
        # Warning: sexpdata.dumps produces minified output.
        with open(self.schematic_path, "w", encoding="utf-8") as f:
            f.write(sexpdata.dumps(self.sexp))

    def update_component(self, uuid: str, updates: Dict[str, str]) -> bool:
        """Update a component by UUID with new properties."""
        if not self.sexp:
            self.load()

        found = False
        # Walk nodes to find symbol with matching UUID
        # Note: sexp structure is recursive lists
        found = self._walk_and_update(self.sexp, uuid, updates)
        if found:
            self.modified = True
        return found

    def _walk_and_update(
        self, node: list, target_uuid: str, updates: Dict[str, str]
    ) -> bool:
        """Recursive walk to find and update symbol."""
        if not isinstance(node, list) or not node:
            return False

        tag = node[0]
        # Check if this is a symbol node
        if tag == Symbol("symbol"):
            # Check UUID
            current_uuid = self._get_uuid(node)
            if current_uuid == target_uuid:
                self._apply_updates(node, updates)
                return True

        # Recurse children
        for child in node:
            if isinstance(child, list):
                if self._walk_and_update(child, target_uuid, updates):
                    return True
        return False

    def _get_uuid(self, node: list) -> str:
        """Extract UUID from symbol node."""
        for item in node[1:]:
            if isinstance(item, list) and len(item) >= 2:
                if item[0] == Symbol("uuid"):
                    return item[1]
        return ""

    def _apply_updates(self, node: list, updates: Dict[str, str]):
        """Apply property updates to symbol node."""
        # Updates keys: Value, Footprint, LCSC, etc.
        # Properties are (property "Key" "Val" ...)

        existing_props = set()

        # Update existing properties
        for item in node[1:]:
            if isinstance(item, list) and len(item) >= 3:
                if item[0] == Symbol("property"):
                    key = item[1]
                    if key in updates:
                        # Update the value
                        item[2] = updates[key]
                        existing_props.add(key)

        # Add new properties
        for key, val in updates.items():
            if key not in existing_props and key not in [
                "Reference",
                "Value",
                "Footprint",
            ]:
                # Add new property
                # We need to clone structure or create new one.
                # Use a default structure for new properties
                new_prop = [
                    Symbol("property"),
                    key,
                    val,
                    [Symbol("id"), 99],  # Dummy ID, KiCad might reassign
                    [Symbol("at"), 0, 0, 0],  # Hidden at origin
                    [
                        Symbol("effects"),
                        [Symbol("font"), [Symbol("size"), 1.27, 1.27]],
                        [Symbol("hide"), Symbol("yes")],
                    ],
                ]
                node.append(new_prop)
            elif key not in existing_props and key in ["Value", "Footprint"]:
                # These should usually exist, but if missing, add them?
                # Value and Footprint are mandatory properties in KiCad symbols usually.
                pass
