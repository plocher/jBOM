"""
KiCad Schematic API Shim.

This module provides an object-oriented API for manipulating KiCad schematics,
modeled after the Pcbnew API. It currently uses S-expression parsing as a backend,
but is designed to be replaced by the official KiCad Python API when available.
"""
from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Optional
import sexpdata
from sexpdata import Symbol as SexpSymbol

from jbom.common.sexp_parser import load_kicad_file


class SCH:
    """Namespace class to mimic pcbnew module."""

    @staticmethod
    def LoadSchematic(filename: str) -> Schematic:
        return Schematic(filename)


class Schematic:
    """Represents a KiCad schematic file."""

    def __init__(self, filename: str):
        self._filename = filename
        self._sexp = load_kicad_file(Path(filename))
        self._symbols: List[Symbol] = []
        self._load_symbols()

    def GetFileName(self) -> str:
        return self._filename

    def Save(self, filename: str) -> bool:
        """Save the schematic to file."""
        try:
            # Reconstruct S-exp from objects if needed, but currently objects hold references to sexp nodes
            # So modifying objects modifies self._sexp tree.
            # sexpdata.dumps is minified. We accept this for now or need a pretty printer.
            # For this shim, we stick to sexpdata.dumps.
            with open(filename, "w", encoding="utf-8") as f:
                f.write(sexpdata.dumps(self._sexp))
            return True
        except Exception:
            return False

    def GetSymbols(self) -> List[Symbol]:
        """Get all symbols in the schematic."""
        return self._symbols

    def _load_symbols(self):
        """Walk the S-exp tree and create Symbol objects."""
        # Recursive walk to find (symbol ...) nodes
        self._symbols = []
        self._walk_nodes(self._sexp)

    def _walk_nodes(self, node: list):
        if not isinstance(node, list) or not node:
            return

        tag = node[0]
        if tag == SexpSymbol("symbol"):
            self._symbols.append(Symbol(node))

        # Recurse
        for child in node:
            if isinstance(child, list):
                self._walk_nodes(child)


class Symbol:
    """Represents a component symbol in the schematic."""

    def __init__(self, node: list):
        self._node = node  # Reference to the S-exp node list
        self._properties: Dict[str, Property] = {}
        self._uuid = ""
        self._parse()

    def _parse(self):
        # Extract UUID and Properties
        for item in self._node[1:]:
            if isinstance(item, list) and len(item) >= 2:
                tag = item[0]
                if tag == SexpSymbol("uuid"):
                    self._uuid = item[1]
                elif tag == SexpSymbol("property") and len(item) >= 3:
                    key = item[1]
                    self._properties[key] = Property(item)

    def GetUUID(self) -> str:
        return self._uuid

    def GetReference(self) -> str:
        prop = self.FindProperty("Reference")
        return prop.GetText() if prop else ""

    def GetValue(self) -> str:
        prop = self.FindProperty("Value")
        return prop.GetText() if prop else ""

    def SetValue(self, value: str):
        prop = self.FindProperty("Value")
        if prop:
            prop.SetText(value)
        else:
            self.AddProperty("Value", value)

    def GetFootprint(self) -> str:
        prop = self.FindProperty("Footprint")
        return prop.GetText() if prop else ""

    def SetFootprint(self, footprint: str):
        prop = self.FindProperty("Footprint")
        if prop:
            prop.SetText(footprint)
        else:
            self.AddProperty("Footprint", footprint)

    def FindProperty(self, name: str) -> Optional[Property]:
        return self._properties.get(name)

    def SetProperty(self, name: str, value: str):
        """Set a property value, creating it if it doesn't exist."""
        prop = self.FindProperty(name)
        if prop:
            prop.SetText(value)
        else:
            self.AddProperty(name, value)

    def AddProperty(self, name: str, value: str):
        """Add a new property to the underlying S-exp node."""
        # Create new property node
        # (property "Key" "Val" (id 99) (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
        new_node = [
            SexpSymbol("property"),
            name,
            value,
            [SexpSymbol("id"), 99],
            [SexpSymbol("at"), 0, 0, 0],
            [
                SexpSymbol("effects"),
                [SexpSymbol("font"), [SexpSymbol("size"), 1.27, 1.27]],
                [SexpSymbol("hide"), SexpSymbol("yes")],
            ],
        ]
        self._node.append(new_node)
        self._properties[name] = Property(new_node)


class Property:
    """Represents a property field in a symbol."""

    def __init__(self, node: list):
        self._node = node  # [Symbol("property"), "Key", "Value", ...]

    def GetName(self) -> str:
        return self._node[1]

    def GetText(self) -> str:
        return self._node[2]

    def SetText(self, value: str):
        self._node[2] = value
