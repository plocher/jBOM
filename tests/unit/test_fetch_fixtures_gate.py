"""Unit tests for the test-only fetch-fixtures gate (jBOM#372)."""

from __future__ import annotations

from pathlib import Path

import pytest

from jbom.common.fetch_fixtures import (
    ALLOW_FETCH_FIXTURES_ENV,
    FetchFixturesNotAllowedError,
    fetch_fixtures_allowed,
    require_fetch_fixtures_manifest,
    resolve_fixture_fetch,
)


@pytest.fixture(autouse=True)
def _clear_allow_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ALLOW_FETCH_FIXTURES_ENV, raising=False)


def test_empty_manifest_is_a_no_op() -> None:
    assert require_fetch_fixtures_manifest("") == ""
    assert require_fetch_fixtures_manifest("   ") == ""
    assert resolve_fixture_fetch("") is None


def test_manifest_without_allow_env_raises_loudly(tmp_path: Path) -> None:
    manifest = str(tmp_path / "fixtures.json")
    with pytest.raises(FetchFixturesNotAllowedError, match=ALLOW_FETCH_FIXTURES_ENV):
        require_fetch_fixtures_manifest(manifest)


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on", " Yes "])
def test_truthy_allow_env_enables_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, value: str, capsys
) -> None:
    monkeypatch.setenv(ALLOW_FETCH_FIXTURES_ENV, value)
    assert fetch_fixtures_allowed() is True

    manifest = str(tmp_path / "fixtures.json")
    assert require_fetch_fixtures_manifest(manifest) == manifest

    err = capsys.readouterr().err
    assert "test-only fetch fixtures are ACTIVE" in err
    assert manifest in err


@pytest.mark.parametrize("value", ["0", "false", "no", "off", ""])
def test_non_truthy_allow_env_still_refuses(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, value: str
) -> None:
    monkeypatch.setenv(ALLOW_FETCH_FIXTURES_ENV, value)
    assert fetch_fixtures_allowed() is False
    with pytest.raises(FetchFixturesNotAllowedError):
        require_fetch_fixtures_manifest(str(tmp_path / "fixtures.json"))


def test_resolve_fixture_fetch_reads_manifest_bytes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(ALLOW_FETCH_FIXTURES_ENV, "1")
    payload = b"%PDF-1.4 fixture"
    fixture_file = tmp_path / "doc.pdf"
    fixture_file.write_bytes(payload)
    manifest_path = tmp_path / "manifest.json"
    url = "https://example.com/docs/a.pdf"
    manifest_path.write_text(
        f'{{"{url}": "{fixture_file}"}}',
        encoding="utf-8",
    )

    fetch = resolve_fixture_fetch(str(manifest_path))
    assert fetch is not None
    assert fetch(url) == payload
