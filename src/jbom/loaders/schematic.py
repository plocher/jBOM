"""
KiCad schematic loader for jBOM.

Loads and parses KiCad schematic files (.kicad_sch) using S-expression format
to extract component information for BOM generation.
"""

from pathlib import Path
from typing import List, Dict, Optional
import sys

from sexpdata import Symbol

from jbom.common.types import Component
from jbom.common.sexp_parser import load_kicad_file, walk_nodes
from jbom.common.options import GeneratorOptions


class SchematicLoader:
    """Loads KiCad schematic files and extracts components using S-expression parser (sexpdata)."""

    def __init__(
        self, schematic_path: Path, options: Optional[GeneratorOptions] = None
    ):
        self.schematic_path = schematic_path
        self.components: List[Component] = []
        self.options = options or GeneratorOptions()

    def parse(self) -> List[Component]:
        """Parse the KiCad schematic file and extract components"""
        return self._parse_with_sexp()

    def _parse_with_sexp(self) -> List[Component]:
        sexp = load_kicad_file(self.schematic_path)
        for symbol_node in walk_nodes(sexp, "symbol"):
            comp = self._parse_symbol(symbol_node)
            if not comp:
                continue

            # Check exclusion criteria
            is_excluded = False
            exclude_reason = ""

            if not comp.in_bom:
                is_excluded = True
                exclude_reason = "Exclude from BOM set"
            elif comp.dnp:
                is_excluded = True
                exclude_reason = "DNP set"
            elif comp.reference.startswith("#"):
                is_excluded = True
                exclude_reason = "Reference starts with #"

            # Debug logging if enabled
            if is_excluded:
                is_debug = self.options.debug
                is_sch_debug = "schematic" in self.options.debug_categories
                if is_debug or is_sch_debug:
                    print(
                        f"DEBUG[schematic]: Excluded component {comp.reference} ({comp.value}): {exclude_reason}",
                        file=sys.stderr,
                    )
            else:
                self.components.append(comp)

        return self.components

    def _parse_symbol(self, node: list) -> Optional[Component]:
        """Parse a (symbol ...) node into a Component"""
        lib_id = ""
        reference = ""
        value = ""
        footprint = ""
        uuid = ""
        in_bom = True
        exclude_from_sim = False
        dnp = False
        properties: Dict[str, str] = {}
        has_instances = False

        # Iterate fields inside symbol
        for item in node[1:]:
            if isinstance(item, list) and item:
                tag = item[0]
                if tag == Symbol("lib_id") and len(item) >= 2:
                    lib_id = item[1]
                elif tag == Symbol("uuid") and len(item) >= 2:
                    uuid = item[1]
                elif tag == Symbol("in_bom") and len(item) >= 2:
                    in_bom = item[1] == Symbol("yes")
                elif tag == Symbol("exclude_from_sim") and len(item) >= 2:
                    exclude_from_sim = item[1] == Symbol("yes")
                elif tag == Symbol("dnp") and len(item) >= 2:
                    dnp = item[1] == Symbol("yes")
                elif tag == Symbol("instances") and len(item) >= 2:
                    has_instances = True
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

        # Only return components that have instances (actual placed components, not library definitions)
        if not reference or not has_instances:
            # Debug logging for components without instances (often library definitions)
            is_debug = self.options.debug
            is_sch_debug = "schematic" in self.options.debug_categories
            if (is_debug or is_sch_debug) and reference:
                print(
                    f"DEBUG[schematic]: Ignored symbol {reference} ({value}): No instances found (likely library definition)",
                    file=sys.stderr,
                )
            return None

        return Component(
            reference=reference,
            lib_id=lib_id,
            value=value or "",
            footprint=footprint or "",
            uuid=uuid,
            properties=properties,
            in_bom=in_bom,
            exclude_from_sim=exclude_from_sim,
            dnp=dnp,
        )
