"""Unit tests for jbom.services.datasheet_staging (jBOM#355).

All fetches are injected fakes; no real network access is ever performed.
"""

from __future__ import annotations

from pathlib import Path

from jbom.common.types import InventoryItem
from jbom.services.datasheet_staging import (
    find_existing_staged_path,
    is_admitted,
    looks_like_html,
    looks_like_pdf,
    resolve_staging_dir,
    stage_datasheet_url,
    staged_filename_for_url,
)

_PDF_BYTES = b"%PDF-1.4\n%...rest of a minimal pdf...\n%%EOF"
_HTML_BYTES = b"<!DOCTYPE html><html><head></head><body>Not found</body></html>"
_JUNK_BYTES = b"this is neither a pdf nor html"


def _make_item(*, datasheet_name: str = "") -> InventoryItem:
    return InventoryItem(
        ipn="RES_10K_0603",
        keywords="",
        category="RES",
        description="",
        smd="",
        value="10K",
        type="",
        tolerance="",
        voltage="",
        amperage="",
        wattage="",
        raw_data={"Datasheet Name": datasheet_name} if datasheet_name else {},
    )


class TestLooksLikePdf:
    def test_true_for_pdf_magic_at_start(self) -> None:
        assert looks_like_pdf(_PDF_BYTES) is True

    def test_true_for_pdf_magic_with_small_prefix(self) -> None:
        # Some PDFs have a small amount of leading junk before %PDF-.
        assert looks_like_pdf(b"\xef\xbb\xbf" + _PDF_BYTES) is True

    def test_false_for_html(self) -> None:
        assert looks_like_pdf(_HTML_BYTES) is False

    def test_false_for_empty_content(self) -> None:
        assert looks_like_pdf(b"") is False

    def test_false_for_unrelated_binary(self) -> None:
        assert looks_like_pdf(_JUNK_BYTES) is False


class TestLooksLikeHtml:
    def test_true_for_doctype_html(self) -> None:
        assert looks_like_html(_HTML_BYTES) is True

    def test_true_for_bare_html_tag(self) -> None:
        assert looks_like_html(b"<html><body>hi</body></html>") is True

    def test_false_for_pdf(self) -> None:
        assert looks_like_html(_PDF_BYTES) is False

    def test_false_for_unrelated_binary(self) -> None:
        assert looks_like_html(_JUNK_BYTES) is False


class TestStagedFilenameForUrl:
    def test_stable_for_same_url(self) -> None:
        url = "https://example.com/docs/LM358.pdf"
        assert staged_filename_for_url(url) == staged_filename_for_url(url)

    def test_different_urls_with_same_basename_do_not_collide(self) -> None:
        stem_a = staged_filename_for_url("https://supplier-a.com/ds/datasheet.pdf")
        stem_b = staged_filename_for_url("https://supplier-b.com/ds/datasheet.pdf")
        assert stem_a != stem_b

    def test_uses_sanitized_basename_as_prefix(self) -> None:
        stem = staged_filename_for_url("https://example.com/docs/LM358.pdf")
        assert stem.startswith("LM358-")

    def test_falls_back_to_generic_stem_for_url_without_path(self) -> None:
        stem = staged_filename_for_url("https://example.com")
        assert stem.startswith("datasheet-")

    def test_sanitizes_unsafe_characters(self) -> None:
        stem = staged_filename_for_url("https://example.com/a b?c=d.pdf")
        prefix = stem.rsplit("-", 1)[0]
        assert all(ch.isalnum() or ch in "._-" for ch in prefix)


class TestIsAdmitted:
    def test_false_when_item_is_none(self) -> None:
        assert is_admitted(None) is False

    def test_false_when_datasheet_name_absent(self) -> None:
        assert is_admitted(_make_item()) is False

    def test_false_when_datasheet_name_blank(self) -> None:
        assert is_admitted(_make_item(datasheet_name="   ")) is False

    def test_true_when_datasheet_name_present(self) -> None:
        assert is_admitted(_make_item(datasheet_name="LM358-series")) is True


