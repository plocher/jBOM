"""Unit tests for :class:`jbom.common.types.TitleBlockMetadata`.

These tests pin down the per-file comment behaviour added in #332:

* ``comments`` is a ``Mapping[int, str]`` keyed by the KiCad comment
  index (1..9).
* The map is built so that *missing* comments are absent from the map
  (consumers see ``meta.comments.get(N)`` → ``None``), while *empty*
  comments are present with an empty-string value.  The distinction is
  load-bearing for downstream tooling that wants to tell "no field" from
  "field deliberately blanked".
* The dataclass remains frozen / immutable.
"""

from __future__ import annotations

import pytest

from jbom.common.types import TitleBlockMetadata


class TestTitleBlockMetadataDefaults:
    """Defaults preserve the existing public API."""

    def test_default_construction_has_empty_comments(self) -> None:
        meta = TitleBlockMetadata()
        assert meta.title == ""
        assert meta.revision == ""
        assert meta.date == ""
        assert meta.company == ""
        assert dict(meta.comments) == {}

    def test_dataclass_is_frozen(self) -> None:
        meta = TitleBlockMetadata()
        with pytest.raises(AttributeError):
            meta.title = "changed"  # type: ignore[misc]


class TestTitleBlockMetadataComments:
    """``comments`` is keyed by int and preserves raw values verbatim."""

    def test_comments_populated_for_all_nine_indices(self) -> None:
        comments = {n: f"c{n}" for n in range(1, 10)}
        meta = TitleBlockMetadata(comments=comments)
        for n in range(1, 10):
            assert meta.comments[n] == f"c{n}"

    def test_missing_comment_indices_are_absent_from_map(self) -> None:
        meta = TitleBlockMetadata(comments={1: "designer", 9: "released"})
        assert meta.comments.get(1) == "designer"
        assert meta.comments.get(9) == "released"
        # The missing indices are absent (not empty-string).
        for n in (2, 3, 4, 5, 6, 7, 8):
            assert n not in meta.comments

    def test_empty_string_comment_is_present_and_empty(self) -> None:
        meta = TitleBlockMetadata(comments={2: ""})
        assert 2 in meta.comments
        assert meta.comments[2] == ""

    def test_raw_string_content_is_preserved_verbatim(self) -> None:
        raw = "  spaced  with\ttabs\nand newlines  "
        meta = TitleBlockMetadata(comments={3: raw})
        assert meta.comments[3] == raw
