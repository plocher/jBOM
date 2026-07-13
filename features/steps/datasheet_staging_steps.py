"""Step definitions for the always-on datasheet staging fetch (jBOM#355).

Network access is never exercised in these scenarios: the CLI runs as a
subprocess (see ``features/steps/common_steps.py``), and
``JBOM_DATASHEET_FETCH_FIXTURES`` redirects ``default_fetch`` to read
response bytes from local fixture files written by these steps instead of
making real HTTP requests (see ``jbom.services.datasheet_staging``).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from behave import given, then

_PDF_FIXTURE_BYTES = b"%PDF-1.4\n%fixture datasheet for jBOM#355 BDD scenarios\n%%EOF"
_HTML_FIXTURE_BYTES = (
    b"<!DOCTYPE html><html><head><title>404</title></head>"
    b"<body>Not Found</body></html>"
)


def _staging_dir(context) -> Path:
    staging_dir = getattr(context, "staging_dir", None)
    assert staging_dir is not None, "Use 'Given a staging directory' first"
    return staging_dir


def _fixture_manifest_path(context) -> Path:
    """Return this scenario's fixture manifest path, creating it if needed.

    Deliberately keyed off ``context.sandbox_root`` (recreated per scenario
    by ``features/environment.py``) rather than cached on ``context`` --
    ``context`` itself is reused across scenarios within a feature run, so a
    cached path would go stale once the previous scenario's sandbox is torn
    down.
    """

    manifest_path = Path(context.sandbox_root) / "_datasheet_fixtures.json"
    if not manifest_path.is_file():
        manifest_path.write_text("{}", encoding="utf-8")
        os.environ["JBOM_DATASHEET_FETCH_FIXTURES"] = str(manifest_path)
        context.add_cleanup(os.environ.pop, "JBOM_DATASHEET_FETCH_FIXTURES", None)
    return manifest_path


def _register_fixture(context, url: str, content: bytes) -> None:
    manifest_path = _fixture_manifest_path(context)
    fixtures_dir = Path(context.sandbox_root) / "_datasheet_fixture_files"
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    fixture_file = fixtures_dir / f"fixture-{len(list(fixtures_dir.glob('*')))}.bin"
    fixture_file.write_bytes(content)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[url] = str(fixture_file)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


@given("a staging directory")
def given_a_staging_directory(context) -> None:
    """Create an isolated staging directory and point JBOM_STAGING_DIR at it."""

    staging_dir = Path(context.sandbox_root) / "staging"
    context.staging_dir = staging_dir
    os.environ["JBOM_STAGING_DIR"] = str(staging_dir)
    context.add_cleanup(os.environ.pop, "JBOM_STAGING_DIR", None)


@given('the datasheet URL "{url}" resolves to a PDF')
def given_datasheet_url_resolves_to_pdf(context, url: str) -> None:
    """Register a fixture so fetching *url* returns verified PDF bytes."""

    _register_fixture(context, url, _PDF_FIXTURE_BYTES)


@given('the datasheet URL "{url}" resolves to HTML')
def given_datasheet_url_resolves_to_html(context, url: str) -> None:
    """Register a fixture so fetching *url* returns HTML-impostor bytes."""

    _register_fixture(context, url, _HTML_FIXTURE_BYTES)


@then('the staging directory contains a verified PDF for "{url}"')
def then_staging_dir_contains_verified_pdf(context, url: str) -> None:
    from jbom.services.datasheet_staging import staged_filename_for_url

    stem = staged_filename_for_url(url)
    staged_path = _staging_dir(context) / f"{stem}.pdf"
    assert staged_path.is_file(), (
        f"Expected verified PDF at {staged_path}; "
        f"staging dir contents: {list(_staging_dir(context).glob('*'))}"
    )
    assert staged_path.read_bytes().startswith(b"%PDF-")


@then('the staging directory contains a flagged unverified file for "{url}"')
def then_staging_dir_contains_flagged_unverified(context, url: str) -> None:
    from jbom.services.datasheet_staging import staged_filename_for_url

    stem = staged_filename_for_url(url)
    staged_path = _staging_dir(context) / f"{stem}.unverified"
    assert staged_path.is_file(), (
        f"Expected flagged .unverified file at {staged_path}; "
        f"staging dir contents: {list(_staging_dir(context).glob('*'))}"
    )
    assert not staged_path.read_bytes().startswith(b"%PDF-")


@then('the staging directory does not contain a file for "{url}"')
def then_staging_dir_does_not_contain_file(context, url: str) -> None:
    from jbom.services.datasheet_staging import staged_filename_for_url

    stem = staged_filename_for_url(url)
    staging_dir = _staging_dir(context)
    verified_path = staging_dir / f"{stem}.pdf"
    unverified_path = staging_dir / f"{stem}.unverified"
    assert not verified_path.exists() and not unverified_path.exists(), (
        f"Expected no staged file for {url!r}, found: "
        f"{[p for p in (verified_path, unverified_path) if p.exists()]}"
    )