class TestResolveStagingDir:
    def test_explicit_override_wins(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("JBOM_STAGING_DIR", str(tmp_path / "env-staging"))
        monkeypatch.setenv("JBOM_INVENTORY_ROOT", str(tmp_path / "env-root"))
        explicit = tmp_path / "explicit"
        assert resolve_staging_dir(explicit) == explicit

    def test_staging_dir_env_var_used_when_no_explicit(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        staging_dir = tmp_path / "env-staging"
        monkeypatch.setenv("JBOM_STAGING_DIR", str(staging_dir))
        monkeypatch.delenv("JBOM_INVENTORY_ROOT", raising=False)
        assert resolve_staging_dir() == staging_dir

    def test_inventory_root_env_var_appends_staging(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        root = tmp_path / "SPCoast-inventory"
        monkeypatch.delenv("JBOM_STAGING_DIR", raising=False)
        monkeypatch.setenv("JBOM_INVENTORY_ROOT", str(root))
        assert resolve_staging_dir() == root / "staging"

    def test_default_when_nothing_configured(self, monkeypatch) -> None:
        monkeypatch.delenv("JBOM_STAGING_DIR", raising=False)
        monkeypatch.delenv("JBOM_INVENTORY_ROOT", raising=False)
        result = resolve_staging_dir()
        assert result.name == "staging"
        assert "SPCoast-inventory" in result.parts


class TestFindExistingStagedPath:
    def test_returns_none_when_nothing_staged(self, tmp_path: Path) -> None:
        assert find_existing_staged_path(tmp_path, "stem-abc") is None

    def test_returns_verified_path_when_present(self, tmp_path: Path) -> None:
        verified = tmp_path / "stem-abc.pdf"
        verified.write_bytes(_PDF_BYTES)
        assert find_existing_staged_path(tmp_path, "stem-abc") == verified

    def test_returns_unverified_path_when_only_that_exists(
        self, tmp_path: Path
    ) -> None:
        unverified = tmp_path / "stem-abc.unverified"
        unverified.write_bytes(_HTML_BYTES)
        assert find_existing_staged_path(tmp_path, "stem-abc") == unverified

    def test_prefers_verified_over_unverified(self, tmp_path: Path) -> None:
        verified = tmp_path / "stem-abc.pdf"
        verified.write_bytes(_PDF_BYTES)
        (tmp_path / "stem-abc.unverified").write_bytes(_HTML_BYTES)
        assert find_existing_staged_path(tmp_path, "stem-abc") == verified


class TestStageDatasheetUrl:
    def test_empty_url_is_skipped(self, tmp_path: Path) -> None:
        outcome = stage_datasheet_url("", staging_dir=tmp_path, fetch=_unused_fetch)
        assert outcome.status == "skip-empty-url"
        assert outcome.path is None

    def test_admitted_item_is_skipped_without_fetching(self, tmp_path: Path) -> None:
        item = _make_item(datasheet_name="LM358-series")
        calls: list[str] = []

        def _tracking_fetch(url: str) -> bytes:
            calls.append(url)
            return _PDF_BYTES

        outcome = stage_datasheet_url(
            "https://example.com/lm358.pdf",
            item=item,
            staging_dir=tmp_path,
            fetch=_tracking_fetch,
        )

        assert outcome.status == "admitted-skip"
        assert calls == []
        assert list(tmp_path.glob("*")) == []

    def test_verified_pdf_is_written_with_pdf_suffix(self, tmp_path: Path) -> None:
        outcome = stage_datasheet_url(
            "https://example.com/docs/lm358.pdf",
            staging_dir=tmp_path,
            fetch=lambda url: _PDF_BYTES,
        )

        assert outcome.status == "verified"
        assert outcome.path is not None
        assert outcome.path.suffix == ".pdf"
        assert outcome.path.read_bytes() == _PDF_BYTES

    def test_html_response_is_flagged_and_kept_unverified(self, tmp_path: Path) -> None:
        outcome = stage_datasheet_url(
            "https://example.com/docs/lm358.pdf",
            staging_dir=tmp_path,
            fetch=lambda url: _HTML_BYTES,
        )

        assert outcome.status == "flagged"
        assert outcome.path is not None
        assert outcome.path.name.endswith(".unverified")
        assert outcome.path.read_bytes() == _HTML_BYTES
        assert "HTML impostor" in outcome.message

    def test_non_pdf_non_html_response_is_flagged_as_unrecognized(
        self, tmp_path: Path
    ) -> None:
        outcome = stage_datasheet_url(
            "https://example.com/docs/lm358.pdf",
            staging_dir=tmp_path,
            fetch=lambda url: _JUNK_BYTES,
        )

        assert outcome.status == "flagged"
        assert "unrecognized content" in outcome.message

    def test_already_verified_staged_file_is_not_refetched(
        self, tmp_path: Path
    ) -> None:
        url = "https://example.com/docs/lm358.pdf"
        first = stage_datasheet_url(
            url, staging_dir=tmp_path, fetch=lambda u: _PDF_BYTES
        )
        assert first.status == "verified"

        calls: list[str] = []

        def _tracking_fetch(u: str) -> bytes:
            calls.append(u)
            return _PDF_BYTES

        second = stage_datasheet_url(url, staging_dir=tmp_path, fetch=_tracking_fetch)

        assert second.status == "staged-skip"
        assert calls == []

    def test_already_flagged_unverified_file_is_not_refetched(
        self, tmp_path: Path
    ) -> None:
        url = "https://example.com/docs/lm358.pdf"
        first = stage_datasheet_url(
            url, staging_dir=tmp_path, fetch=lambda u: _HTML_BYTES
        )
        assert first.status == "flagged"

        calls: list[str] = []

        def _tracking_fetch(u: str) -> bytes:
            calls.append(u)
            return _HTML_BYTES

        second = stage_datasheet_url(url, staging_dir=tmp_path, fetch=_tracking_fetch)

        assert second.status == "staged-skip"
        assert calls == []

    def test_fetch_error_is_reported_without_raising(self, tmp_path: Path) -> None:
        def _boom(url: str) -> bytes:
            raise RuntimeError("connection reset")

        outcome = stage_datasheet_url(
            "https://example.com/docs/lm358.pdf",
            staging_dir=tmp_path,
            fetch=_boom,
        )

        assert outcome.status == "fetch-error"
        assert "connection reset" in outcome.message
        assert list(tmp_path.glob("*")) == []

    def test_staging_dir_is_created_on_first_write(self, tmp_path: Path) -> None:
        staging_dir = tmp_path / "nested" / "staging"
        assert not staging_dir.exists()

        outcome = stage_datasheet_url(
            "https://example.com/docs/lm358.pdf",
            staging_dir=staging_dir,
            fetch=lambda url: _PDF_BYTES,
        )

        assert outcome.status == "verified"
        assert staging_dir.is_dir()


def _unused_fetch(url: str) -> bytes:  # pragma: no cover - defensive guard
    raise AssertionError(f"fetch should not have been called for {url!r}")
