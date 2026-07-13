"""Step definitions for ``jbom audit --check-urls`` (jBOM#358).

Network access is never exercised in these scenarios: the CLI runs as a
subprocess (see ``features/steps/common_steps.py``), and the
``defaults.check_urls.fetch_fixtures_manifest`` profile key redirects the
recovery-ladder fetch to read response bytes from local fixture files
written by these steps instead of making real HTTP requests (see
``jbom.services.datasheet_url_upgrade_report``).

This mirrors the pattern used for the always-on datasheet staging fetch
in ``features/steps/datasheet_staging_steps.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from behave import given

_PDF_FIXTURE_BYTES = b"%PDF-1.4\n%fixture datasheet for jBOM#358 BDD scenarios\n%%EOF"
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


def _set_check_urls_value(context, key: str, value: Any) -> None:
    """Merge one ``defaults.check_urls.<key>`` value into common.jbom.yaml."""

    data = _read_common_profile(context)
    defaults_stanza = data.get("defaults")
    if not isinstance(defaults_stanza, dict):
        defaults_stanza = {}
    check_urls_cfg = defaults_stanza.get("check_urls")
    if not isinstance(check_urls_cfg, dict):
        check_urls_cfg = {}
    check_urls_cfg[key] = value
    defaults_stanza["check_urls"] = check_urls_cfg
    data["defaults"] = defaults_stanza
    _write_common_profile(context, data)


def _fixture_manifest_path(context) -> Path:
    """Return this scenario's fixture manifest path, creating it if needed."""

    manifest_path = Path(context.sandbox_root) / "_check_urls_fixtures.json"
    if not manifest_path.is_file():
        manifest_path.write_text("{}", encoding="utf-8")
        _set_check_urls_value(context, "fetch_fixtures_manifest", str(manifest_path))
    return manifest_path


def _register_fixture(context, url: str, content: bytes) -> None:
    manifest_path = _fixture_manifest_path(context)
    fixtures_dir = Path(context.sandbox_root) / "_check_urls_fixture_files"
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    fixture_file = fixtures_dir / f"fixture-{len(list(fixtures_dir.glob('*')))}.bin"
    fixture_file.write_bytes(content)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[url] = str(fixture_file)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


@given("a check-urls fixture manifest")
def given_a_check_urls_fixture_manifest(context) -> None:
    """Ensure the fixture manifest exists, even if no URL fixture is ever registered.

    Any URL not explicitly registered via the steps below will raise inside
    the recovery ladder's fetch, which is treated as a fetch error (dead
    link) by :mod:`jbom.services.datasheet_url_recovery` -- never a silent
    fallback to the real network.
    """

    _fixture_manifest_path(context)


@given('the check-urls URL "{url}" resolves to a PDF')
def given_check_urls_url_resolves_to_pdf(context, url: str) -> None:
    """Register a fixture so fetching *url* returns verified PDF bytes."""

    _register_fixture(context, url, _PDF_FIXTURE_BYTES)


@given('the check-urls URL "{url}" resolves to HTML')
def given_check_urls_url_resolves_to_html(context, url: str) -> None:
    """Register a fixture so fetching *url* returns HTML-impostor bytes."""

    _register_fixture(context, url, _HTML_FIXTURE_BYTES)


@given(
    'the check-urls LCSC product-detail API for "{product_code}" returns '
    'durable PDF URL "{durable_url}"'
)
def given_check_urls_product_detail_api_response(
    context, product_code: str, durable_url: str
) -> None:
    """Register the LCSC product-detail API fixture for rung 3 (jBOM#358)."""

    from jbom.services.datasheet_url_recovery import product_detail_api_url

    api_url = product_detail_api_url(product_code)
    api_response = json.dumps({"result": {"pdfUrl": durable_url}}).encode("utf-8")
    _register_fixture(context, api_url, api_response)
