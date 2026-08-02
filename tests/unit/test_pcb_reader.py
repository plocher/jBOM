"""Unit tests for PCB reader attribute extraction behavior."""

from __future__ import annotations

import pytest

from sexpdata import Symbol

from jbom.common.types import TitleBlockMetadata
from jbom.services.pcb_reader import DefaultKiCadReaderService


def _footprint_node(
    attr_tokens: list[str],
    *,
    locked: bool = False,
) -> list[object]:
    """Build a minimal footprint S-expression node for parser unit tests."""

    node: list[object] = [
        Symbol("footprint"),
        "Resistor_SMD:R_0805_2012Metric",
        [Symbol("layer"), "F.Cu"],
        [Symbol("at"), "10", "20", "90"],
        [Symbol("property"), "Reference", "R1"],
        [Symbol("property"), "Value", "10K"],
    ]
    if attr_tokens:
        node.append([Symbol("attr"), *[Symbol(token) for token in attr_tokens]])
    if locked:
        node.append([Symbol("locked")])
    return node


def test_parse_footprint_node_records_all_attr_tokens_and_locked_flag() -> None:
    """PCB reader should preserve all `attr` tokens, layer, and locked metadata."""

    reader = DefaultKiCadReaderService()
    parsed = reader._parse_footprint_node(
        _footprint_node(
            ["smd", "exclude_from_pos_files", "exclude_from_bom"],
            locked=True,
        )
    )

    assert parsed is not None
    assert parsed.attributes["mount_type"] == "smd"
    assert parsed.attributes["smd"] == "yes"
    assert parsed.attributes["exclude_from_pos_files"] == "yes"
    assert parsed.attributes["exclude_from_bom"] == "yes"
    assert parsed.attributes["locked"] == "yes"
    assert parsed.attributes["layer"] == "F.Cu"


def test_parse_footprint_node_preserves_unknown_attr_tokens() -> None:
    """Unexpected attr tokens should still be recorded for downstream consumers."""

    reader = DefaultKiCadReaderService()
    parsed = reader._parse_footprint_node(_footprint_node(["custom_attr_flag"]))

    assert parsed is not None
    assert parsed.attributes["custom_attr_flag"] == "yes"


def test_parse_footprint_node_preserves_canonical_fpid_over_schematic_footprint_property() -> (
    None
):
    """PCB-first contract: ``footprint_name`` must be the FPID from the
    ``(footprint "Lib:Name" ...)`` opener.  When the footprint block also
    carries a ``(property "Footprint" ...)`` field (which mirrors the
    schematic-side hint and can disagree with the actual PCB FPID), the
    reader must record it under ``attributes['schematic_footprint']`` and
    NOT overwrite ``footprint_name``.  Otherwise the BOM ends up reporting
    a footprint that doesn't match what's physically on the board (the
    LEDStripDriver / cpOD-updated provenance bug).
    """

    reader = DefaultKiCadReaderService()
    node: list[object] = [
        Symbol("footprint"),
        "VendorLib:0805-CAP",  # canonical FPID
        [Symbol("layer"), "F.Cu"],
        [Symbol("at"), "10", "20", "0"],
        [Symbol("property"), "Reference", "C1"],
        [Symbol("property"), "Value", "1uF"],
        # Schematic-side hint that disagrees with the placed FPID.
        [Symbol("property"), "Footprint", "Capacitor_SMD:C_0805_2012Metric"],
    ]

    parsed = reader._parse_footprint_node(node)

    assert parsed is not None
    # The canonical PCB FPID survives unchanged.
    assert parsed.footprint_name == "VendorLib:0805-CAP"
    # The schematic-side hint is preserved alongside it for diagnostics.
    assert parsed.attributes["schematic_footprint"] == "Capacitor_SMD:C_0805_2012Metric"


# ---------------------------------------------------------------------------
# Title-block metadata: COMMENT 1..9 parsing (#332)
# ---------------------------------------------------------------------------


def _pcb_sexp_with_title_block(title_block_items: list[object]) -> list[object]:
    """Build a minimal ``(kicad_pcb ... (title_block ...))`` tree for tests."""
    return [
        Symbol("kicad_pcb"),
        [Symbol("version"), "20240108"],
        [Symbol("title_block"), *title_block_items],
    ]


def _comment(index: int, text: str) -> list[object]:
    return [Symbol("comment"), index, text]


