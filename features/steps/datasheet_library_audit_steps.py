"""Step definitions for `jbom audit` datasheet document-library checks (jBOM#357).

Fixture PDFs are minimal ``%PDF-`` byte stubs; the audit checks under test
only care about filename presence/absence under ``<library>/datasheets/``,
never file contents.
"""

from __future__ import annotations

from pathlib import Path

from behave import given

_PDF_FIXTURE_BYTES = b"%PDF-1.4\n%fixture datasheet for jBOM#357 BDD scenarios\n%%EOF"


@given('a datasheet library directory "{rel_path}" containing:')
def given_datasheet_library_directory(context, rel_path: str) -> None:
    """Create ``<sandbox>/<rel_path>/datasheets/<Filename>`` fixture PDFs.

    The table's ``Filename`` column may be empty (zero data rows) to create
    an empty library (still exercising DATASHEET_FILE_MISSING checks).
    """

    datasheets_dir = Path(context.project_root) / rel_path / "datasheets"
    datasheets_dir.mkdir(parents=True, exist_ok=True)

    if context.table:
        for row in context.table:
            filename = row["Filename"].strip()
            if not filename:
                continue
            (datasheets_dir / filename).write_bytes(_PDF_FIXTURE_BYTES)
