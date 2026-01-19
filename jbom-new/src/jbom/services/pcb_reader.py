"""KiCad PCB file reading service.

This service reads KiCad PCB files and provides comprehensive component
information for use by various plugins (POS, BOM, etc.).
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from jbom.common.pcb_types import BoardModel, PcbComponent


class KiCadReaderService(ABC):
    """Abstract interface for reading KiCad PCB files.

    This service reads KiCad PCB files and returns comprehensive board
    information that can be used by various plugins (POS, BOM, etc.).
    """

    @abstractmethod
    def read_pcb_file(self, pcb_path: Path) -> BoardModel:
        """Read a KiCad PCB file and return board model with all component data.

        Args:
            pcb_path: Path to the .kicad_pcb file

        Returns:
            BoardModel containing all footprints and board metadata

        Raises:
            FileNotFoundError: If PCB file doesn't exist
            KiCadParseError: If PCB file cannot be parsed
        """
        pass

    @abstractmethod
    def validate_pcb_file(self, pcb_path: Path) -> bool:
        """Validate that a PCB file can be read.

        Args:
            pcb_path: Path to check

        Returns:
            True if file exists and appears to be a valid KiCad PCB file
        """
        pass


class KiCadParseError(Exception):
    """Raised when a KiCad PCB file cannot be parsed."""

    def __init__(self, message: str, pcb_path: Optional[Path] = None):
        self.pcb_path = pcb_path
        super().__init__(message)


class DefaultKiCadReaderService(KiCadReaderService):
    """Default implementation providing comprehensive KiCad PCB file reading.

    This implementation reads all component information from KiCad PCB files
    using S-expression parsing, making it suitable for various plugins.
    """

    def __init__(self, mode: str = "auto"):
        """Initialize the reader service.

        Args:
            mode: Loading mode ("auto", "pcbnew", "sexp")
                - auto: Try pcbnew first, fall back to S-expression parser
                - pcbnew: Use KiCad pcbnew Python module (requires KiCad installation)
                - sexp: Use pure Python S-expression parser
        """
        self.mode = mode

    def read_pcb_file(self, pcb_path: Path) -> BoardModel:
        """Read a KiCad PCB file and return comprehensive board model."""
        if not self.validate_pcb_file(pcb_path):
            raise KiCadParseError(f"Invalid or missing PCB file: {pcb_path}", pcb_path)

        try:
            from jbom.common.sexp_parser import load_kicad_file, walk_nodes

            # Load and parse the S-expression file
            sexp = load_kicad_file(pcb_path)
            board = BoardModel(path=pcb_path)

            # Extract board-level information
            self._extract_board_metadata(sexp, board)

            # Process all footprints
            for footprint_node in walk_nodes(sexp, "footprint"):
                component = self._parse_footprint_node(footprint_node)
                if component:
                    board.footprints.append(component)

            return board

        except Exception as e:
            raise KiCadParseError(f"Failed to parse PCB file: {e}", pcb_path)

    def validate_pcb_file(self, pcb_path: Path) -> bool:
        """Validate PCB file exists and has correct extension."""
        if not pcb_path.exists():
            return False

        if not pcb_path.is_file():
            return False

        if not pcb_path.suffix.lower() == ".kicad_pcb":
            return False

        # Basic content validation - check if it looks like a KiCad PCB file
        try:
            with open(pcb_path, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                return first_line.startswith("(kicad_pcb")
        except (OSError, UnicodeDecodeError):
            return False

    def _extract_board_metadata(self, sexp, board: BoardModel) -> None:
        """Extract board-level metadata from S-expression."""
        from sexpdata import Symbol

        if not isinstance(sexp, list) or len(sexp) < 2:
            return

        # Look for general section with title
        for item in sexp[1:]:
            if isinstance(item, list) and item and item[0] == Symbol("general"):
                for general_item in item[1:]:
                    if (
                        isinstance(general_item, list)
                        and len(general_item) >= 2
                        and general_item[0] == Symbol("title")
                        and isinstance(general_item[1], str)
                    ):
                        board.title = general_item[1]
                        break
            elif (
                isinstance(item, list)
                and len(item) >= 2
                and item[0] == Symbol("version")
                and isinstance(item[1], str)
            ):
                board.kicad_version = item[1]

    def _parse_footprint_node(self, node) -> Optional[PcbComponent]:
        """Parse a footprint node and extract all component information."""
        from sexpdata import Symbol

        # node: (footprint "Lib:Name" (layer "F.Cu") (at x y [rot]) ...)
        fp_name = None
        if len(node) >= 2 and isinstance(node[1], str):
            fp_name = node[1]

        ref = None
        value = ""
        x_mm = y_mm = 0.0
        rot = 0.0
        side = "TOP"
        attributes = {}

        for child in node[2:]:
            if not (isinstance(child, list) and child):
                continue

            head = child[0]
            if (
                head == Symbol("layer")
                and len(child) >= 2
                and isinstance(child[1], str)
            ):
                layer_name = child[1]
                side = "TOP" if layer_name.startswith("F.") else "BOTTOM"

            elif head == Symbol("at") and len(child) >= 3:
                # (at x y [rot])
                try:
                    x_mm = float(child[1])
                    y_mm = float(child[2])
                    if len(child) >= 4:
                        rot = float(child[3])
                except (ValueError, TypeError):
                    pass  # Keep defaults

            elif head == Symbol("fp_text") and len(child) >= 3:
                # (fp_text reference "R1" ...) or (fp_text value "1K" ...)
                if len(child) >= 3 and isinstance(child[2], str):
                    if child[1] == Symbol("reference"):
                        ref = child[2]
                    elif child[1] == Symbol("value"):
                        value = child[2]

            elif head == Symbol("property") and len(child) >= 3:
                # (property "Reference" "R1" ...) or (property "Value" "1K" ...)
                try:
                    key = child[1]
                    val = child[2]
                    if isinstance(key, str) and isinstance(val, str):
                        if key == "Reference":
                            ref = val
                        elif key == "Value":
                            value = val
                        elif key == "Footprint":
                            fp_name = val
                        else:
                            # Store all other properties
                            attributes[key] = val
                except (IndexError, TypeError):
                    pass

            elif head == Symbol("attr"):
                # (attr smd) or (attr through_hole)
                if len(child) >= 2:
                    attr_type = str(child[1])
                    attributes["mount_type"] = attr_type

        if not ref:
            return None

        # Extract package token from footprint name
        package_token = self._extract_package_token(fp_name or "")

        # Ensure value is in attributes for easy access by plugins
        if value:
            attributes["Value"] = value

        return PcbComponent(
            reference=ref,
            footprint_name=fp_name or "",
            package_token=package_token,
            center_x_mm=x_mm,
            center_y_mm=y_mm,
            rotation_deg=rot,
            side=side,
            attributes=attributes,
        )

    def _extract_package_token(self, footprint_name: str) -> str:
        """Extract package token from footprint name for compatibility."""
        if not footprint_name:
            return ""

        # Handle library:footprint format
        if ":" in footprint_name:
            footprint_part = footprint_name.split(":", 1)[1]
        else:
            footprint_part = footprint_name

        # Common package patterns (simplified for now)
        footprint_lower = footprint_part.lower()

        # Basic pattern matching
        patterns = [
            "0201",
            "0402",
            "0603",
            "0805",
            "1206",
            "1210",
            "1812",
            "2010",
            "2512",
            "soic",
            "tsop",
            "qfn",
            "qfp",
            "bga",
            "lga",
            "dfn",
            "son",
        ]

        for pattern in patterns:
            if pattern in footprint_lower:
                return pattern.upper()

        return footprint_part


# Factory function for creating the service
def create_kicad_reader_service(mode: str = "auto") -> KiCadReaderService:
    """Create a KiCad reader service instance.

    Args:
        mode: Loading mode for the service

    Returns:
        Configured KiCadReaderService instance
    """
    return DefaultKiCadReaderService(mode=mode)
