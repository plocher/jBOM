"""POS generator service for creating position/placement files from KiCad PCB files."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import csv
import sys

from jbom.loaders.kicad_reader import create_kicad_reader_service
from ..models import PositionData, ComponentPosition


class POSGenerator(ABC):
    """Abstract interface for POS file generation."""

    @abstractmethod
    def generate_pos_file(
        self, pcb_file: Path, output_file: Optional[Path] = None
    ) -> None:
        """Generate a POS file from a KiCad PCB file.

        Args:
            pcb_file: Path to the .kicad_pcb file to read
            output_file: Path to write POS file to, or None for stdout

        Raises:
            FileNotFoundError: If PCB file doesn't exist
            ValueError: If PCB file cannot be parsed
        """
        pass


class DefaultPOSGenerator(POSGenerator):
    """Default implementation of POS generator using KiCadReaderService."""

    def __init__(self):
        """Initialize the POS generator with required services."""
        self.kicad_reader = create_kicad_reader_service(mode="sexp")

    def generate_pos_file(
        self, pcb_file: Path, output_file: Optional[Path] = None
    ) -> None:
        """Generate a POS file from a KiCad PCB file."""
        # Step 1: Read the PCB file using KiCadReaderService
        board_model = self.kicad_reader.read_pcb_file(pcb_file)

        # Step 2: Convert BoardModel to PositionData
        position_data = self._convert_board_to_position_data(board_model)

        # Step 3: Generate CSV output
        if output_file is None:
            # Write to stdout
            self._write_csv_to_stdout(position_data)
        else:
            # Write to file
            self._write_csv_to_file(position_data, output_file)

    def _convert_board_to_position_data(self, board_model) -> PositionData:
        """Convert BoardModel to PositionData for POS-specific processing."""
        position_data = PositionData(
            pcb_file=board_model.path,
            board_title=board_model.title,
            kicad_version=board_model.kicad_version,
        )

        for footprint in board_model.footprints:
            # Convert side designation from BoardModel format to POS format
            layer = "Top" if footprint.side == "TOP" else "Bottom"

            # Extract package from package_token or footprint name
            package = footprint.package_token
            if not package:
                # Fallback to extracting from footprint name
                if ":" in footprint.footprint_name:
                    package = footprint.footprint_name.split(":", 1)[1]
                else:
                    package = footprint.footprint_name

            # Get value from attributes
            value = footprint.attributes.get("Value", "")

            component_pos = ComponentPosition(
                reference=footprint.reference,
                value=value,
                package=package,
                footprint=footprint.footprint_name,
                x_mm=footprint.center_x_mm,
                y_mm=footprint.center_y_mm,
                rotation_deg=footprint.rotation_deg,
                layer=layer,
                attributes=footprint.attributes.copy(),
            )

            position_data.components.append(component_pos)

        return position_data

    def _write_csv_to_stdout(self, position_data: PositionData) -> None:
        """Write POS data as CSV to stdout."""
        writer = csv.writer(sys.stdout)
        self._write_csv_data(writer, position_data)

    def _write_csv_to_file(
        self, position_data: PositionData, output_file: Path
    ) -> None:
        """Write POS data as CSV to a file."""
        with open(output_file, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            self._write_csv_data(writer, position_data)

    def _write_csv_data(self, writer, position_data: PositionData) -> None:
        """Write POS data using the provided CSV writer."""
        # Write header
        writer.writerow(
            ["Designator", "Val", "Package", "Mid X", "Mid Y", "Rotation", "Layer"]
        )

        # Write component data
        for comp in position_data.components:
            writer.writerow(
                [
                    comp.reference,
                    comp.value,
                    comp.package,
                    comp.x_mm,
                    comp.y_mm,
                    comp.rotation_deg,
                    comp.layer,
                ]
            )


def create_pos_generator() -> POSGenerator:
    """Factory function to create a POS generator instance.

    Returns:
        Configured POSGenerator instance
    """
    return DefaultPOSGenerator()
