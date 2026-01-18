"""POS generator service for creating position/placement files from KiCad PCB files."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union, List, Dict, Any

from jbom.cli.formatting import Column, print_tabular_data
import csv
import sys

from jbom.loaders.kicad_reader import create_kicad_reader_service
from ..models import PositionData, ComponentPosition


class POSGenerator(ABC):
    """Abstract interface for POS file generation."""

    @abstractmethod
    def generate_pos_file(
        self, pcb_file: Path, output_file: Optional[Union[Path, str]] = None
    ) -> None:
        """Generate a POS file from a KiCad PCB file.

        Args:
            pcb_file: Path to the .kicad_pcb file to read
            output_file: Path to write POS file to, None for CSV stdout,
                        or 'Console' for human-readable output

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
        self,
        pcb_file: Path,
        output_file: Optional[Union[Path, str]] = None,
        layer: Optional[str] = None,
        fabricator_id: Optional[str] = None,
        fields: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Generate a POS file from a KiCad PCB file."""
        # Step 1: Read the PCB file using KiCadReaderService
        board_model = self.kicad_reader.read_pcb_file(pcb_file)

        # Step 2: Convert BoardModel to PositionData
        all_filters = filters or {}
        if layer:
            all_filters["layer"] = layer
        position_data = self._convert_board_to_position_data(
            board_model, filters=all_filters
        )

        # Build headers/fields based on fabricator/fields
        from jbom.config.fabricators import load_fabricator, headers_for_fields

        fab = None
        if fabricator_id:
            fab = load_fabricator(fabricator_id)
        default_fields = ["reference", "value", "package", "x", "y", "rotation", "side"]
        if fab and not fields:
            fab_implied = list(dict.fromkeys(fab.pos_columns.values()))
            eff_fields = fab_implied
        elif fab and fields:
            fab_implied = list(dict.fromkeys(fab.pos_columns.values()))
            eff_fields = list(fields)
            for f in fab_implied:
                if f not in eff_fields:
                    eff_fields.append(f)
        else:
            eff_fields = fields or default_fields
        headers = headers_for_fields(fab, eff_fields)

        # Step 3: Generate output based on format
        if output_file is None or output_file == "-":
            # Write CSV to stdout
            self._write_csv_to_stdout(position_data, headers, eff_fields)
        elif isinstance(output_file, str) and output_file.lower() == "console":
            # Write human-readable console output
            self._write_console_output(position_data)
        else:
            # Write CSV to file
            self._write_csv_to_file(position_data, output_file, headers, eff_fields)

    def _convert_board_to_position_data(
        self, board_model, filters: Optional[Dict[str, Any]] = None
    ) -> PositionData:
        """Convert BoardModel to PositionData for POS-specific processing."""
        position_data = PositionData(
            pcb_file=board_model.path,
            board_title=board_model.title,
            kicad_version=board_model.kicad_version,
        )

        for footprint in board_model.footprints:
            # Apply all filters
            if filters and not self._passes_filters(footprint, filters):
                continue
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

    def _passes_filters(self, footprint, filters: Dict[str, Any]) -> bool:
        """Check if a footprint passes all active filters."""
        # Layer filter
        if "layer" in filters:
            layer_filter = filters["layer"]
            if footprint.side != layer_filter:
                return False

        # SMD only filter
        if filters.get("smd_only", False):
            mount_type = footprint.attributes.get("mount_type", "SMD")
            if mount_type.upper() != "SMD":
                return False

        # Exclude DNP (Do Not Populate) components
        if filters.get("exclude_dnp", False):
            # Check various DNP indicators
            dnp_attrs = [
                footprint.attributes.get("dnp", "").lower(),
                footprint.attributes.get("do_not_populate", "").lower(),
                footprint.attributes.get("Value", "").lower(),
            ]
            if any(
                attr in ["true", "1", "yes", "dnp", "do not populate"]
                for attr in dnp_attrs
            ):
                return False

        # Exclude from POS filter
        if filters.get("exclude_from_pos", False):
            exclude_pos = footprint.attributes.get("exclude_from_pos", "").lower()
            if exclude_pos in ["true", "1", "yes"]:
                return False

        return True

    def _write_console_output(self, position_data: PositionData) -> None:
        """Write POS data in human-readable format using shared table formatter."""

        def transform_component(comp):
            """Transform ComponentPosition to row mapping for display."""
            # Determine SMD display
            smd_type = comp.attributes.get("mount_type", "smd").upper()
            if smd_type == "SMD":
                smd_display = "SMD"
            elif smd_type == "THROUGH_HOLE":
                smd_display = "THT"
            else:
                smd_display = "SMD"

            side = "TOP" if comp.layer.upper() == "TOP" else "BOT"
            return {
                "ref": comp.reference,
                "x": f"{comp.x_mm:.4f}",
                "y": f"{comp.y_mm:.4f}",
                "rot": f"{comp.rotation_deg:.1f}",
                "side": side,
                "footprint": comp.footprint,
                "smd": smd_display,
            }

        # Define columns with wrapping and alignment similar to legacy output
        columns = [
            Column(
                "Reference",
                "ref",
                wrap=True,
                preferred_width=16,
                fixed=False,
                align="left",
            ),
            Column("X", "x", wrap=False, preferred_width=8, fixed=True, align="right"),
            Column("Y", "y", wrap=False, preferred_width=7, fixed=True, align="right"),
            Column(
                "Rotation",
                "rot",
                wrap=False,
                preferred_width=8,
                fixed=True,
                align="right",
            ),
            Column(
                "Side", "side", wrap=False, preferred_width=4, fixed=True, align="left"
            ),
            Column(
                "Footprint",
                "footprint",
                wrap=True,
                preferred_width=25,
                fixed=False,
                align="left",
            ),
            Column(
                "SMD", "smd", wrap=False, preferred_width=3, fixed=True, align="left"
            ),
        ]

        # Use general tabular data formatter
        print_tabular_data(
            data=position_data.components,
            columns=columns,
            row_transformer=transform_component,
            sort_key=lambda c: c.reference,
            title="Placement Table:",
            summary_line=f"Total: {len(position_data.components)} components",
        )

    def _write_csv_to_stdout(
        self, position_data: PositionData, headers: List[str], fields: List[str]
    ) -> None:
        """Write POS data as CSV to stdout."""
        writer = csv.writer(sys.stdout)
        self._write_csv_data(writer, position_data, headers, fields)

    def _write_csv_to_file(
        self,
        position_data: PositionData,
        output_file: Path,
        headers: List[str],
        fields: List[str],
    ) -> None:
        """Write POS data as CSV to a file."""
        with open(output_file, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            self._write_csv_data(writer, position_data, headers, fields)

    def _write_csv_data(
        self, writer, position_data: PositionData, headers: List[str], fields: List[str]
    ) -> None:
        """Write POS data using the provided CSV writer with given headers/fields."""
        # Write header
        writer.writerow(headers)

        # Write component data
        for comp in position_data.components:
            row: List[Union[str, float]] = []
            x_str = f"{comp.x_mm:.4f}"
            y_str = f"{comp.y_mm:.4f}"
            rot_str = f"{comp.rotation_deg:.1f}"
            side_str = comp.layer.upper()
            for fld in fields:
                if fld == "reference":
                    row.append(comp.reference)
                elif fld == "value":
                    row.append(comp.value)
                elif fld == "package":
                    row.append(comp.package)
                elif fld == "footprint":
                    row.append(comp.footprint)
                elif fld == "x":
                    row.append(x_str)
                elif fld == "y":
                    row.append(y_str)
                elif fld == "rotation":
                    row.append(rot_str)
                elif fld == "side":
                    row.append(side_str)
                elif fld == "smd":
                    mt = comp.attributes.get("mount_type", "SMD").upper()
                    row.append("SMD" if mt == "SMD" else "THT")
                else:
                    row.append("")
            writer.writerow(row)


def create_pos_generator() -> POSGenerator:
    """Factory function to create a POS generator instance.

    Returns:
        Configured POSGenerator instance
    """
    return DefaultPOSGenerator()
