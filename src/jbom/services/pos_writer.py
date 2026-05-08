"""POS writer service — friend serializer for file-layer placement CSV output.

POSWriter accepts a self-contained POSGenerationPayload and writes placement data
to a target CSV file with standard jBOM format (QUOTE_ALL), respecting the
force-overwrite policy.
"""
from __future__ import annotations

import csv
from pathlib import Path

from jbom.application.pos_workflow import POSGenerationPayload
from jbom.services.pos_field_resolver import resolve_pos_field_value


class POSWriter:
    """Friend serializer for POS/CPL CSV file output."""

    @staticmethod
    def write(
        payload: POSGenerationPayload,
        output_path: Path,
        *,
        force: bool = False,
    ) -> None:
        """Write POS data from payload to a CSV file.

        Args:
            payload: POSGenerationPayload containing POS data and field metadata
            output_path: Target file path for CSV output
            force: If False, raise FileExistsError when file exists; if True, overwrite

        Raises:
            FileExistsError: When output_path exists and force=False
            ValueError: When POS data is invalid
            IOError: When file write fails
        """
        output_path = Path(output_path)

        # Enforce overwrite guard
        if output_path.exists() and not force:
            raise FileExistsError(str(output_path))

        # Write CSV with QUOTE_ALL (preserves leading zeros, quotes all fields)
        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            writer.writerow(payload.headers)

            for entry in payload.pos_data:
                row = [
                    resolve_pos_field_value(
                        entry,
                        field,
                        fabricator_id=payload.fabricator,
                        fabricator_config=payload.fabricator_config,
                    )
                    for field in payload.selected_fields
                ]
                writer.writerow(row)


__all__ = ["POSWriter"]
