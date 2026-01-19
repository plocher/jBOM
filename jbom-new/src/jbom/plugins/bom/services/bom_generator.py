"""BOM generator service for creating bill of materials from KiCad schematic files."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union, List, Dict, Any
import csv
import sys

from jbom.cli.formatting import Column, print_tabular_data
from jbom.loaders.kicad_reader import create_kicad_reader_service
from ..models import SchematicComponent, BOMEntry, BOMData


class BOMGenerator(ABC):
    """Abstract interface for BOM generation."""

    @abstractmethod
    def generate_bom_file(
        self,
        project_files,
        output_file: Optional[Union[Path, str]] = None,
        fabricator_id: Optional[str] = None,
        fields: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Generate a BOM file from KiCad schematic files.

        Args:
            project_files: ProjectFiles object with discovered files
            output_file: Path to write BOM file to, None for CSV stdout,
                        or 'console' for human-readable output
            fabricator_id: Optional fabricator ID for specific formatting
            fields: Optional list of fields to include
            filters: Optional filtering criteria

        Raises:
            FileNotFoundError: If schematic file doesn't exist
            ValueError: If schematic file cannot be parsed
        """
        pass


class DefaultBOMGenerator(BOMGenerator):
    """Default implementation of BOM generator using KiCadReaderService."""

    def __init__(self):
        """Initialize the BOM generator with required services."""
        self.kicad_reader = create_kicad_reader_service(mode="sexp")

    def generate_bom_file(
        self,
        project_files,
        output_file: Optional[Union[Path, str]] = None,
        fabricator_id: Optional[str] = None,
        fields: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Generate a BOM file from KiCad schematic files."""
        # Check that we have schematic files
        if not project_files.schematic_files:
            raise ValueError("No schematic files found")

        # Step 1: Read all schematic files
        all_components = []
        for sch_file in project_files.schematic_files:
            # For now, use the PCB reader as a placeholder
            # TODO: Implement proper schematic reading
            components = self._read_schematic_file(sch_file)
            all_components.extend(components)

        # Step 2: Apply filtering
        filtered_components = self._apply_filters(all_components, filters or {})

        # Step 3: Aggregate components into BOM entries
        bom_data = self._aggregate_components(
            filtered_components, project_files.base_name, project_files.schematic_files
        )

        # Step 4: Build headers/fields based on fabricator/fields
        from jbom.config.fabricators import load_fabricator

        fab = None
        if fabricator_id:
            fab = load_fabricator(fabricator_id)

        default_fields = ["references", "value", "footprint", "quantity"]
        if fab and not fields:
            # Use fabricator's BOM field set if it exists
            fab_fields = getattr(fab, "bom_columns", {})
            if fab_fields:
                fab_implied = list(dict.fromkeys(fab_fields.values()))
                eff_fields = fab_implied
            else:
                eff_fields = default_fields
        elif fab and fields:
            # Merge user fields with fabricator requirements
            fab_fields = getattr(fab, "bom_columns", {})
            if fab_fields:
                fab_implied = list(dict.fromkeys(fab_fields.values()))
                eff_fields = list(fields)
                for f in fab_implied:
                    if f not in eff_fields:
                        eff_fields.append(f)
            else:
                eff_fields = fields
        else:
            eff_fields = fields or default_fields

        headers = self._get_headers_for_fields(fab, eff_fields)

        # Step 5: Generate output based on format
        if output_file is None or output_file == "-":
            # Write CSV to stdout
            self._write_csv_to_stdout(bom_data, headers, eff_fields)
        elif isinstance(output_file, str) and output_file.lower() == "console":
            # Write human-readable console output
            self._write_console_output(bom_data)
        else:
            # Write CSV to file
            self._write_csv_to_file(bom_data, output_file, headers, eff_fields)

    def _read_schematic_file(self, sch_file: Path) -> List[SchematicComponent]:
        """Read components from a schematic file.

        TODO: Implement proper schematic reading when KiCad reader supports it.
        For now, return mock data to enable testing of aggregation logic.
        """
        # Mock schematic components for testing
        if "test" in sch_file.name.lower():
            return [
                SchematicComponent(
                    reference="R1",
                    value="10K",
                    footprint="R_0805",
                    attributes={"mount_type": "SMD"},
                    sheet_path="/",
                ),
                SchematicComponent(
                    reference="R2",
                    value="10K",
                    footprint="R_0805",
                    attributes={"mount_type": "SMD"},
                    sheet_path="/",
                ),
                SchematicComponent(
                    reference="C1",
                    value="100nF",
                    footprint="C_0603",
                    attributes={"mount_type": "SMD"},
                    sheet_path="/",
                ),
                SchematicComponent(
                    reference="U1",
                    value="LM358",
                    footprint="SOIC-8",
                    attributes={"mount_type": "SMD"},
                    sheet_path="/",
                ),
            ]
        return []

    def _apply_filters(
        self, components: List[SchematicComponent], filters: Dict[str, Any]
    ) -> List[SchematicComponent]:
        """Apply filtering criteria to components."""
        filtered = []

        # Default: exclude DNP and excluded components unless overridden
        exclude_dnp = filters.get("exclude_dnp", True)
        exclude_from_bom = filters.get("exclude_from_bom", True)

        for component in components:
            # Apply DNP filter
            if exclude_dnp and component.is_dnp:
                continue

            # Apply exclude from BOM filter
            if exclude_from_bom and component.is_excluded_from_bom:
                continue

            filtered.append(component)

        return filtered

    def _aggregate_components(
        self,
        components: List[SchematicComponent],
        project_name: str,
        sch_files: List[Path],
    ) -> BOMData:
        """Aggregate components into BOM entries by value and footprint."""
        # Group components by aggregation key (value, footprint)
        groups: Dict[tuple, List[SchematicComponent]] = {}

        for component in components:
            key = component.aggregation_key
            if key not in groups:
                groups[key] = []
            groups[key].append(component)

        # Create BOM entries from groups
        entries = []
        for (value, footprint), component_list in groups.items():
            references = [comp.reference for comp in component_list]

            # Merge attributes from all components in the group
            merged_attributes = {}
            for comp in component_list:
                for attr_key, attr_value in comp.attributes.items():
                    if attr_key not in merged_attributes:
                        merged_attributes[attr_key] = attr_value

            entry = BOMEntry(
                references=references,
                value=value,
                footprint=footprint,
                quantity=len(references),
                attributes=merged_attributes,
            )
            entries.append(entry)

        # Sort entries by first reference for consistent output
        entries.sort(key=lambda e: e.references[0])

        return BOMData(
            project_name=project_name,
            schematic_files=sch_files,
            entries=entries,
        )

    def _get_headers_for_fields(self, fab, fields: List[str]) -> List[str]:
        """Get headers for the specified fields."""
        # Default BOM header mapping
        default_headers = {
            "references": "References",
            "value": "Value",
            "footprint": "Footprint",
            "quantity": "Quantity",
            "description": "Description",
            "manufacturer": "Manufacturer",
            "manufacturer_part": "Manufacturer Part",
            "supplier": "Supplier",
            "supplier_part": "Supplier Part",
            "lcsc_part": "LCSC Part",
        }

        if fab and hasattr(fab, "bom_columns"):
            # Use fabricator-specific headers with fallbacks
            headers = []
            fab_headers = fab.bom_columns
            for field in fields:
                # Check if fabricator defines this field
                fabricator_header = None
                for header, internal_field in fab_headers.items():
                    if internal_field == field:
                        fabricator_header = header
                        break

                if fabricator_header:
                    headers.append(fabricator_header)
                else:
                    # Fall back to default headers
                    headers.append(default_headers.get(field, field))
            return headers
        else:
            # Use default headers
            return [default_headers.get(field, field) for field in fields]

    def _write_csv_to_stdout(
        self, bom_data: BOMData, headers: List[str], fields: List[str]
    ) -> None:
        """Write BOM data as CSV to stdout."""
        writer = csv.writer(sys.stdout)
        self._write_csv_data(writer, bom_data, headers, fields)

    def _write_csv_to_file(
        self,
        bom_data: BOMData,
        output_file: Union[Path, str],
        headers: List[str],
        fields: List[str],
    ) -> None:
        """Write BOM data as CSV to a file."""
        output_path = Path(output_file) if isinstance(output_file, str) else output_file
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            self._write_csv_data(writer, bom_data, headers, fields)

    def _write_csv_data(
        self, writer, bom_data: BOMData, headers: List[str], fields: List[str]
    ) -> None:
        """Write BOM data using the provided CSV writer."""
        # Write header
        writer.writerow(headers)

        # Write BOM entries
        for entry in bom_data.entries:
            row = []
            for field in fields:
                if field == "references":
                    row.append(entry.references_string)
                elif field == "value":
                    row.append(entry.value)
                elif field == "footprint":
                    row.append(entry.footprint)
                elif field == "quantity":
                    row.append(str(entry.quantity))
                elif field in entry.attributes:
                    row.append(str(entry.attributes[field]))
                else:
                    row.append("")
            writer.writerow(row)

    def _write_console_output(self, bom_data: BOMData) -> None:
        """Write BOM data in human-readable format using shared table formatter."""

        def transform_entry(entry):
            """Transform BOMEntry to row mapping for display."""
            return {
                "refs": entry.references_string,
                "value": entry.value,
                "footprint": entry.footprint,
                "qty": str(entry.quantity),
                "description": entry.attributes.get("description", ""),
            }

        # Define columns for BOM display
        columns = [
            Column(
                "References",
                "refs",
                wrap=True,
                preferred_width=20,
                fixed=False,
                align="left",
            ),
            Column(
                "Value",
                "value",
                wrap=False,
                preferred_width=15,
                fixed=True,
                align="left",
            ),
            Column(
                "Footprint",
                "footprint",
                wrap=True,
                preferred_width=20,
                fixed=False,
                align="left",
            ),
            Column(
                "Qty", "qty", wrap=False, preferred_width=5, fixed=True, align="right"
            ),
            Column(
                "Description",
                "description",
                wrap=True,
                preferred_width=25,
                fixed=False,
                align="left",
            ),
        ]

        # Use general tabular data formatter
        print_tabular_data(
            data=bom_data.entries,
            columns=columns,
            row_transformer=transform_entry,
            sort_key=lambda e: e.references[0],
            title="Bill of Materials",
            summary_line=f"Total: {bom_data.total_components} components, {bom_data.total_line_items} line items",
        )


def create_bom_generator() -> BOMGenerator:
    """Factory function to create a BOM generator instance.

    Returns:
        Configured BOMGenerator instance
    """
    return DefaultBOMGenerator()