def test_pcb_title_block_extracts_scalar_fields() -> None:
    """Existing scalar fields keep working alongside the new comments map."""
    reader = DefaultKiCadReaderService()
    sexp = _pcb_sexp_with_title_block(
        [
            [Symbol("title"), "MyBoard"],
            [Symbol("rev"), "1.0"],
            [Symbol("date"), "2026-05-09"],
            [Symbol("company"), "Acme"],
        ]
    )
    metadata = reader._extract_title_block_metadata(sexp)
    assert metadata.title == "MyBoard"
    assert metadata.revision == "1.0"
    assert metadata.date == "2026-05-09"
    assert metadata.company == "Acme"
    assert dict(metadata.comments) == {}


def test_pcb_title_block_populates_all_nine_comments() -> None:
    """COMMENT 1..9 each surface verbatim under :attr:`comments`."""
    reader = DefaultKiCadReaderService()
    sexp = _pcb_sexp_with_title_block(
        [_comment(n, f"pcb-comment-{n}") for n in range(1, 10)]
    )
    metadata = reader._extract_title_block_metadata(sexp)
    assert isinstance(metadata, TitleBlockMetadata)
    for n in range(1, 10):
        assert metadata.comments[n] == f"pcb-comment-{n}"


def test_pcb_title_block_missing_comments_are_absent() -> None:
    """A title block without any comments yields an empty comments map."""
    reader = DefaultKiCadReaderService()
    sexp = _pcb_sexp_with_title_block([[Symbol("title"), "MyBoard"]])
    metadata = reader._extract_title_block_metadata(sexp)
    assert dict(metadata.comments) == {}


def test_pcb_title_block_empty_comment_value_preserved() -> None:
    """``(comment 2 "")`` keeps the key with an empty-string value."""
    reader = DefaultKiCadReaderService()
    sexp = _pcb_sexp_with_title_block([_comment(2, "")])
    metadata = reader._extract_title_block_metadata(sexp)
    assert 2 in metadata.comments
    assert metadata.comments[2] == ""


def test_pcb_title_block_mixed_presence_preserved() -> None:
    """Mixed-presence layouts keep the populated indices verbatim and omit the rest."""
    reader = DefaultKiCadReaderService()
    sexp = _pcb_sexp_with_title_block(
        [
            _comment(1, "designer"),
            _comment(9, "released"),
        ]
    )
    metadata = reader._extract_title_block_metadata(sexp)
    assert metadata.comments == {1: "designer", 9: "released"}


def test_pcb_title_block_preserves_raw_comment_strings() -> None:
    """Raw values are stored verbatim, including whitespace."""
    reader = DefaultKiCadReaderService()
    raw = "  spaced  with\ttabs  "
    sexp = _pcb_sexp_with_title_block([_comment(3, raw)])
    metadata = reader._extract_title_block_metadata(sexp)
    assert metadata.comments[3] == raw


def test_parse_footprint_node_captures_pads() -> None:
    """Pad nodes should populate footprint-local pad list."""
    from sexpdata import Symbol

    reader = DefaultKiCadReaderService()
    node: list[object] = [
        Symbol("footprint"),
        "Conn:HDR",
        [Symbol("layer"), "F.Cu"],
        [Symbol("at"), "10", "20", "90"],
        [Symbol("property"), "Reference", "J1"],
        [Symbol("property"), "Value", "HDR"],
        [Symbol("attr"), Symbol("through_hole")],
        [
            Symbol("pad"),
            "1",
            Symbol("thru_hole"),
            Symbol("circle"),
            [Symbol("at"), "0", "0"],
            [Symbol("size"), "1.5", "1.5"],
        ],
        [
            Symbol("pad"),
            "2",
            Symbol("thru_hole"),
            Symbol("circle"),
            [Symbol("at"), "2.54", "0", "180"],
            [Symbol("size"), "1.5", "1.5"],
        ],
    ]
    parsed = reader._parse_footprint_node(node)
    assert parsed is not None
    assert len(parsed.pads) == 2
    assert parsed.pads[0].x_mm == pytest.approx(0.0)
    assert parsed.pads[1].x_mm == pytest.approx(2.54)
    assert parsed.pads[1].rotation_deg == pytest.approx(180.0)


def test_extract_setup_origins_aux_and_grid() -> None:
    """Board setup should populate aux_origin_mm and grid_origin_mm."""
    from pathlib import Path

    from jbom.common.pcb_types import BoardModel
    from sexpdata import Symbol

    reader = DefaultKiCadReaderService()
    board = BoardModel(path=Path("t.kicad_pcb"))
    setup = [
        Symbol("setup"),
        [Symbol("grid_origin"), 127, 127.1],
        [Symbol("aux_axis_origin"), 10.5, 20.25],
    ]
    reader._extract_setup_origins(setup, board)
    assert board.aux_origin_mm == pytest.approx((10.5, 20.25))
    assert board.grid_origin_mm == pytest.approx((127.0, 127.1))
