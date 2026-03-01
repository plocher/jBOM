"""Unit tests for Issue #90: InventoryItem typed parametric fields.

Tests cover:
- InventoryItem has new typed fields with correct defaults
- Inventory reader decodes Resistance/Capacitance/Inductance columns at intake
- Value-column fallback when explicit typed column is absent
- Warning logged when explicit column and Value disagree numerically
- build_query() uses typed float fields for passives (formatted as EIA strings)
- build_query() uses Name field for non-passive components
"""
from __future__ import annotations

import logging
import os
import sys
import tempfile
import textwrap
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from jbom.common.types import InventoryItem  # noqa: E402
from jbom.services.inventory_reader import InventoryReader  # noqa: E402
from jbom.services.search.inventory_search_service import (
    InventorySearchService,
)  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_inventory_item(**kwargs) -> InventoryItem:
    """Return a minimal InventoryItem with sane defaults."""
    defaults = dict(
        ipn="TEST_001",
        keywords="",
        category="RES",
        description="",
        smd="SMD",
        value="10K",
        type="",
        tolerance="1%",
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


def _make_search_service() -> InventorySearchService:
    """Return a service with a no-op mock provider."""
    provider = MagicMock()
    provider.provider_id = "mouser"
    provider.search.return_value = []
    return InventorySearchService(provider)


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


class TestInventoryItemTypedFieldDefaults:
    def test_resistance_defaults_to_none(self):
        item = _make_inventory_item()
        assert item.resistance is None

    def test_capacitance_defaults_to_none(self):
        item = _make_inventory_item(category="CAP", value="100nF")
        assert item.capacitance is None

    def test_inductance_defaults_to_none(self):
        item = _make_inventory_item(category="IND", value="10uH")
        assert item.inductance is None

    def test_name_defaults_to_empty_string(self):
        item = _make_inventory_item()
        assert item.name == ""

    def test_explicit_typed_fields_accepted(self):
        item = _make_inventory_item(resistance=10_000.0, name="MyPart")
        assert item.resistance == pytest.approx(10_000.0)
        assert item.name == "MyPart"


# ---------------------------------------------------------------------------
# Inventory reader: decode from explicit typed column
# ---------------------------------------------------------------------------


# Shared CSV header matching the current inventory column layout.
_INV_HEADER = (
    "IPN,ComponentName,Keywords,Category,SMD,Value,Type,Description,"
    "Name,Resistance,Capacitance,Inductance,Package,Tolerance,V,A,W,"
    "Priority,Manufacturer,MPN,Datasheet\n"
)


class TestInventoryReaderTypedColumnDecode:
    """Typed columns (Resistance, Capacitance, Inductance) are decoded at intake."""

    def test_resistance_explicit_column_decoded(self):
        csv = _INV_HEADER + "R1,,10K RES,RES,SMD,10K,,,,10K,,,0603,1%,,,,1,,,,\n"
        items = _csv_reader(csv)
        assert items[0].resistance == pytest.approx(10_000.0)

    def test_capacitance_explicit_column_decoded(self):
        csv = _INV_HEADER + "C1,,CAP,CAP,SMD,100nF,,,,, 100nF,,0603,10%,,,,1,,,,\n"
        items = _csv_reader(csv)
        assert items[0].capacitance == pytest.approx(100e-9)

    def test_inductance_explicit_column_decoded(self):
        csv = _INV_HEADER + "L1,,IND,IND,SMD,10uH,,,,,, 10uH,0603,,,,,1,,,,\n"
        items = _csv_reader(csv)
        assert items[0].inductance == pytest.approx(10e-6)

    def test_name_column_read_for_nonpassive(self):
        csv = _INV_HEADER + "IC1,,IC,IC,SMD,LM358D,,,LM358D,,,,,,,,,1,,,,\n"
        items = _csv_reader(csv)
        assert items[0].name == "LM358D"

    def test_name_column_empty_for_passive(self):
        csv = _INV_HEADER + "R1,,RES,RES,SMD,10K,,,, 10K,,,0603,1%,,,,1,,,,\n"
        items = _csv_reader(csv)
        assert items[0].name == ""


# ---------------------------------------------------------------------------
# Inventory reader: Value-column fallback
# ---------------------------------------------------------------------------


class TestInventoryReaderValueFallback:
    """When explicit typed column is absent, Value column is decoded as fallback."""

    def test_resistance_decoded_from_value_when_column_empty(self):
        # Resistance column is empty; Value="10K"
        csv = _INV_HEADER + "R1,,RES,RES,SMD,10K,,,,,,,0603,1%,,,,1,,,,\n"
        items = _csv_reader(csv)
        assert items[0].resistance == pytest.approx(10_000.0)

    def test_capacitance_decoded_from_value_when_column_empty(self):
        csv = _INV_HEADER + "C1,,CAP,CAP,SMD,100nF,,,,,,,0603,10%,,,,1,,,,\n"
        items = _csv_reader(csv)
        assert items[0].capacitance == pytest.approx(100e-9)

    def test_inductance_decoded_from_value_when_column_empty(self):
        csv = _INV_HEADER + "L1,,IND,IND,SMD,10uH,,,,,,,0603,,,,,1,,,,\n"
        items = _csv_reader(csv)
        assert items[0].inductance == pytest.approx(10e-6)

    def test_nonpassive_leaves_typed_fields_none(self):
        # IC has no parseable Resistance/Capacitance/Inductance
        csv = _INV_HEADER + "IC1,,IC,IC,SMD,LM358D,,,LM358D,,,,,,,,,1,,,,\n"
        items = _csv_reader(csv)
        assert items[0].resistance is None
        assert items[0].capacitance is None
        assert items[0].inductance is None

    def test_unparseable_value_leaves_typed_field_none(self):
        # Value is not a parseable resistance (e.g. "N/A")
        csv = _INV_HEADER + "R1,,RES,RES,SMD,N/A,,,,,,,0603,,,,,1,,,,\n"
        items = _csv_reader(csv)
        assert items[0].resistance is None


# ---------------------------------------------------------------------------
# Inventory reader: disagreement warning
# ---------------------------------------------------------------------------


class TestInventoryReaderDisagreementWarning:
    """A WARNING is logged when explicit typed column and Value parse to different values."""

    def test_warning_when_resistance_and_value_disagree(self, caplog):
        # Resistance column says 10K but Value says 1K — clear disagreement
        csv = _INV_HEADER + "R1,,RES,RES,SMD,1K,,,, 10K,,,0603,1%,,,,1,,,,\n"
        with caplog.at_level(logging.WARNING, logger="jbom.services.inventory_reader"):
            items = _csv_reader(csv)
        assert items[0].resistance == pytest.approx(10_000.0)  # explicit column wins
        assert any(
            "conflict" in r.message.lower() or "disagree" in r.message.lower()
            for r in caplog.records
        )

    def test_no_warning_when_both_agree(self, caplog):
        csv = _INV_HEADER + "R1,,RES,RES,SMD,10K,,,, 10K,,,0603,1%,,,,1,,,,\n"
        with caplog.at_level(logging.WARNING, logger="jbom.services.inventory_reader"):
            items = _csv_reader(csv)
        assert items[0].resistance == pytest.approx(10_000.0)
        assert not any(
            "conflict" in r.message.lower() or "disagree" in r.message.lower()
            for r in caplog.records
        )

    def test_no_warning_when_only_value_present(self, caplog):
        csv = _INV_HEADER + "R1,,RES,RES,SMD,10K,,,,,,,0603,1%,,,,1,,,,\n"
        with caplog.at_level(logging.WARNING, logger="jbom.services.inventory_reader"):
            _csv_reader(csv)
        assert not any(
            "conflict" in r.message.lower() or "disagree" in r.message.lower()
            for r in caplog.records
        )


# ---------------------------------------------------------------------------
# build_query: typed fields for passives
# ---------------------------------------------------------------------------


class TestBuildQueryTypedFields:
    """build_query() uses typed float fields for passives, formatted back to EIA."""

    def _svc(self) -> InventorySearchService:
        return _make_search_service()

    def test_resistor_uses_resistance_field(self):
        svc = self._svc()
        item = _make_inventory_item(category="RES", value="10K", resistance=10_000.0)
        query = svc.build_query(item)
        assert "10K" in query

    def test_resistor_normalizes_value_via_typed_field(self):
        # value="200" (no unit suffix), resistance=200.0 → should format as "200R"
        svc = self._svc()
        item = _make_inventory_item(category="RES", value="200", resistance=200.0)
        query = svc.build_query(item)
        assert "200R" in query

    def test_capacitor_uses_capacitance_field(self):
        svc = self._svc()
        item = _make_inventory_item(
            category="CAP", value="0.01uF", capacitance=10e-9, tolerance="10%"
        )
        query = svc.build_query(item)
        # 10nF is the normalized form of 0.01uF
        assert "10nF" in query

    def test_inductor_uses_inductance_field(self):
        svc = self._svc()
        item = _make_inventory_item(category="IND", value="10uH", inductance=10e-6)
        query = svc.build_query(item)
        assert "10uH" in query

    def test_resistor_falls_back_to_value_when_resistance_none(self):
        svc = self._svc()
        item = _make_inventory_item(category="RES", value="10K", resistance=None)
        query = svc.build_query(item)
        assert "10K" in query

    def test_capacitor_falls_back_to_value_when_capacitance_none(self):
        svc = self._svc()
        item = _make_inventory_item(category="CAP", value="100nF", capacitance=None)
        query = svc.build_query(item)
        assert "100nF" in query


# ---------------------------------------------------------------------------
# build_query: Name field for non-passives
# ---------------------------------------------------------------------------


class TestBuildQueryNameField:
    """build_query() prefers item.name over item.value for non-passive components."""

    def _svc(self) -> InventorySearchService:
        return _make_search_service()

    def test_ic_uses_name_field_when_set(self):
        svc = self._svc()
        item = _make_inventory_item(category="IC", value="LM358D", name="LM358D")
        query = svc.build_query(item)
        assert "LM358D" in query

    def test_reg_prefers_name_over_value_when_name_set(self):
        svc = self._svc()
        item = _make_inventory_item(category="REG", value="3.3V", name="AMS1117-3.3")
        query = svc.build_query(item)
        assert "AMS1117-3.3" in query

    def test_nonpassive_falls_back_to_value_when_name_empty(self):
        svc = self._svc()
        item = _make_inventory_item(category="IC", value="NE555", name="")
        query = svc.build_query(item)
        assert "NE555" in query

    def test_name_not_used_for_passives(self):
        """Even if name is populated, passives use typed fields / value."""
        svc = self._svc()
        # Hypothetical: name accidentally set on a resistor — should be ignored
        item = _make_inventory_item(
            category="RES", value="10K", resistance=10_000.0, name="SomeResistor"
        )
        query = svc.build_query(item)
        assert "SomeResistor" not in query
        assert "10K" in query
