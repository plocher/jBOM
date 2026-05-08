"""BOM writer service — friend serializer for file-layer BOM CSV output.

BOMWriter accepts a self-contained BOMGenerationPayload and writes BOM data
to a target CSV file with standard jBOM format (QUOTE_ALL), respecting the
force-overwrite policy.
"""
from __future__ import annotations

import csv
from pathlib import Path

from jbom.application.bom_workflow import BOMGenerationPayload
from jbom.services.bom_field_resolver import resolve_bom_field_value
from jbom.services.fabricator_projection_service import FabricatorProjectionService


class BOMWriter:
    """Friend serializer for BOM CSV file output."""

    @staticmethod
    def write(
        payload: BOMGenerationPayload,
        output_path: Path,
        *,
        force: bool = False,
    ) -> None:
        """Write BOM data from payload to a CSV file.

        Args:
            payload: BOMGenerationPayload containing BOM data and field metadata
            output_path: Target file path for CSV output
            force: If False, raise FileExistsError when file exists; if True, overwrite

        Raises:
            FileExistsError: When output_path exists and force=False
            ValueError: When BOM data is invalid
            IOError: When file write fails
        """
        output_path = Path(output_path)

        # Enforce overwrite guard
        if output_path.exists() and not force:
            raise FileExistsError(str(output_path))

        # Build projection with headers from service
        projection_service = FabricatorProjectionService()
        projection = projection_service.build_projection(
            fabricator_id=payload.fabricator,
            output_type="bom",
            selected_fields=list(payload.selected_fields),
        )
        headers = list(projection.headers)

        # Write CSV with QUOTE_ALL (preserves leading zeros, quotes all fields)
        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            writer.writerow(headers)

            for entry in payload.bom_data.entries:
                row = [
                    resolve_bom_field_value(
                        entry,
                        field,
                        fabricator_id=payload.fabricator,
                        fabricator_config=payload.fabricator_config,
                    )
                    for field in payload.selected_fields
                ]
                writer.writerow(row)


__all__ = ["BOMWriter"]
