"""BOM generation workflow.

Composes schematic reading and BOM generation services to produce BOM output.
Registered under name "bom.generate".
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union, Dict, Any

from jbom.workflows import registry
from jbom.plugins.bom.services.bom_generator import create_bom_generator


def _generate_bom(
    project_files,
    output: Optional[Union[Path, str]] = None,
    fabricator_id: Optional[str] = None,
    fields: Optional[list[str]] = None,
    filters: Optional[Dict[str, Any]] = None,
) -> None:
    """Generate a BOM from KiCad schematic files.

    Args:
        project_files: ProjectFiles object with discovered schematic files
        output: Output target (file path, '-' for stdout, 'console' for table)
        fabricator_id: Optional fabricator ID for specific formatting
        fields: Optional list of fields to include in output
        filters: Optional filtering criteria
    """
    gen = create_bom_generator()
    gen.generate_bom_file(
        project_files=project_files,
        output_file=output,
        fabricator_id=fabricator_id,
        fields=fields,
        filters=filters,
    )


# Register workflow at import time
registry.register("bom.generate", _generate_bom)
