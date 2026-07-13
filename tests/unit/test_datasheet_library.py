"""Unit tests for jbom.services.datasheet_library helpers (jBOM#357)."""

from __future__ import annotations

from pathlib import Path

from jbom.common.types import InventoryItem
from jbom.services.datasheet_library import (
    DATASHEET_NAME_COLUMN,
    datasheet_filename,
    extract_name_tokens,
    find_near_collisions,
    get_datasheet_name,
    group_case_insensitive_variants,
    normalize_token,
    resolve_canonical_spellings,
    scan_library_pdfs,
)


def _make_item(*, datasheet_name: str = "", **raw_extra: str) -> InventoryItem:
    raw = dict(raw_extra)
    if datasheet_name:
        raw[DATASHEET_NAME_COLUMN] = datasheet_name
    return InventoryItem(
        ipn="IPN1",
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
        raw_data=raw,
    )


class TestGetDatasheetName:
    def test_returns_stripped_name(self) -> None:
        item = _make_item(datasheet_name="  foo-series  ")
        assert get_datasheet_name(item) == "foo-series"

    def test_returns_empty_when_absent(self) -> None:
        item = _make_item()
        assert get_datasheet_name(item) == ""

    def test_returns_empty_when_raw_data_none(self) -> None:
        item = InventoryItem(
            ipn="X",
            keywords="",
            category="",
            description="",
            smd="",
            value="",
            type="",
            tolerance="",
            voltage="",
            amperage="",
            wattage="",
            raw_data=None,
        )
        assert get_datasheet_name(item) == ""


class TestNormalizeToken:
    def test_strips_punctuation_and_uppercases(self) -> None:
        # Non-ASCII qualifiers (e.g. the CJK aside in "UNI-ROYAL(\u539a\u58f0)") are
        # stripped along with punctuation, so both spellings normalize to the
        # same ASCII token and are recognized as the same manufacturer.
        assert normalize_token("UNI-ROYAL(\u539a\u58f0)") == "UNIROYAL"
        assert normalize_token("Uniroyal") == "UNIROYAL"

    def test_empty_input(self) -> None:
        assert normalize_token("") == ""
        assert normalize_token(None) == ""  # type: ignore[arg-type]


class TestResolveCanonicalSpellings:
    def test_most_frequent_spelling_wins(self) -> None:
        canonical = resolve_canonical_spellings(
            ["Uniroyal", "Uniroyal", "UNI-ROYAL", "Uniroyal"]
        )
        assert canonical[normalize_token("Uniroyal")] == "Uniroyal"

    def test_tie_break_is_first_seen(self) -> None:
        canonical = resolve_canonical_spellings(["Yageo", "YAGEO"])
        assert canonical[normalize_token("Yageo")] == "Yageo"

    def test_ignores_blank_values(self) -> None:
        canonical = resolve_canonical_spellings(["", "  ", "Vishay"])
        assert canonical == {normalize_token("Vishay"): "Vishay"}

    def test_distinct_manufacturers_do_not_collide(self) -> None:
        canonical = resolve_canonical_spellings(["Yageo", "Vishay"])
        assert canonical[normalize_token("Yageo")] == "Yageo"
        assert canonical[normalize_token("Vishay")] == "Vishay"


class TestFindNearCollisions:
    def test_flags_similar_long_names(self) -> None:
        pairs = find_near_collisions(
            [
                "Resistor-ThickFilm-Uniroyal-0603WAJ",
                "Resistor-ThickFilm-Univoyal-0603WAJ",
            ]
        )
        assert len(pairs) == 1
        assert pairs[0][2] >= 0.90

    def test_ignores_case_insensitive_duplicates(self) -> None:
        pairs = find_near_collisions(["Foo-Series-Long", "foo-series-long"])
        assert pairs == []

    def test_ignores_short_names(self) -> None:
        pairs = find_near_collisions(["ab", "ac"])
        assert pairs == []

    def test_distinct_names_not_flagged(self) -> None:
        pairs = find_near_collisions(
            ["Resistor-ThickFilm-Uniroyal-0603WAJ", "MOSFET-AO4443-PChannel-UMW"]
        )
        assert pairs == []


class TestGroupCaseInsensitiveVariants:
    def test_groups_by_lowercase(self) -> None:
        groups = group_case_insensitive_variants(["Foo-Bar", "foo-bar", "Baz"])
        assert groups["foo-bar"] == {"Foo-Bar", "foo-bar"}
        assert groups["baz"] == {"Baz"}

    def test_skips_empty_names(self) -> None:
        groups = group_case_insensitive_variants(["", "Foo"])
        assert "" not in groups
        assert groups["foo"] == {"Foo"}


class TestExtractNameTokens:
    def test_splits_on_hyphen_and_underscore(self) -> None:
        assert extract_name_tokens("Resistor-ThickFilm-Uniroyal-0603WAJ-series") == [
            "Resistor",
            "ThickFilm",
            "Uniroyal",
            "0603WAJ",
            "series",
        ]

    def test_empty_name(self) -> None:
        assert extract_name_tokens("") == []


class TestDatasheetFilename:
    def test_appends_pdf_extension(self) -> None:
        assert datasheet_filename("foo-series") == "foo-series.pdf"


class TestScanLibraryPdfs:
    def test_returns_stems_sorted(self, tmp_path: Path) -> None:
        datasheets = tmp_path / "datasheets"
        datasheets.mkdir()
        (datasheets / "b-series.pdf").write_bytes(b"%PDF-1.4\n")
        (datasheets / "a-series.pdf").write_bytes(b"%PDF-1.4\n")
        (datasheets / "not-a-pdf.txt").write_text("nope")
        assert scan_library_pdfs(tmp_path) == ["a-series", "b-series"]

    def test_missing_datasheets_dir_returns_empty(self, tmp_path: Path) -> None:
        assert scan_library_pdfs(tmp_path) == []
