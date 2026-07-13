"""Step definitions for the always-on datasheet staging fetch (jBOM#355).

Configuration (staging directory, fetch budget, and the test-only fixture
manifest) is written to this scenario's sandboxed ``.jbom/common.jbom.yaml``
profile -- the same ``defaults:`` stanza mechanism every other jBOM setting
uses (see ``docs/reference/configuration.md``) -- rather than environment
variables. ``common.jbom.yaml`` is used (instead of ``generic.jbom.yaml``)
because the supplier-profile steps in ``project_centric_steps.py`` overwrite
``.jbom/generic.jbom.yaml`` wholesale; ``common.jbom.yaml`` merges
cumulatively underneath every named profile, so the two step families never
collide.

Network access is never exercised in these scenarios: the CLI runs as a
subprocess (see ``features/steps/common_steps.py``), and the
``fetch_fixtures_manifest`` profile key redirects ``default_fetch`` to read
response bytes from local fixture files written by these steps instead of
making real HTTP requests (see ``jbom.services.datasheet_staging``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from behave import given, then

_PDF_FIXTURE_BYTES = b"%PDF-1.4\n%fixture datasheet for jBOM#355 BDD scenarios\n%%EOF"
_HTML_FIXTURE_BYTES = (
    b"<!DOCTYPE html><html><head><title>404</title></head>"
    b"<body>Not Found</body></html>"
)


def _common_profile_path(context) -> Path:
    jbom_dir = Path(context.sandbox_root) / ".jbom"
    jbom_dir.mkdir(parents=True, exist_ok=True)
    return jbom_dir / "common.jbom.yaml"


def _read_common_profile(context) -> dict[str, Any]:
    path = _common_profile_path(context)
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_common_profile(context, data: dict[str, Any]) -> None:
    _common_profile_path(context).write_text(
        yaml.safe_dump(data, sort_keys=False), encoding="utf-8"
    )


def _set_datasheet_staging_value(context, key: str, value: Any) -> None:
    """Merge one ``defaults.datasheet_staging.<key>`` value into common.jbom.yaml."""

    data = _read_common_profile(context)
    defaults_stanza = data.get("defaults")
    if not isinstance(defaults_stanza, dict):
        defaults_stanza = {}
    staging_cfg = defaults_stanza.get("datasheet_staging")
    if not isinstance(staging_cfg, dict):
        staging_cfg = {}
    staging_cfg[key] = value
    defaults_stanza["datasheet_staging"] = staging_cfg
    data["defaults"] = defaults_stanza
    _write_common_profile(context, data)


def _fixture_manifest_path(context) -> Path:
    """Return this scenario's fixture manifest path, creating it if needed."""

    manifest_path = Path(context.sandbox_root) / "_datasheet_fixtures.json"
    if not manifest_path.is_file():
        manifest_path.write_text("{}", encoding="utf-8")
        _set_datasheet_staging_value(
            context, "fetch_fixtures_manifest", str(manifest_path)
        )
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


def _staging_dir(context) -> Path:
    staging_dir = getattr(context, "staging_dir", None)
    assert staging_dir is not None, "Use 'Given a staging directory' first"
    return staging_dir


@given("a staging directory")
def given_a_staging_directory(context) -> None:
    """Configure datasheet_staging.staging_dir to an isolated sandbox path.

    Also mirrors generic.jbom.yaml's shipped fetch-budget defaults
    (max_fetches_per_run=20, fetch_time_budget_seconds=30): scenarios in
    this feature also write a supplier profile to the sandbox's own
    ``.jbom/generic.jbom.yaml`` (see ``project_centric_steps.py``), which
    shadows the builtin generic profile entirely -- including the
    datasheet_staging budget values it declares -- so this step supplies
    working defaults directly rather than relying on the (shadowed)
    builtin.
    """

    staging_dir = Path(context.sandbox_root) / "staging"
    context.staging_dir = staging_dir
    _set_datasheet_staging_value(context, "staging_dir", str(staging_dir))
    _set_datasheet_staging_value(context, "max_fetches_per_run", 20)
    _set_datasheet_staging_value(context, "fetch_time_budget_seconds", 30)


@given("the datasheet staging fetch budget is {count:d} fetch per run")
@given("the datasheet staging fetch budget is {count:d} fetches per run")
def given_the_datasheet_staging_fetch_budget(context, count: int) -> None:
    """Configure datasheet_staging.max_fetches_per_run."""

    _set_datasheet_staging_value(context, "max_fetches_per_run", count)


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


@then("the staging directory contains exactly {count:d} staged file")
@then("the staging directory contains exactly {count:d} staged files")
def then_staging_dir_contains_exactly_n_staged_files(context, count: int) -> None:
    staging_dir = _staging_dir(context)
    staged = (
        list(staging_dir.glob("*.pdf")) + list(staging_dir.glob("*.unverified"))
        if staging_dir.is_dir()
        else []
    )
    assert (
        len(staged) == count
    ), f"Expected exactly {count} staged file(s), found {len(staged)}: {staged}"
