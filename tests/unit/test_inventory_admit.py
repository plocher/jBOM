"""Unit tests for jbom.services.inventory_admit (jBOM#356)."""

from __future__ import annotations

import io
from pathlib import Path

from jbom.common.types import InventoryItem
from jbom.services.inventory_admit import (
    ACTION_ADMIT,
    ACTION_SKIP,
    DISPOSITION_COLLISION,
    DISPOSITION_DUPE_OF,
    DISPOSITION_NEW,
    DISPOSITION_UNRESOLVABLE,
    AdmitManifestRow,
    apply_admit_manifest,
    invalid_proposed_name_reason,
    never_rename_violation,
    propose_admit_manifest,
    propose_document_name,
    read_admit_manifest,
    write_admit_manifest,
    write_paste_file,
)

_PDF_BYTES_A = b"%PDF-1.4\n%datasheet A\n%%EOF"
_PDF_BYTES_B = b"%PDF-1.4\n%datasheet B (different content)\n%%EOF"


def _item(
    *,
    ipn: str,
    category: str = "RES",
    manufacturer: str = "Uniroyal",
    mfgpn: str = "0603WAJ0331T5E",
    datasheet: str = "",
    datasheet_name: str = "",
) -> InventoryItem:
    raw_data = {}
    if datasheet_name:
        raw_data["Datasheet Name"] = datasheet_name
    return InventoryItem(
        ipn=ipn,
        keywords="",
        category=category,
        description="",
        smd="",
        value="10K",
        type="",
        tolerance="",
        voltage="",
        amperage="",
        wattage="",
        manufacturer=manufacturer,
        mfgpn=mfgpn,
        datasheet=datasheet,
        raw_data=raw_data,
    )


class TestProposeDocumentName:
    def test_single_mpn_uses_verbatim_token(self) -> None:
        name = propose_document_name(
            category="RES", manufacturer="Uniroyal", mfgpn_candidates=["0603WAJ0331T5E"]
        )
        assert name == "Resistor-Uniroyal-0603WAJ0331T5E"

    def test_family_candidates_truncate_to_common_prefix_with_series_suffix(
        self,
    ) -> None:
        name = propose_document_name(
            category="RES",
            manufacturer="Uniroyal",
            mfgpn_candidates=["0603WAJ0331T5E", "0603WAJ0332T5E", "0603WAJ0333T5E"],
        )
        assert name == "Resistor-Uniroyal-0603WAJ033-series"

    def test_no_common_prefix_falls_back_to_first_candidate(self) -> None:
        name = propose_document_name(
            category="IC", manufacturer="TI", mfgpn_candidates=["LM358D", "NE555P"]
        )
        assert name == "IC-TI-LM358D"

    def test_unknown_category_is_title_cased(self) -> None:
        name = propose_document_name(
            category="WIDGET", manufacturer="Acme", mfgpn_candidates=["W-1"]
        )
        assert name.startswith("Widget-Acme-")

    def test_sanitizes_unsafe_characters_in_tokens(self) -> None:
        name = propose_document_name(
            category="CAP",
            manufacturer="UNI-ROYAL(厚声)",
            mfgpn_candidates=["CC0603KPX7R8BB103"],
        )
        assert all(ch.isalnum() or ch == "-" for ch in name)


