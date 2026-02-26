"""SchematicReader Service - pure business logic for loading KiCad schematics."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from jbom.common.options import GeneratorOptions
from jbom.common.types import Component
from jbom.services.readers import schematic_reader


class SchematicReader:
    """Pure service for reading KiCad schematic files.

    This service has no dependencies on CLI, workflows, or other services.
    It focuses solely on loading and parsing schematic files.
    """

    def __init__(self, options: Optional[GeneratorOptions] = None):
        """Initialize the schematic reader.

        Args:
            options: Optional configuration for filtering and debugging
        """
        self.options = options or GeneratorOptions()

    def load_components(self, schematic_file: Path) -> List[Component]:
        """Load components from a KiCad schematic file.

        Args:
            schematic_file: Path to .kicad_sch file

        Returns:
            List of Component objects found in the schematic

        Raises:
            FileNotFoundError: If schematic file doesn't exist
            ValueError: If schematic file cannot be parsed
        """
        if not schematic_file.exists():
            raise FileNotFoundError(f"Schematic file not found: {schematic_file}")

        if not schematic_file.suffix.lower() == ".kicad_sch":
            raise ValueError(f"Expected .kicad_sch file, got: {schematic_file.suffix}")

        try:
            return self._parse_schematic(schematic_file)
        except Exception as e:
            raise ValueError(f"Failed to parse schematic {schematic_file}: {e}")

    def _parse_schematic(self, schematic_file: Path) -> List[Component]:
        """Parse schematic file using S-expression parser."""
        sexp = schematic_reader.load_kicad_file(schematic_file)
        components: List[Component] = []

        for symbol_node in schematic_reader.walk_nodes(sexp, "symbol"):
            component = self._parse_symbol(symbol_node)
            if component and self._should_include_component(component):
                components.append(component)

        return components

    def _parse_symbol(self, node: list) -> Optional[Component]:
        """Parse a (symbol ...) node into a Component."""
        from sexpdata import Symbol

        lib_id = ""
        reference = ""
        value = ""
        footprint = ""
        uuid = ""
        in_bom = True
        exclude_from_sim = False
        dnp = False
        properties = {}
        has_instances = False
        has_position = False

        # Parse symbol data
        for item in node[1:]:
            if isinstance(item, list) and item:
                tag = item[0]
                if tag == Symbol("lib_id") and len(item) >= 2:
                    lib_id = item[1]
                elif tag == Symbol("at") and len(item) >= 2:
                    has_position = True
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
                        if isinstance(key, str) and isinstance(val, str):
                            properties[key] = val

        # Validate component
        if not reference:
            return None

        # Check if component is actually placed
        if not has_instances and not has_position:
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

    def _should_include_component(self, component: Component) -> bool:
        """Return True if a parsed component should be included.

        SchematicReader is intentionally permissive: it loads components and
        preserves their flags (DNP, in_bom, virtual symbols, etc.).

        Filtering policy is applied later via `jbom.common.component_filters`
        based on CLI flags (e.g. --include-dnp, --include-excluded, --include-all).
        """

        return True
