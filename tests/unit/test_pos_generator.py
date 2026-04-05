"""Unit tests for POSGenerator filtering and ordering behavior."""

from __future__ import annotations

from pathlib import Path

from jbom.common.options import PlacementOptions
from jbom.common.pcb_types import BoardModel, PcbComponent
from jbom.services.pos_generator import POSGenerator


def _pcb_component(
    reference: str,
    *,
    attributes: dict[str, str] | None = None,
) -> PcbComponent:
    """Build a minimal PCB component for POS generator tests."""

    return PcbComponent(
        reference=reference,
        footprint_name="Resistor_SMD:R_0805_2012Metric",
        package_token="0805",
        center_x_mm=10.0,
        center_y_mm=20.0,
        rotation_deg=0.0,
        side="TOP",
        attributes=attributes or {},
    )


def test_generate_pos_data_excludes_position_file_marked_components() -> None:
    """POS output should omit references marked as excluded from position files."""

    board = BoardModel(
        path=Path("project.kicad_pcb"),
        footprints=[
            _pcb_component("R1", attributes={"mount_type": "smd"}),
            _pcb_component(
                "R2",
                attributes={
                    "mount_type": "smd",
                    "exclude_from_pos_files": "yes",
                },
            ),
            _pcb_component(
                "R3",
                attributes={
                    "mount_type": "smd",
                    "Exclude From Position Files": "Yes",
                },
            ),
        ],
    )

    pos_data = POSGenerator(options=PlacementOptions(smd_only=False)).generate_pos_data(
        board
    )

    assert [row["reference"] for row in pos_data] == ["R1"]


def test_generate_pos_data_sorts_references_in_natural_order() -> None:
    """POS output should use natural reference ordering for deterministic UX."""

    board = BoardModel(
        path=Path("project.kicad_pcb"),
        footprints=[
            _pcb_component("R10", attributes={"mount_type": "smd"}),
            _pcb_component("R2", attributes={"mount_type": "smd"}),
            _pcb_component("R1", attributes={"mount_type": "smd"}),
        ],
    )

    pos_data = POSGenerator(options=PlacementOptions(smd_only=False)).generate_pos_data(
        board
    )

    assert [row["reference"] for row in pos_data] == ["R1", "R2", "R10"]


def test_generate_pos_data_sorts_by_prefix_and_numeric_suffix() -> None:
    """POS output should sort by prefix first, then by natural numeric suffix."""

    board = BoardModel(
        path=Path("project.kicad_pcb"),
        footprints=[
            _pcb_component("J10", attributes={"mount_type": "smd"}),
            _pcb_component("IO1", attributes={"mount_type": "smd"}),
            _pcb_component("GND0", attributes={"mount_type": "smd"}),
            _pcb_component("J1", attributes={"mount_type": "smd"}),
        ],
    )

    pos_data = POSGenerator(options=PlacementOptions(smd_only=False)).generate_pos_data(
        board
    )

    assert [row["reference"] for row in pos_data] == ["GND0", "IO1", "J1", "J10"]