class TestNeverRenameViolation:
    def test_returns_none_when_no_existing_file(self, tmp_path: Path) -> None:
        staged = tmp_path / "staged.pdf"
        staged.write_bytes(_PDF_BYTES_A)
        library_dir = tmp_path / "datasheets"
        assert (
            never_rename_violation(
                proposed_name="New-Doc", staged_path=staged, library_dir=library_dir
            )
            is None
        )

    def test_returns_none_when_content_is_byte_identical(self, tmp_path: Path) -> None:
        library_dir = tmp_path / "datasheets"
        library_dir.mkdir()
        (library_dir / "Existing-Doc.pdf").write_bytes(_PDF_BYTES_A)
        staged = tmp_path / "staged.pdf"
        staged.write_bytes(_PDF_BYTES_A)
        assert (
            never_rename_violation(
                proposed_name="Existing-Doc",
                staged_path=staged,
                library_dir=library_dir,
            )
            is None
        )

    def test_returns_existing_stem_when_content_differs(self, tmp_path: Path) -> None:
        library_dir = tmp_path / "datasheets"
        library_dir.mkdir()
        (library_dir / "Existing-Doc.pdf").write_bytes(_PDF_BYTES_A)
        staged = tmp_path / "staged.pdf"
        staged.write_bytes(_PDF_BYTES_B)
        assert (
            never_rename_violation(
                proposed_name="Existing-Doc",
                staged_path=staged,
                library_dir=library_dir,
            )
            == "Existing-Doc"
        )

    def test_collision_is_case_insensitive(self, tmp_path: Path) -> None:
        library_dir = tmp_path / "datasheets"
        library_dir.mkdir()
        (library_dir / "Existing-Doc.pdf").write_bytes(_PDF_BYTES_A)
        staged = tmp_path / "staged.pdf"
        staged.write_bytes(_PDF_BYTES_B)
        assert (
            never_rename_violation(
                proposed_name="existing-doc",
                staged_path=staged,
                library_dir=library_dir,
            )
            == "Existing-Doc"
        )


class TestInvalidProposedNameReason:
    def test_none_for_safe_name(self, tmp_path: Path) -> None:
        library_dir = tmp_path / "datasheets"
        assert (
            invalid_proposed_name_reason("IC-TI-LM358D", library_dir=library_dir)
            is None
        )

    def test_rejects_relative_path_traversal(self, tmp_path: Path) -> None:
        library_dir = tmp_path / "datasheets"
        reason = invalid_proposed_name_reason("../../evil", library_dir=library_dir)
        assert reason is not None
        assert "path separator" in reason

    def test_rejects_nested_subdirectory(self, tmp_path: Path) -> None:
        library_dir = tmp_path / "datasheets"
        reason = invalid_proposed_name_reason("sub/evil", library_dir=library_dir)
        assert reason is not None

    def test_rejects_backslash_traversal(self, tmp_path: Path) -> None:
        library_dir = tmp_path / "datasheets"
        reason = invalid_proposed_name_reason("..\\evil", library_dir=library_dir)
        assert reason is not None

    def test_rejects_absolute_path(self, tmp_path: Path) -> None:
        library_dir = tmp_path / "datasheets"
        reason = invalid_proposed_name_reason("/etc/passwd", library_dir=library_dir)
        assert reason is not None

    def test_rejects_bare_dot_dot(self, tmp_path: Path) -> None:
        library_dir = tmp_path / "datasheets"
        reason = invalid_proposed_name_reason("..", library_dir=library_dir)
        assert reason is not None

    def test_rejects_empty_name(self, tmp_path: Path) -> None:
        library_dir = tmp_path / "datasheets"
        reason = invalid_proposed_name_reason("   ", library_dir=library_dir)
        assert reason is not None


