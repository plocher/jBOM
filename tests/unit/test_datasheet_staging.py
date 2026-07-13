"""Unit tests for jbom.services.datasheet_staging (jBOM#355).

All fetches are injected fakes; no real network access is ever performed
(and the autouse ``_hermetic_datasheet_staging`` fixture in ``tests/conftest.py``
would raise loudly if one slipped through).
"""

from __future__ import annotations

from pathlib import Path

from jbom.common.types import InventoryItem
from jbom.config.defaults import DefaultsConfig
from jbom.services.datasheet_staging import (
    find_existing_staged_path,
    is_admitted,
    looks_like_html,
    looks_like_pdf,
    resolve_staging_dir,
    stage_datasheet_url,
    stage_datasheet_urls,
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


def _defaults_with_staging_dir(staging_dir: Path) -> DefaultsConfig:
    # max_fetches_per_run / fetch_time_budget_seconds mirror generic.jbom.yaml's
    # shipped values: DatasheetStagingConfig's own Python-level defaults are
    # deliberately 0/0.0 ("unconfigured"), per jBOM's no-hardcoded-defaults-in-
    # code convention -- real values always come from the profile.
    return DefaultsConfig.model_validate(
        {
            "datasheet_staging": {
                "staging_dir": str(staging_dir),
                "max_fetches_per_run": 20,
                "fetch_time_budget_seconds": 30.0,
            }
        }
    )


def _defaults_with_budget(
    *, max_fetches_per_run: int = 20, fetch_time_budget_seconds: float = 30.0
) -> DefaultsConfig:
    return DefaultsConfig.model_validate(
        {
            "datasheet_staging": {
                "max_fetches_per_run": max_fetches_per_run,
                "fetch_time_budget_seconds": fetch_time_budget_seconds,
            }
        }
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
    def test_explicit_override_wins(self, tmp_path: Path) -> None:
        cfg = _defaults_with_staging_dir(tmp_path / "profile-staging")
        explicit = tmp_path / "explicit"
        assert resolve_staging_dir(explicit, defaults=cfg) == explicit

    def test_profile_configured_staging_dir_is_honored(self, tmp_path: Path) -> None:
        configured = tmp_path / "profile-staging"
        cfg = _defaults_with_staging_dir(configured)
        assert resolve_staging_dir(defaults=cfg) == configured

    def test_profile_staging_dir_supports_tilde_expansion(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))
        cfg = DefaultsConfig.model_validate(
            {"datasheet_staging": {"staging_dir": "~/my-staging"}}
        )
        assert resolve_staging_dir(defaults=cfg) == tmp_path / "my-staging"

    def test_returns_none_when_unconfigured(self) -> None:
        # staging_dir is a user-machine binding (names a local
        # SPCoast-inventory checkout); there is deliberately no code-level
        # fallback path, so an unconfigured profile means "inactive".
        cfg = DefaultsConfig.model_validate({})
        assert resolve_staging_dir(defaults=cfg) is None


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
    def test_inactive_when_staging_dir_is_none(self) -> None:
        outcome = stage_datasheet_url(
            "https://example.com/docs/lm358.pdf",
            staging_dir=None,
            fetch=_unused_fetch,
        )
        assert outcome.status == "inactive"

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

    def test_fixture_manifest_resolves_bytes_without_a_fetch_callable(
        self, tmp_path: Path
    ) -> None:
        pdf_file = tmp_path / "fixture.pdf"
        pdf_file.write_bytes(_PDF_BYTES)
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(
            '{"https://example.com/docs/lm358.pdf": "%s"}' % pdf_file, encoding="utf-8"
        )

        outcome = stage_datasheet_url(
            "https://example.com/docs/lm358.pdf",
            staging_dir=tmp_path / "staging",
            fetch_fixtures_manifest=str(manifest_path),
        )

        assert outcome.status == "verified"


class TestStageDatasheetUrls:
    def test_inert_when_staging_dir_unconfigured(self) -> None:
        cfg = DefaultsConfig.model_validate({})
        entries = [("https://example.com/docs/a.pdf", None)]

        result = stage_datasheet_urls(entries, defaults=cfg)

        assert result.outcomes == []
        assert result.attempted == 0
        assert result.budget_exceeded is False

    def test_stages_multiple_entries(self, tmp_path: Path) -> None:
        cfg = _defaults_with_staging_dir(tmp_path)
        entries = [
            ("https://example.com/docs/a.pdf", None),
            ("https://example.com/docs/b.pdf", None),
        ]

        # Real calls require monkeypatching default_fetch (module-level),
        # which the autouse hermetic fixture forbids by default -- so patch
        # it locally for this test.
        import jbom.services.datasheet_staging as _mod

        original = _mod.default_fetch
        try:
            _mod.default_fetch = lambda url, **_: _PDF_BYTES
            result = stage_datasheet_urls(entries, defaults=cfg)
        finally:
            _mod.default_fetch = original

        assert len(result.outcomes) == 2
        assert all(o.status == "verified" for o in result.outcomes)
        assert result.attempted == 2
        assert result.budget_exceeded is False
        assert result.summary_message() == ""

    def test_empty_and_admitted_entries_are_free(self, tmp_path: Path) -> None:
        cfg = _defaults_with_staging_dir(tmp_path)
        admitted_item = _make_item(datasheet_name="LM358-series")
        entries = [
            ("", None),
            ("https://example.com/docs/admitted.pdf", admitted_item),
        ]

        result = stage_datasheet_urls(entries, defaults=cfg)

        assert len(result.outcomes) == 1
        assert result.outcomes[0].status == "admitted-skip"
        assert result.attempted == 0
        assert result.budget_exceeded is False

    def test_max_fetches_per_run_caps_real_fetch_attempts(self, tmp_path: Path) -> None:
        cfg = _defaults_with_budget(
            max_fetches_per_run=1, fetch_time_budget_seconds=30.0
        )
        # Redirect staging_dir onto tmp_path via a second profile merge.
        cfg = DefaultsConfig.model_validate(
            {
                "datasheet_staging": {
                    "staging_dir": str(tmp_path),
                    "max_fetches_per_run": 1,
                    "fetch_time_budget_seconds": 30.0,
                }
            }
        )
        entries = [
            ("https://example.com/docs/a.pdf", None),
            ("https://example.com/docs/b.pdf", None),
            ("https://example.com/docs/c.pdf", None),
        ]

        import jbom.services.datasheet_staging as _mod

        original = _mod.default_fetch
        try:
            _mod.default_fetch = lambda url, **_: _PDF_BYTES
            result = stage_datasheet_urls(entries, defaults=cfg)
        finally:
            _mod.default_fetch = original

        assert result.attempted == 1
        assert result.budget_exceeded is True
        assert result.skipped_for_budget == 2
        assert len(result.outcomes) == 1
        assert "budget exceeded" in result.summary_message()

    def test_zero_time_budget_blocks_all_real_fetches(self, tmp_path: Path) -> None:
        cfg = DefaultsConfig.model_validate(
            {
                "datasheet_staging": {
                    "staging_dir": str(tmp_path),
                    "max_fetches_per_run": 20,
                    "fetch_time_budget_seconds": 0.0,
                }
            }
        )
        entries = [("https://example.com/docs/a.pdf", None)]

        import jbom.services.datasheet_staging as _mod

        original = _mod.default_fetch
        try:
            _mod.default_fetch = lambda url, **_: _PDF_BYTES
            result = stage_datasheet_urls(entries, defaults=cfg)
        finally:
            _mod.default_fetch = original

        assert result.attempted == 0
        assert result.budget_exceeded is True
        assert result.skipped_for_budget == 1

    def test_free_entries_do_not_count_against_budget(self, tmp_path: Path) -> None:
        cfg = DefaultsConfig.model_validate(
            {
                "datasheet_staging": {
                    "staging_dir": str(tmp_path),
                    "max_fetches_per_run": 1,
                    "fetch_time_budget_seconds": 30.0,
                }
            }
        )
        admitted_item = _make_item(datasheet_name="LM358-series")
        entries = [
            ("https://example.com/docs/admitted-1.pdf", admitted_item),
            ("https://example.com/docs/admitted-2.pdf", admitted_item),
            ("https://example.com/docs/real.pdf", None),
        ]

        import jbom.services.datasheet_staging as _mod

        original = _mod.default_fetch
        try:
            _mod.default_fetch = lambda url, **_: _PDF_BYTES
            result = stage_datasheet_urls(entries, defaults=cfg)
        finally:
            _mod.default_fetch = original

        assert result.attempted == 1
        assert result.budget_exceeded is False
        assert [o.status for o in result.outcomes] == [
            "admitted-skip",
            "admitted-skip",
            "verified",
        ]


def _unused_fetch(url: str) -> bytes:  # pragma: no cover - defensive guard
    raise AssertionError(f"fetch should not have been called for {url!r}")
