"""Unit tests for Issue #127: inventory three-state (~) round-trip semantics."""

from __future__ import annotations

import csv
import io
import tempfile
import textwrap
from pathlib import Path

from jbom.cli.inventory import _write_csv
from jbom.services.inventory_reader import InventoryReader

_ROUND_TRIP_FIELD_ORDER = [
    "IPN",
    "Category",
    "Value",
    "Description",
    "Package",
    "Manufacturer",
    "MFGPN",
    "LCSC",
    "Datasheet",
    "UUID",
    "Tolerance",
    "Footprint",
]


def _load_items_from_csv(csv_text: str) -> tuple[list, list[str]]:
    """Load inventory items from a temporary CSV payload."""

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as handle:
        handle.write(textwrap.dedent(csv_text).lstrip())
        temp_path = Path(handle.name)

    try:
        reader = InventoryReader(temp_path)
        return reader.load()
    finally:
        temp_path.unlink(missing_ok=True)


def test_tilde_round_trip_is_preserved_through_reader_and_writer() -> None:
    """`~` should survive inventory reader -> writer round-trip unchanged."""

    items, _ = _load_items_from_csv(
        """
        IPN,Category,Value,Package,Tolerance,Footprint,UUID
        RES_10K,RES,~,~,~,~,uuid-r1
        """
    )

    assert len(items) == 1
    item = items[0]
    assert item.value == "~"
    assert item.package == "~"
    assert item.tolerance == "~"
    assert item.raw_data["Footprint"] == "~"

    out = io.StringIO()
    _write_csv(items, _ROUND_TRIP_FIELD_ORDER, out=out)

    rows = list(csv.DictReader(io.StringIO(out.getvalue())))
    assert len(rows) == 1
    assert rows[0]["Value"] == "~"
    assert rows[0]["Package"] == "~"
    assert rows[0]["Tolerance"] == "~"
    assert rows[0]["Footprint"] == "~"


def test_blank_cells_remain_blank_in_round_trip() -> None:
    """Blank cells remain blank and are not coerced into a sentinel value."""

    items, _ = _load_items_from_csv(
        """
        IPN,Category,Value,Package,Tolerance,Footprint,UUID
        RES_10K,RES,,,,,uuid-r1
        """
    )

    out = io.StringIO()
    _write_csv(items, _ROUND_TRIP_FIELD_ORDER, out=out)
    rows = list(csv.DictReader(io.StringIO(out.getvalue())))

    assert rows[0]["Value"] == ""
    assert rows[0]["Package"] == ""
    assert rows[0]["Tolerance"] == ""
    assert rows[0]["Footprint"] == ""