class TestManifestCsvRoundTrip:
    def test_round_trips_all_fields(self) -> None:
        rows = [
            AdmitManifestRow(
                action=ACTION_ADMIT,
                proposed_name="Resistor-Uniroyal-0603WAJ-series",
                disposition=DISPOSITION_NEW,
                dupe_of="",
                staged_file="stem-abc123.pdf",
                source_url="https://example.com/ds.pdf",
                member_ipns=("RES_A", "RES_B", "RES_C"),
            )
        ]
        buf = io.StringIO()
        write_admit_manifest(rows, buf)
        buf.seek(0)
        parsed = read_admit_manifest(buf)

        assert len(parsed) == 1
        assert parsed[0] == rows[0]

    def test_round_trips_empty_member_ipns(self) -> None:
        rows = [
            AdmitManifestRow(
                action=ACTION_SKIP,
                proposed_name="",
                disposition=DISPOSITION_UNRESOLVABLE,
                dupe_of="",
                staged_file="orphan-xyz.pdf",
                source_url="",
                member_ipns=(),
            )
        ]
        buf = io.StringIO()
        write_admit_manifest(rows, buf)
        buf.seek(0)
        parsed = read_admit_manifest(buf)

        assert parsed[0].member_ipns == ()

    def test_human_edits_survive_round_trip(self) -> None:
        """A human editing Action/ProposedName in the CSV is what apply reads back."""
        buf = io.StringIO(
            "Action,ProposedName,Disposition,DupeOf,StagedFile,SourceURL,MemberIPNs\n"
            "ADMIT,Human-Renamed-Doc,new,,stem-abc.pdf,https://x/y.pdf,RES_A;RES_B\n"
        )
        parsed = read_admit_manifest(buf)
        assert parsed[0].action == "ADMIT"
        assert parsed[0].proposed_name == "Human-Renamed-Doc"
        assert parsed[0].member_ipns == ("RES_A", "RES_B")

    def test_missing_optional_columns_default_to_empty(self) -> None:
        """A hand-trimmed manifest missing DupeOf/MemberIPNs must still parse."""
        buf = io.StringIO(
            "Action,ProposedName,Disposition,StagedFile,SourceURL\n"
            "ADMIT,Minimal-Doc,new,stem-min.pdf,https://x/min.pdf\n"
        )
        parsed = read_admit_manifest(buf)
        assert parsed[0].proposed_name == "Minimal-Doc"
        assert parsed[0].dupe_of == ""
        assert parsed[0].member_ipns == ()

    def test_duplicate_staged_file_rows_are_preserved_independently(self) -> None:
        """The manifest is a flat CSV with no uniqueness constraint on
        StagedFile/SourceURL -- a human accidentally duplicating a row (e.g.
        via spreadsheet copy-paste) must round-trip both rows unchanged;
        de-duplication is not this module's job. (apply_admit_manifest
        processes each row independently, so a duplicate simply re-attempts
        the same admission -- the second attempt becomes an idempotent
        no-op once the first succeeds.)
        """
        buf = io.StringIO(
            "Action,ProposedName,Disposition,DupeOf,StagedFile,SourceURL,MemberIPNs\n"
            "ADMIT,Dup-Doc,new,,stem-dup.pdf,https://x/dup.pdf,IC_A\n"
            "ADMIT,Dup-Doc,new,,stem-dup.pdf,https://x/dup.pdf,IC_A\n"
        )
        parsed = read_admit_manifest(buf)
        assert len(parsed) == 2
        assert parsed[0] == parsed[1]


