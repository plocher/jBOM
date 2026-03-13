"""Unit tests for inventory output destination defaults (Issue #176)."""

from __future__ import annotations

from pathlib import Path

from jbom.cli.inventory import _output_inventory, _output_inventory_rows
from jbom.common.types import InventoryItem


def _make_inventory_item() -> InventoryItem:
    """Build a minimal InventoryItem for output-path tests."""
    return InventoryItem(
        ipn="RES-10K-0603",
        keywords="",
        category="RES",
        description="10k resistor",
        smd="",
        value="10K",
        type="",
        tolerance="",
        voltage="",
        amperage="",
        wattage="",
        lcsc="",
        manufacturer="",
        mfgpn="",
        datasheet="",
        row_type="ITEM",
    )


def test_output_inventory_defaults_to_console(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    monkeypatch.chdir(tmp_path)
    item = _make_inventory_item()

    exit_code = _output_inventory(
        [item],
        ["IPN", "Category", "Value"],
        output=None,
        force=False,
        verbose=False,
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Generated inventory" in captured.out
    assert not (tmp_path / "part-inventory.csv").exists()


def test_output_inventory_rows_defaults_to_console(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    monkeypatch.chdir(tmp_path)
    rows = [
        {
            "RowType": "COMPONENT",
            "Project": "/tmp/proj",
            "ComponentID": "RES-10K-0603",
        }
    ]
    field_names = ["RowType", "Project", "ComponentID"]

    exit_code = _output_inventory_rows(
        rows,
        field_names,
        output=None,
        force=False,
        verbose=False,
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Generated inventory" in captured.out
    assert not (tmp_path / "part-inventory.csv").exists()
