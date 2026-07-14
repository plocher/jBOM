"""Step definitions for the datasheet library admission gate (jBOM#356).

Reuses the hermetic staging-directory setup from
``datasheet_staging_steps.py`` (``Given a staging directory`` -- sandboxed
``datasheet_staging.staging_dir`` binding written to this scenario's own
``.jbom/common.jbom.yaml``; never a real developer/CI ``$HOME``). These
steps place already-verified PDFs directly into the staging directory
(admit consumes staged content -- it does not fetch), and inspect the
library's ``datasheets/`` directory, which the CLI defaults to a sibling
of the staging directory.
"""

from __future__ import annotations

import csv
from pathlib import Path

from behave import given, then, when

_PDF_HEADER = b"%PDF-1.4\n"
_PDF_FOOTER = b"\n%%EOF"


def _pdf_bytes_for(url: str) -> bytes:
    """Deterministic verified-PDF content derived from *url*.

    Same URL always yields the same bytes, so re-staging (dupe-of) and
    distinct URLs (never byte-identical) both behave predictably in tests.
    """

    return _PDF_HEADER + f"%fixture datasheet for {url}".encode("utf-8") + _PDF_FOOTER


def _staging_dir(context) -> Path:
    staging_dir = getattr(context, "staging_dir", None)
    assert staging_dir is not None, "Use 'Given a staging directory' first"
    return staging_dir


def _library_dir(context) -> Path:
    return _staging_dir(context).parent / "datasheets"


@given('the staging directory already has a verified PDF staged for "{url}"')
def given_staged_verified_pdf_for_url(context, url: str) -> None:
    """Place a verified PDF directly into staging (admit does not fetch)."""

    from jbom.services.datasheet_staging import staged_filename_for_url

    staging_dir = _staging_dir(context)
    staging_dir.mkdir(parents=True, exist_ok=True)
    stem = staged_filename_for_url(url)
    (staging_dir / f"{stem}.pdf").write_bytes(_pdf_bytes_for(url))


@given('the library already contains "{name}" published with different content')
def given_library_contains_published_with_different_content(context, name: str) -> None:
    """Pre-populate the library with a published document under *name*."""

    library_dir = _library_dir(context)
    library_dir.mkdir(parents=True, exist_ok=True)
    (library_dir / f"{name}.pdf").write_bytes(
        _PDF_HEADER + b"%an already-published, unrelated document" + _PDF_FOOTER
    )


@then('the library contains a published document named "{name}"')
def then_library_contains_published_document(context, name: str) -> None:
    published = _library_dir(context) / f"{name}.pdf"
    assert published.is_file(), (
        f"Expected published document at {published}; "
        f"library contents: {list(_library_dir(context).glob('*')) if _library_dir(context).is_dir() else []}"
    )


@then("the library contains exactly {count:d} published document")
@then("the library contains exactly {count:d} published documents")
def then_library_contains_exactly_n_documents(context, count: int) -> None:
    library_dir = _library_dir(context)
    published = list(library_dir.glob("*.pdf")) if library_dir.is_dir() else []
    assert (
        len(published) == count
    ), f"Expected exactly {count} published document(s), found {len(published)}: {published}"


@then('the published document "{name}" still has its original content')
def then_published_document_unchanged(context, name: str) -> None:
    published = _library_dir(context) / f"{name}.pdf"
    assert published.is_file(), f"Expected {published} to still exist"
    assert published.read_bytes() == (
        _PDF_HEADER + b"%an already-published, unrelated document" + _PDF_FOOTER
    ), "Published document content changed -- never-rename guard failed to protect it"


@then('the file "{filename}" contains exactly {count:d} admit candidate row')
@then('the file "{filename}" contains exactly {count:d} admit candidate rows')
def then_manifest_contains_exactly_n_rows(context, filename: str, count: int) -> None:
    path = context.project_root / filename
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert (
        len(rows) == count
    ), f"Expected exactly {count} manifest row(s), got {len(rows)}: {rows}"


def _edit_manifest_column_for_url(
    context, filename: str, column: str, value: str, url: str
) -> None:
    """Shared implementation: rewrite one manifest cell for the row matching *url*."""

    path = context.project_root / filename
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    matched = False
    for row in rows:
        if row.get("SourceURL", "") == url:
            row[column] = value
            matched = True
    assert matched, f"No manifest row found with SourceURL={url!r} in {filename}"

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


@when(
    'I edit the manifest "{filename}" to set Action "{action}" for staged file '
    'matching "{url}"'
)
def when_edit_manifest_action_for_url(
    context, filename: str, action: str, url: str
) -> None:
    """Simulate a human editing the manifest before --apply.

    Finds the row whose ``SourceURL`` matches *url* and rewrites its
    ``Action`` cell -- e.g. accepting a candidate that propose flagged as a
    collision, to exercise the never-rename guard at apply time.
    """

    _edit_manifest_column_for_url(context, filename, "Action", action, url)


@when(
    'I edit the manifest "{filename}" to set ProposedName "{name}" for staged file '
    'matching "{url}"'
)
def when_edit_manifest_proposed_name_for_url(
    context, filename: str, name: str, url: str
) -> None:
    """Simulate a human typing an unsafe ProposedName into the manifest.

    Exercises the apply-time path-traversal guard: a crafted name like
    ``"../../evil"`` must be refused, never trusted as a bare filename
    stem.
    """

    _edit_manifest_column_for_url(context, filename, "ProposedName", name, url)


@then('nothing named "{filename}" exists outside the library directory')
def then_nothing_named_exists_outside_library(context, filename: str) -> None:
    """Assert a crafted ProposedName never wrote a file outside datasheets/.

    Checks both inside the sandbox tree (the whole scenario workspace) and
    several levels above the sandbox root -- a ``"../../evil"`` style
    traversal from the library directory (a fixed two levels under the
    sandbox root: ``<sandbox>/staging/../datasheets``) would land outside
    the sandbox tree entirely, so scanning only inside the sandbox would
    not catch a real escape. This is the belt-and-braces proof that a
    path-traversal ProposedName was refused, not merely refused-with-a-
    caveat.
    """

    sandbox_root = Path(context.sandbox_root)
    library_dir = _library_dir(context)

    for path in sandbox_root.rglob(filename):
        assert library_dir in path.parents or path.parent == library_dir, (
            f"Found {path} outside the library directory ({library_dir}) -- "
            "a path-traversal ProposedName was not refused."
        )

    # Also scan a few levels above the sandbox root -- where a "../../evil"
    # style traversal rooted at <sandbox>/datasheets would actually resolve
    # to (outside the sandbox tree, and outside anywhere rglob above would
    # ever look).
    probe_dir = sandbox_root
    for _ in range(5):
        probe_dir = probe_dir.parent
        candidate = probe_dir / filename
        assert not candidate.exists(), (
            f"Found {candidate} outside the sandbox and library directory -- "
            "a path-traversal ProposedName was not refused."
        )

    # Also confirm it did not land inside the library either (this filename
    # was never a legitimate ProposedName in these scenarios).
    assert not (library_dir / filename).exists()