class TestProposeAdmitManifest:
    def test_returns_empty_list_when_staging_dir_missing(self, tmp_path: Path) -> None:
        rows = propose_admit_manifest(
            staging_dir=tmp_path / "does-not-exist",
            library_dir=tmp_path / "datasheets",
            inventory_items=[],
        )
        assert rows == []

    def test_single_item_candidate_is_disposition_new(self, tmp_path: Path) -> None:
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()
        from jbom.services.datasheet_staging import staged_filename_for_url

        url = "https://example.com/docs/lm358.pdf"
        stem = staged_filename_for_url(url)
        (staging_dir / f"{stem}.pdf").write_bytes(_PDF_BYTES_A)

        items = [
            _item(
                ipn="IC_LM358",
                category="IC",
                manufacturer="TI",
                mfgpn="LM358D",
                datasheet=url,
            )
        ]

        rows = propose_admit_manifest(
            staging_dir=staging_dir,
            library_dir=tmp_path / "datasheets",
            inventory_items=items,
        )

        assert len(rows) == 1
        assert rows[0].disposition == DISPOSITION_NEW
        assert rows[0].action == ACTION_ADMIT
        assert rows[0].member_ipns == ("IC_LM358",)
        assert rows[0].proposed_name == "IC-TI-LM358D"

    def test_family_members_sharing_one_url_are_grouped_into_one_row(
        self, tmp_path: Path
    ) -> None:
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()
        from jbom.services.datasheet_staging import staged_filename_for_url

        url = "https://example.com/docs/0603waj-series.pdf"
        stem = staged_filename_for_url(url)
        (staging_dir / f"{stem}.pdf").write_bytes(_PDF_BYTES_A)

        items = [
            _item(ipn="RES_331", mfgpn="0603WAJ0331T5E", datasheet=url),
            _item(ipn="RES_332", mfgpn="0603WAJ0332T5E", datasheet=url),
            _item(ipn="RES_333", mfgpn="0603WAJ0333T5E", datasheet=url),
        ]

        rows = propose_admit_manifest(
            staging_dir=staging_dir,
            library_dir=tmp_path / "datasheets",
            inventory_items=items,
        )

        assert len(rows) == 1
        assert set(rows[0].member_ipns) == {"RES_331", "RES_332", "RES_333"}
        assert rows[0].proposed_name.endswith("-series")

    def test_already_admitted_items_are_excluded_from_backlog(
        self, tmp_path: Path
    ) -> None:
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()
        from jbom.services.datasheet_staging import staged_filename_for_url

        url = "https://example.com/docs/lm358.pdf"
        stem = staged_filename_for_url(url)
        (staging_dir / f"{stem}.pdf").write_bytes(_PDF_BYTES_A)

        items = [
            _item(
                ipn="IC_LM358",
                category="IC",
                mfgpn="LM358D",
                datasheet=url,
                datasheet_name="LM358-series",
            )
        ]

        rows = propose_admit_manifest(
            staging_dir=staging_dir,
            library_dir=tmp_path / "datasheets",
            inventory_items=items,
        )

        assert len(rows) == 1
        assert rows[0].disposition == DISPOSITION_UNRESOLVABLE

    def test_staged_file_with_no_matching_backlog_url_is_unresolvable(
        self, tmp_path: Path
    ) -> None:
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()
        (staging_dir / "orphan-abc123.pdf").write_bytes(_PDF_BYTES_A)

        rows = propose_admit_manifest(
            staging_dir=staging_dir,
            library_dir=tmp_path / "datasheets",
            inventory_items=[],
        )

        assert len(rows) == 1
        assert rows[0].disposition == DISPOSITION_UNRESOLVABLE
        assert rows[0].action == ACTION_SKIP

    def test_unverified_files_are_never_proposed(self, tmp_path: Path) -> None:
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()
        (staging_dir / "flagged-abc123.unverified").write_bytes(b"<html></html>")

        rows = propose_admit_manifest(
            staging_dir=staging_dir,
            library_dir=tmp_path / "datasheets",
            inventory_items=[],
        )

        assert rows == []

    def test_collision_with_existing_different_content_is_flagged(
        self, tmp_path: Path
    ) -> None:
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()
        library_dir = tmp_path / "datasheets"
        library_dir.mkdir()

        from jbom.services.datasheet_staging import staged_filename_for_url

        url = "https://example.com/docs/lm358.pdf"
        stem = staged_filename_for_url(url)
        (staging_dir / f"{stem}.pdf").write_bytes(_PDF_BYTES_B)
        (library_dir / "IC-TI-LM358D.pdf").write_bytes(_PDF_BYTES_A)

        items = [
            _item(
                ipn="IC_LM358",
                category="IC",
                manufacturer="TI",
                mfgpn="LM358D",
                datasheet=url,
            )
        ]

        rows = propose_admit_manifest(
            staging_dir=staging_dir, library_dir=library_dir, inventory_items=items
        )

        assert rows[0].disposition == DISPOSITION_COLLISION
        assert rows[0].action == ACTION_SKIP

    def test_byte_identical_existing_doc_is_dupe_of(self, tmp_path: Path) -> None:
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()
        library_dir = tmp_path / "datasheets"
        library_dir.mkdir()

        from jbom.services.datasheet_staging import staged_filename_for_url

        url = "https://example.com/docs/lm358.pdf"
        stem = staged_filename_for_url(url)
        (staging_dir / f"{stem}.pdf").write_bytes(_PDF_BYTES_A)
        (library_dir / "IC-TI-LM358D.pdf").write_bytes(_PDF_BYTES_A)

        items = [
            _item(
                ipn="IC_LM358",
                category="IC",
                manufacturer="TI",
                mfgpn="LM358D",
                datasheet=url,
            )
        ]

        rows = propose_admit_manifest(
            staging_dir=staging_dir, library_dir=library_dir, inventory_items=items
        )

        assert rows[0].disposition == DISPOSITION_DUPE_OF
        assert rows[0].dupe_of == "IC-TI-LM358D"
        assert rows[0].action == ACTION_ADMIT


