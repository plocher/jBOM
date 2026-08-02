"""Unit tests for POS placement origin, Y polarity, and pad-centroid modes."""

from __future__ import annotations

from pathlib import Path

import pytest

from jbom.common.options import PlacementOptions
from jbom.common.pcb_types import BoardModel, PadLocal, PcbComponent
from jbom.services.pos_generator import (
    POSGenerator,
    apply_origin_and_y,
    local_to_board,
    pad_centers_bbox_board,
    resolve_placement_xy,
    rotate_offset,
)


def test_local_to_board_rot90() -> None:
    bx, by = local_to_board(1.0, 2.0, 10.0, 20.0, 90.0)
    assert bx == pytest.approx(12.0)
    assert by == pytest.approx(19.0)


def test_pad_centers_bbox_board_matches_midpoint() -> None:
    pads = (
        PadLocal(0.0, 0.0),
        PadLocal(2.54, 0.0),
        PadLocal(5.08, 0.0),
        PadLocal(7.62, 0.0),
    )
    bx, by = pad_centers_bbox_board(pads, 100.0, 50.0, 180.0)
    # local centre (3.81, 0) at rot 180 → board (100-3.81, 50)
    assert bx == pytest.approx(96.19)
    assert by == pytest.approx(50.0)


def test_apply_origin_and_y_aux_and_down() -> None:
    x, y = apply_origin_and_y(
        15.0,
        25.0,
        origin="aux",
        y_direction="down",
        aux_origin_mm=(5.0, 10.0),
    )
    assert x == pytest.approx(10.0)
    assert y == pytest.approx(-15.0)


def test_apply_origin_aux_missing_is_zero() -> None:
    x, y = apply_origin_and_y(
        15.0,
        25.0,
        origin="aux",
        y_direction="down",
        aux_origin_mm=None,
    )
    assert x == pytest.approx(15.0)
    assert y == pytest.approx(-25.0)


def test_rotate_offset_top_90() -> None:
    ox, oy = rotate_offset(1.0, 0.0, 90.0, side="TOP")
    assert ox == pytest.approx(0.0)
    assert oy == pytest.approx(1.0)


def _comp(
    *,
    ref: str = "J1",
    x: float = 100.0,
    y: float = 50.0,
    rot: float = 180.0,
    mount: str = "through_hole",
    pads: tuple[PadLocal, ...] = (),
    attrs: dict[str, str] | None = None,
) -> PcbComponent:
    attributes = {"mount_type": mount}
    if attrs:
        attributes.update(attrs)
    return PcbComponent(
        reference=ref,
        footprint_name="Lib:Name",
        package_token="NAME",
        center_x_mm=x,
        center_y_mm=y,
        rotation_deg=rot,
        side="TOP",
        attributes=attributes,
        pads=pads,
    )


def test_auto_mode_smd_uses_anchor() -> None:
    pads = (PadLocal(-1.0, 0.0), PadLocal(1.0, 0.0))
    c = _comp(mount="smd", pads=pads)
    bx, by = resolve_placement_xy(c, position_mode="auto")
    assert bx == pytest.approx(100.0)
    assert by == pytest.approx(50.0)


def test_auto_mode_tht_uses_pad_center() -> None:
    pads = (PadLocal(0.0, 0.0), PadLocal(4.0, 0.0))
    c = _comp(mount="through_hole", pads=pads, rot=0.0)
    bx, by = resolve_placement_xy(c, position_mode="auto")
    assert bx == pytest.approx(102.0)
    assert by == pytest.approx(50.0)


def test_origin_property_overrides_auto_to_anchor() -> None:
    pads = (PadLocal(0.0, 0.0), PadLocal(4.0, 0.0))
    c = _comp(
        mount="through_hole",
        pads=pads,
        rot=0.0,
        attrs={"FT Origin": "Anchor"},
    )
    bx, by = resolve_placement_xy(c, position_mode="auto")
    assert bx == pytest.approx(100.0)
    assert by == pytest.approx(50.0)


def test_pos_generator_emits_y_down_with_aux() -> None:
    pads = (PadLocal(0.0, 0.0), PadLocal(2.0, 0.0))
    board = BoardModel(
        path=Path("t.kicad_pcb"),
        aux_origin_mm=(10.0, 5.0),
        footprints=[
            _comp(ref="J1", x=20.0, y=15.0, rot=0.0, mount="through_hole", pads=pads)
        ],
    )
    rows = POSGenerator(
        PlacementOptions(
            origin="aux",
            y_direction="down",
            position_mode="auto",
            smd_only=False,
        )
    ).generate_pos_data(board)
    assert len(rows) == 1
    # pad centre local x=1 → board 21,15; aux → 11,10; y-down → 11,-10
    assert rows[0]["x_mm"] == pytest.approx(11.0)
    assert rows[0]["y_mm"] == pytest.approx(-10.0)
