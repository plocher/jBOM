"""
KiCad schematic loader for jBOM.

Loads and parses KiCad schematic files (.kicad_sch) using S-expression format
to extract component information for BOM generation.
"""

from pathlib import Path
from typing import List, Dict, Optional

from sexpdata import Symbol

from jbom.common.types import Component
from jbom.common.sexp_parser import load_kicad_file, walk_nodes


class SchematicLoader:
    """Loads KiCad schematic files and extracts component data using S-expression parser (sexpdata)."""

    def __init__(self, schematic_path: Path):
        self.schematic_path = schematic_path
        self.components: List[Component] = []

    def parse(self) -> List[Component]:
        """Parse the KiCad schematic file and extract components"""
        return self._parse_with_sexp()

    def _parse_with_sexp(self) -> List[Component]:
        sexp = load_kicad_file(self.schematic_path)
        for symbol_node in walk_nodes(sexp, "symbol"):
            comp = self._parse_symbol(symbol_node)
            if (
                comp
                and comp.in_bom
                and not comp.dnp
                and not comp.reference.startswith("#")
            ):
                self.components.append(comp)
        return self.components

    def _parse_symbol(self, node: list) -> Optional[Component]:
        """Parse a (symbol ...) node into a Component"""
        lib_id = ""
        reference = ""
        value = ""
        footprint = ""
        in_bom = True
        exclude_from_sim = False
        dnp = False
        properties: Dict[str, str] = {}

        # Iterate fields inside symbol
        for item in node[1:]:
            if isinstance(item, list) and item:
                tag = item[0]
                if tag == Symbol("lib_id") and len(item) >= 2:
                    lib_id = item[1]
                elif tag == Symbol("in_bom") and len(item) >= 2:
                    in_bom = item[1] == Symbol("yes")
                elif tag == Symbol("exclude_from_sim") and len(item) >= 2:
                    exclude_from_sim = item[1] == Symbol("yes")
                elif tag == Symbol("dnp") and len(item) >= 2:
                    dnp = item[1] == Symbol("yes")
                elif tag == Symbol("property") and len(item) >= 3:
                    key = item[1]
                    val = item[2]
                    if key == "Reference":
                        reference = val
                    elif key == "Value":
                        value = val
                    elif key == "Footprint":
                        footprint = val
                    else:
                        # capture interesting attributes
                        if isinstance(key, str) and isinstance(val, str):
                            properties[key] = val

        if not reference:
            return None
        return Component(
            reference=reference,
            lib_id=lib_id,
            value=value or "",
            footprint=footprint or "",
            properties=properties,
            in_bom=in_bom,
            exclude_from_sim=exclude_from_sim,
            dnp=dnp,
        )