class TestApplyAdmitManifest:
    def test_admits_new_document_and_moves_file(self, tmp_path: Path) -> None:
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()
        library_dir = tmp_path / "datasheets"
        (staging_dir / "stem-abc.pdf").write_bytes(_PDF_BYTES_A)

        rows = [
            AdmitManifestRow(
                action=ACTION_ADMIT,
                proposed_name="IC-TI-LM358D",
                disposition=DISPOSITION_NEW,
                dupe_of="",
                staged_file="stem-abc.pdf",
                source_url="https://example.com/lm358.pdf",
                member_ipns=("IC_LM358",),
            )
        ]

        result = apply_admit_manifest(
            rows, staging_dir=staging_dir, library_dir=library_dir
        )

        assert result.admitted_count == 1
        assert result.refused_count == 0
        assert (library_dir / "IC-TI-LM358D.pdf").is_file()
        assert not (staging_dir / "stem-abc.pdf").exists()
        assert result.paste_rows == [("IC_LM358", "IC-TI-LM358D")]

    def test_family_doc_names_every_member(self, tmp_path: Path) -> None:
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()
        library_dir = tmp_path / "datasheets"
        (staging_dir / "stem-fam.pdf").write_bytes(_PDF_BYTES_A)

        rows = [
            AdmitManifestRow(
                action=ACTION_ADMIT,
                proposed_name="Resistor-Uniroyal-0603WAJ-series",
                disposition=DISPOSITION_NEW,
                dupe_of="",
                staged_file="stem-fam.pdf",
                source_url="https://example.com/0603waj-series.pdf",
                member_ipns=("RES_331", "RES_332", "RES_333"),
            )
        ]

        result = apply_admit_manifest(
            rows, staging_dir=staging_dir, library_dir=library_dir
        )

        assert (library_dir / "Resistor-Uniroyal-0603WAJ-series.pdf").is_file()
        assert result.paste_rows == [
            ("RES_331", "Resistor-Uniroyal-0603WAJ-series"),
            ("RES_332", "Resistor-Uniroyal-0603WAJ-series"),
            ("RES_333", "Resistor-Uniroyal-0603WAJ-series"),
        ]

    def test_skip_rows_are_left_untouched(self, tmp_path: Path) -> None:
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()
        library_dir = tmp_path / "datasheets"
        (staging_dir / "stem-abc.pdf").write_bytes(_PDF_BYTES_A)

        rows = [
            AdmitManifestRow(
                action=ACTION_SKIP,
                proposed_name="IC-TI-LM358D",
                disposition=DISPOSITION_NEW,
                dupe_of="",
                staged_file="stem-abc.pdf",
                source_url="https://example.com/lm358.pdf",
                member_ipns=("IC_LM358",),
            )
        ]

        result = apply_admit_manifest(
            rows, staging_dir=staging_dir, library_dir=library_dir
        )

        assert result.admitted_count == 0
        assert (staging_dir / "stem-abc.pdf").is_file()
        assert not library_dir.exists()
        assert result.paste_rows == []

    def test_never_rename_guard_refuses_collision_without_mutating_anything(
        self, tmp_path: Path
    ) -> None:
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()
        library_dir = tmp_path / "datasheets"
        library_dir.mkdir()
        (staging_dir / "stem-new.pdf").write_bytes(_PDF_BYTES_B)
        (library_dir / "Published-Name.pdf").write_bytes(_PDF_BYTES_A)

        rows = [
            AdmitManifestRow(
                action=ACTION_ADMIT,
                # Case-variant of the published name -- still a collision on
                # case-insensitive filesystems (macOS/Dropbox), per jBOM#346.
                proposed_name="published-name",
                disposition=DISPOSITION_NEW,
                dupe_of="",
                staged_file="stem-new.pdf",
                source_url="https://example.com/other.pdf",
                member_ipns=("IC_OTHER",),
            )
        ]

        result = apply_admit_manifest(
            rows, staging_dir=staging_dir, library_dir=library_dir
        )

        assert result.refused_count == 1
        assert result.admitted_count == 0
        assert result.paste_rows == []
        # Neither the staged file nor the published file were touched, and
        # no second file was created (macOS/Dropbox filesystems are
        # case-insensitive, so "published-name.pdf" and "Published-Name.pdf"
        # are the same path -- assert via directory listing, not via a
        # second `.exists()` check that would trivially pass on such
        # filesystems).
        assert (staging_dir / "stem-new.pdf").read_bytes() == _PDF_BYTES_B
        assert (library_dir / "Published-Name.pdf").read_bytes() == _PDF_BYTES_A
        assert [p.name for p in library_dir.glob("*.pdf")] == ["Published-Name.pdf"]

    def test_reapplying_byte_identical_content_is_idempotent(
        self, tmp_path: Path
    ) -> None:
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()
        library_dir = tmp_path / "datasheets"
        library_dir.mkdir()
        (staging_dir / "stem-dupe.pdf").write_bytes(_PDF_BYTES_A)
        (library_dir / "Existing-Doc.pdf").write_bytes(_PDF_BYTES_A)

        rows = [
            AdmitManifestRow(
                action=ACTION_ADMIT,
                proposed_name="Existing-Doc",
                disposition=DISPOSITION_DUPE_OF,
                dupe_of="Existing-Doc",
                staged_file="stem-dupe.pdf",
                source_url="https://example.com/existing.pdf",
                member_ipns=("IC_DUPE",),
            )
        ]

        result = apply_admit_manifest(
            rows, staging_dir=staging_dir, library_dir=library_dir
        )

        assert result.outcomes[0].status == "already-admitted"
        assert result.admitted_count == 1
        assert result.refused_count == 0
        assert result.paste_rows == [("IC_DUPE", "Existing-Doc")]

    def test_missing_staged_file_is_skipped_not_errored(self, tmp_path: Path) -> None:
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()
        library_dir = tmp_path / "datasheets"

        rows = [
            AdmitManifestRow(
                action=ACTION_ADMIT,
                proposed_name="Ghost-Doc",
                disposition=DISPOSITION_NEW,
                dupe_of="",
                staged_file="does-not-exist.pdf",
                source_url="https://example.com/ghost.pdf",
                member_ipns=("IC_GHOST",),
            )
        ]

        result = apply_admit_manifest(
            rows, staging_dir=staging_dir, library_dir=library_dir
        )

        assert result.outcomes[0].status == "skipped"
        assert result.admitted_count == 0
        assert result.refused_count == 0

    def test_path_traversal_proposed_name_is_refused_and_writes_nothing_outside_library(
        self, tmp_path: Path
    ) -> None:
        """A crafted ProposedName in a human-edited manifest must never
        escape the library directory (reviewer-demonstrated live escape on
        PR#373: ``proposed_name="../../evil"``).
        """
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()
        library_dir = tmp_path / "library" / "datasheets"
        library_dir.mkdir(parents=True)
        (staging_dir / "stem-evil.pdf").write_bytes(_PDF_BYTES_A)

        rows = [
            AdmitManifestRow(
                action=ACTION_ADMIT,
                proposed_name="../../evil",
                disposition=DISPOSITION_NEW,
                dupe_of="",
                staged_file="stem-evil.pdf",
                source_url="https://example.com/evil.pdf",
                member_ipns=("IC_EVIL",),
            )
        ]

        result = apply_admit_manifest(
            rows, staging_dir=staging_dir, library_dir=library_dir
        )

        assert result.outcomes[0].status == "refused-invalid-name"
        assert result.refused_count == 1
        assert result.admitted_count == 0
        assert result.paste_rows == []
        # The staged file must still be exactly where it was -- no move, no
        # write anywhere, including outside the library directory tree.
        assert (staging_dir / "stem-evil.pdf").read_bytes() == _PDF_BYTES_A
        assert not (tmp_path / "library" / "evil.pdf").exists()
        assert not (tmp_path / "evil.pdf").exists()
        assert list(library_dir.glob("*.pdf")) == []

    def test_absolute_path_proposed_name_is_refused(self, tmp_path: Path) -> None:
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()
        library_dir = tmp_path / "datasheets"
        outside_target = tmp_path / "outside-target.pdf"
        (staging_dir / "stem-abs.pdf").write_bytes(_PDF_BYTES_A)

        rows = [
            AdmitManifestRow(
                action=ACTION_ADMIT,
                proposed_name=str(outside_target.with_suffix("")),
                disposition=DISPOSITION_NEW,
                dupe_of="",
                staged_file="stem-abs.pdf",
                source_url="https://example.com/abs.pdf",
                member_ipns=("IC_ABS",),
            )
        ]

        result = apply_admit_manifest(
            rows, staging_dir=staging_dir, library_dir=library_dir
        )

        assert result.outcomes[0].status == "refused-invalid-name"
        assert not outside_target.exists()

    def test_unicode_variant_name_is_treated_as_the_same_published_document(
        self, tmp_path: Path
    ) -> None:
        """NFC vs NFD encodings of the same visible name must not bypass
        the case-insensitive uniqueness invariant (jBOM#346)."""
        import unicodedata

        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()
        library_dir = tmp_path / "datasheets"
        library_dir.mkdir()

        nfc_name = unicodedata.normalize("NFC", "Cafe\u0301-Doc")  # "Café-Doc" (NFC)
        nfd_name = unicodedata.normalize("NFD", nfc_name)  # same text, NFD encoding
        assert nfc_name != nfd_name  # sanity: genuinely different byte sequences

        (library_dir / f"{nfc_name}.pdf").write_bytes(_PDF_BYTES_A)
        (staging_dir / "stem-variant.pdf").write_bytes(_PDF_BYTES_B)

        rows = [
            AdmitManifestRow(
                action=ACTION_ADMIT,
                proposed_name=nfd_name,
                disposition=DISPOSITION_NEW,
                dupe_of="",
                staged_file="stem-variant.pdf",
                source_url="https://example.com/variant.pdf",
                member_ipns=("IC_VARIANT",),
            )
        ]

        result = apply_admit_manifest(
            rows, staging_dir=staging_dir, library_dir=library_dir
        )

        # Different content under the "same" (unicode-normalized) name is a
        # never-rename violation, not a fresh admission.
        assert result.outcomes[0].status == "refused-never-rename"

    def test_case_variant_reuse_is_idempotent_without_relying_on_filesystem_case_sensitivity(
        self, tmp_path: Path
    ) -> None:
        """Re-admitting identical content under a different-case spelling of
        an existing published name must be detected via the case-insensitive
        index, not ``Path.exists()`` (which only "works" on filesystems that
        happen to be case-insensitive, e.g. macOS/Windows -- not Linux)."""
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()
        library_dir = tmp_path / "datasheets"
        library_dir.mkdir()
        (library_dir / "Existing-Doc.pdf").write_bytes(_PDF_BYTES_A)
        (staging_dir / "stem-case.pdf").write_bytes(_PDF_BYTES_A)

        rows = [
            AdmitManifestRow(
                action=ACTION_ADMIT,
                proposed_name="existing-doc",  # case-variant spelling
                disposition=DISPOSITION_DUPE_OF,
                dupe_of="Existing-Doc",
                staged_file="stem-case.pdf",
                source_url="https://example.com/case.pdf",
                member_ipns=("IC_CASE",),
            )
        ]

        result = apply_admit_manifest(
            rows, staging_dir=staging_dir, library_dir=library_dir
        )

        assert result.outcomes[0].status == "already-admitted"
        # Exactly one published file exists -- no case-variant duplicate was
        # created, regardless of host filesystem case sensitivity.
        assert [p.name for p in library_dir.glob("*.pdf")] == ["Existing-Doc.pdf"]


