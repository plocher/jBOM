"""Unit tests for Issue #126: InventoryItem harvest fidelity fields.

Tests cover:
- InventoryItem has footprint_full, symbol_lib, symbol_name, pins, pitch fields with correct defaults
- InventoryReader populates these fields from CSV rows when columns are present
- Absent columns leave fields as empty string (no backward-compat shims)
"""
from __future__ import annotations

import os
import sys
import tempfile
import textwrap
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from jbom.common.types import InventoryItem  # noqa: E402
from jbom.services.inventory_reader import InventoryReader  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_item(**kwargs) -> InventoryItem:
    """Return a minimal InventoryItem with sane defaults."""
    defaults = dict(
        ipn="TEST_001",
        keywords="",
        category="CAP",
        description="",
        smd="SMD",
        value="100nF",
        type="",
        tolerance="",
        voltage="",
        amperage="",
        wattage="",
        lcsc="",
        manufacturer="",
        mfgpn="",
        datasheet="",
    )
    defaults.update(kwargs)
    return InventoryItem(**defaults)


def _csv_reader(csv_text: str) -> list:
    """Load inventory items from in-memory CSV text via a temp file."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        f.write(textwrap.dedent(csv_text))
        tmp_path = Path(f.name)
    reader = InventoryReader(tmp_path)
    items, _ = reader.load()
    os.unlink(tmp_path)
    return items


# ---------------------------------------------------------------------------
# InventoryItem field defaults
# ---------------------------------------------------------------------------


class TestInventoryItemHarvestFidelityDefaults:
    """New fields default to empty string; explicit values are stored."""

    def test_footprint_full_defaults_to_empty_string(self):
        item = _make_item()
        assert item.footprint_full == ""

    def test_symbol_lib_defaults_to_empty_string(self):
        item = _make_item()
        assert item.symbol_lib == ""

    def test_symbol_name_defaults_to_empty_string(self):
        item = _make_item()
        assert item.symbol_name == ""

    def test_pins_defaults_to_empty_string(self):
        item = _make_item()
        assert item.pins == ""

    def test_pitch_defaults_to_empty_string(self):
        item = _make_item()
        assert item.pitch == ""

    def test_aliases_defaults_to_empty_string(self):
        item = _make_item()
        assert item.aliases == ""

    def test_dnp_defaults_to_false(self):
        item = _make_item()
        assert item.dnp is False

    def test_explicit_fields_accepted(self):
        item = _make_item(
            footprint_full="Capacitor_SMD:CP_Elec_4x5.4mm",
            symbol_lib="Device",
            symbol_name="C_Polarized",
            pins="4",
            pitch="2.54mm",
            aliases="ALT1 ALT2",
            dnp=True,
        )
        assert item.footprint_full == "Capacitor_SMD:CP_Elec_4x5.4mm"
        assert item.symbol_lib == "Device"
        assert item.symbol_name == "C_Polarized"
        assert item.pins == "4"
        assert item.pitch == "2.54mm"
        assert item.aliases == "ALT1 ALT2"
        assert item.dnp is True


# ---------------------------------------------------------------------------
# InventoryReader CSV round-trip
# ---------------------------------------------------------------------------

_INV_HEADER = (
    "IPN,Category,Value,Package,footprint_full,symbol_lib,symbol_name,Pins,Pitch\n"
)

_CAP_ROW = (
    "CAP-001,CAP,100nF,0603," "Capacitor_SMD:CP_Elec_4x5.4mm,Device,C_Polarized,,\n"
)
_CON_ROW = (
    "CON-001,CON,Conn_01x04,,"
    "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical,"
    "Connector,Conn_01x04_MountingPin,4,2.54mm\n"
)


class TestInventoryReaderHarvestFidelityRoundtrip:
    """footprint_full, symbol_lib, symbol_name, pins, pitch are read from CSV."""

    def test_footprint_full_read_from_csv(self):
        items = _csv_reader(_INV_HEADER + _CAP_ROW)
        assert items[0].footprint_full == "Capacitor_SMD:CP_Elec_4x5.4mm"

    def test_symbol_lib_read_from_csv(self):
        items = _csv_reader(_INV_HEADER + _CAP_ROW)
        assert items[0].symbol_lib == "Device"

    def test_symbol_name_read_from_csv(self):
        items = _csv_reader(_INV_HEADER + _CAP_ROW)
        assert items[0].symbol_name == "C_Polarized"

    def test_pins_read_from_csv(self):
        items = _csv_reader(_INV_HEADER + _CON_ROW)
        assert items[0].pins == "4"

    def test_pitch_read_from_csv(self):
        items = _csv_reader(_INV_HEADER + _CON_ROW)
        assert items[0].pitch == "2.54mm"

    def test_absent_columns_leave_fields_empty(self):
        """CSV without the new columns: all five fields remain empty string."""
        csv = "IPN,Category,Value,Package\nCAP-001,CAP,100nF,0603\n"
        items = _csv_reader(csv)
        assert items[0].footprint_full == ""
        assert items[0].symbol_lib == ""
        assert items[0].symbol_name == ""
        assert items[0].pins == ""
        assert items[0].pitch == ""

    def test_empty_cells_leave_fields_empty(self):
        """Columns present but cells empty: fields remain empty string."""
        csv = _INV_HEADER + "CAP-001,CAP,100nF,0603,,,,,\n"
        items = _csv_reader(csv)
        assert items[0].footprint_full == ""
        assert items[0].symbol_lib == ""
        assert items[0].symbol_name == ""
        assert items[0].pins == ""
        assert items[0].pitch == ""

    def test_alias_columns_populate_manufacturer_and_mfgpn(self):
        """Standard alias headers should populate canonical manufacturer/mfgpn fields."""
        csv = (
            "IPN,Category,Value,Package,Manufacturer_Name,Manufacturer_Part_Number\n"
            "R-001,RES,10K,0603,LITTELFUSE,CPC1709J\n"
        )
        items = _csv_reader(csv)
        assert items[0].manufacturer == "LITTELFUSE"
        assert items[0].mfgpn == "CPC1709J"

    def test_aliases_column_populates_inventory_item_aliases(self):
        csv = "IPN,Category,Value,Package,Aliases\nIC-001,IC,LM358D,SOP-8,LM6132A TLV272CS-13\n"
        items = _csv_reader(csv)
        assert items[0].aliases == "LM6132A TLV272CS-13"

    def test_dnp_column_parses_truthy_markers(self):
        csv = "IPN,Category,Value,Package,DNP\nJ-001,CON,CONN,TH,DNP\n"
        items = _csv_reader(csv)
        assert items[0].dnp is True

    def test_dnp_column_parses_empty_as_false(self):
        csv = "IPN,Category,Value,Package,DNP\nJ-002,CON,CONN,TH,\n"
        items = _csv_reader(csv)
        assert items[0].dnp is False