class TestApplyAdmitManifestPartialBatch:
    def test_one_refused_row_does_not_block_other_rows_in_the_same_batch(
        self, tmp_path: Path
    ) -> None:
        """Row-by-row commit semantics: rows are independent within one
        ``--apply`` run -- a refusal on one row must not prevent, roll back,
        or otherwise affect any other row in the same manifest."""
        staging_dir = tmp_path / "staging"
        staging_dir.mkdir()
        library_dir = tmp_path / "datasheets"
        library_dir.mkdir()
        (library_dir / "Published-Name.pdf").write_bytes(_PDF_BYTES_A)

        (staging_dir / "stem-good-1.pdf").write_bytes(_PDF_BYTES_A)
        (staging_dir / "stem-bad.pdf").write_bytes(_PDF_BYTES_B)
        (staging_dir / "stem-good-2.pdf").write_bytes(b"%PDF-1.4\n%datasheet C\n%%EOF")

        rows = [
            AdmitManifestRow(
                action=ACTION_ADMIT,
                proposed_name="IC-First-Doc",
                disposition=DISPOSITION_NEW,
                dupe_of="",
                staged_file="stem-good-1.pdf",
                source_url="https://example.com/first.pdf",
                member_ipns=("IC_FIRST",),
            ),
            AdmitManifestRow(
                action=ACTION_ADMIT,
                # Collides with a published doc of different content --
                # must be refused without affecting the other two rows.
                proposed_name="Published-Name",
                disposition=DISPOSITION_COLLISION,
                dupe_of="",
                staged_file="stem-bad.pdf",
                source_url="https://example.com/bad.pdf",
                member_ipns=("IC_BAD",),
            ),
            AdmitManifestRow(
                action=ACTION_ADMIT,
                proposed_name="IC-Third-Doc",
                disposition=DISPOSITION_NEW,
                dupe_of="",
                staged_file="stem-good-2.pdf",
                source_url="https://example.com/third.pdf",
                member_ipns=("IC_THIRD",),
            ),
        ]

        result = apply_admit_manifest(
            rows, staging_dir=staging_dir, library_dir=library_dir
        )

        assert result.admitted_count == 2
        assert result.refused_count == 1
        assert (library_dir / "IC-First-Doc.pdf").is_file()
        assert (library_dir / "IC-Third-Doc.pdf").is_file()
        # The refused row's staged file is untouched and never landed under
        # the colliding published name.
        assert (staging_dir / "stem-bad.pdf").read_bytes() == _PDF_BYTES_B
        assert (library_dir / "Published-Name.pdf").read_bytes() == _PDF_BYTES_A
        assert set(result.paste_rows) == {
            ("IC_FIRST", "IC-First-Doc"),
            ("IC_THIRD", "IC-Third-Doc"),
        }


class TestWritePasteFile:
    def test_writes_ipn_and_datasheet_name_columns(self) -> None:
        buf = io.StringIO()
        write_paste_file([("RES_331", "Resistor-Uniroyal-0603WAJ-series")], buf)
        content = buf.getvalue()
        assert "IPN" in content and "Datasheet Name" in content
        assert "RES_331" in content
        assert "Resistor-Uniroyal-0603WAJ-series" in content

    def test_empty_paste_rows_writes_header_only(self) -> None:
        buf = io.StringIO()
        write_paste_file([], buf)
        lines = [line for line in buf.getvalue().splitlines() if line.strip()]
        assert len(lines) == 1
