"""Unit tests for multi-project batch inventory logic.

Tests exercise _handle_batch_inventory, _merge_field_names, and _print_batch_summary
using mocked component loading so no real KiCad files are required.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

from jbom.cli.inventory import (
    _handle_batch_inventory,
    _merge_field_names,
    _print_batch_summary,
    handle_inventory,
)
from jbom.common.types import Component, InventoryItem, DEFAULT_PRIORITY


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_args(**kwargs) -> argparse.Namespace:
    """Build a minimal args Namespace for inventory tests."""
    defaults = {
        "output": None,
        "force": False,
        "verbose": False,
        "stop_on_error": False,
        "inventory_files": None,
        "filter_matches": False,
        "per_instance": False,
        "input": None,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _make_component(
    reference: str = "R1",
    value: str = "10K",
    footprint: str = "R_0603_1608Metric",
    lib_id: str = "Device:R",
) -> Component:
    return Component(
        reference=reference,
        lib_id=lib_id,
        value=value,
        footprint=footprint,
        uuid=f"uuid-{reference}",
        properties={},
        in_bom=True,
        exclude_from_sim=False,
        dnp=False,
    )


def _make_item(component_id: str, value: str = "10K") -> InventoryItem:
    """Build a minimal InventoryItem with the given ComponentID."""
    return InventoryItem(
        ipn="",
        keywords="",
        category="RES",
        description=f"Resistor {value}",
        smd="",
        value=value,
        type="",
        tolerance="",
        voltage="",
        amperage="",
        wattage="",
        lcsc="",
        manufacturer="",
        mfgpn="",
        datasheet="",
        row_type="COMPONENT",
        component_id=component_id,
        priority=DEFAULT_PRIORITY,
    )


def _make_load_result(
    components: list[Component],
    project_name: str = "TestProject",
    project_dir: Path | None = None,
):
    """Return a mock load result tuple."""
    return (components, project_name, project_dir or Path("/tmp/project"))


# ---------------------------------------------------------------------------
# _merge_field_names
# ---------------------------------------------------------------------------


class TestMergeFieldNames:
    def test_canonical_fields_come_first(self):
        fields = {"UUID", "ComponentID", "Value", "RowType", "IPN", "ExtraField"}
        ordered = _merge_field_names(fields)
        # Canonical fields should appear before ExtraField
        assert ordered.index("RowType") < ordered.index("ExtraField")
        assert ordered.index("ComponentID") < ordered.index("ExtraField")
        assert ordered.index("IPN") < ordered.index("ExtraField")

    def test_extra_fields_appended_alphabetically(self):
        fields = {"ComponentID", "Zebra", "Alpha", "Beta"}
        ordered = _merge_field_names(fields)
        extra = [f for f in ordered if f not in {"ComponentID"}]
        assert extra == sorted(extra), "Extra fields should be alphabetically sorted"

    def test_only_present_canonical_fields_included(self):
        fields = {"ComponentID", "Value"}
        ordered = _merge_field_names(fields)
        assert "UUID" not in ordered  # not in input set
        assert "ComponentID" in ordered
        assert "Value" in ordered

    def test_empty_input(self):
        assert _merge_field_names(set()) == []


# ---------------------------------------------------------------------------
# _print_batch_summary
# ---------------------------------------------------------------------------


class TestPrintBatchSummary:
    def test_ok_and_fail_lines(self, capsys):
        results = [
            ("/proj/A", True, "10 items (8 unique added)"),
            ("/proj/B", False, "failed to load components"),
        ]
        _print_batch_summary(results)
        out = capsys.readouterr().err
        assert "[OK ]" in out
        assert "[FAIL]" in out
        assert "/proj/A" in out
        assert "/proj/B" in out

    def test_all_success(self, capsys):
        results = [("/proj/A", True, "5 items (5 unique added)")]
        _print_batch_summary(results)
        out = capsys.readouterr().err
        assert "[FAIL]" not in out
        assert "[OK ]" in out


# ---------------------------------------------------------------------------
# _handle_batch_inventory — deduplication
# ---------------------------------------------------------------------------


class TestBatchInventoryDeduplication:
    """ComponentID deduplication: first-seen across projects wins."""

    def _item_a(self):
        return _make_item("RES-10K-0603", value="10K")

    def _item_b(self):
        """Same ComponentID as _item_a — should be deduplicated."""
        item = _make_item("RES-10K-0603", value="10K")
        return item

    def _item_unique(self):
        return _make_item("CAP-100nF-0603", value="100nF")

    @patch("jbom.cli.inventory._load_components_from_path")
    @patch("jbom.cli.inventory.ProjectInventoryGenerator")
    @patch("jbom.cli.inventory._output_inventory")
    def test_duplicate_component_ids_deduplicated(
        self, mock_output, mock_gen_cls, mock_load
    ):
        """Item with same ComponentID from two projects appears only once."""
        comp = _make_component()
        mock_load.return_value = _make_load_result([comp], "ProjA")

        # Both projects return an item with the same component_id
        item_a = self._item_a()
        item_b = self._item_b()
        mock_gen_instance = MagicMock()
        mock_gen_instance.load.side_effect = [
            ([item_a], ["ComponentID", "Value"]),
            ([item_b], ["ComponentID", "Value"]),
        ]
        mock_gen_cls.return_value = mock_gen_instance
        mock_output.return_value = 0

        args = _make_args()
        result = _handle_batch_inventory(["projA", "projB"], args)

        assert result == 0
        # _output_inventory called once with deduplicated items
        call_args = mock_output.call_args
        items_passed = call_args[0][0]
        component_ids = [i.component_id for i in items_passed]
        assert (
            component_ids.count("RES-10K-0603") == 1
        ), "Duplicate ComponentID should appear only once"

    @patch("jbom.cli.inventory._load_components_from_path")
    @patch("jbom.cli.inventory.ProjectInventoryGenerator")
    @patch("jbom.cli.inventory._output_inventory")
    def test_unique_component_ids_all_included(
        self, mock_output, mock_gen_cls, mock_load
    ):
        """Items with different ComponentIDs from two projects are both included."""
        comp = _make_component()
        mock_load.return_value = _make_load_result([comp])

        item_a = self._item_a()
        item_unique = self._item_unique()
        mock_gen_instance = MagicMock()
        mock_gen_instance.load.side_effect = [
            ([item_a], ["ComponentID", "Value"]),
            ([item_unique], ["ComponentID", "Value"]),
        ]
        mock_gen_cls.return_value = mock_gen_instance
        mock_output.return_value = 0

        args = _make_args()
        _handle_batch_inventory(["projA", "projB"], args)

        items_passed = mock_output.call_args[0][0]
        ids = {i.component_id for i in items_passed}
        assert "RES-10K-0603" in ids
        assert "CAP-100nF-0603" in ids

    @patch("jbom.cli.inventory._load_components_from_path")
    @patch("jbom.cli.inventory.ProjectInventoryGenerator")
    @patch("jbom.cli.inventory._output_inventory")
    def test_first_seen_wins(self, mock_output, mock_gen_cls, mock_load):
        """When ComponentID is shared, first project's item data is kept."""
        comp = _make_component()
        mock_load.return_value = _make_load_result([comp])

        item_first = _make_item("RES-10K-0603", value="10K-first")
        item_second = _make_item("RES-10K-0603", value="10K-second")

        mock_gen_instance = MagicMock()
        mock_gen_instance.load.side_effect = [
            ([item_first], ["ComponentID", "Value"]),
            ([item_second], ["ComponentID", "Value"]),
        ]
        mock_gen_cls.return_value = mock_gen_instance
        mock_output.return_value = 0

        args = _make_args()
        _handle_batch_inventory(["projA", "projB"], args)

        items_passed = mock_output.call_args[0][0]
        kept = next(i for i in items_passed if i.component_id == "RES-10K-0603")
        assert kept.value == "10K-first", "First-seen item should be kept"

    @patch("jbom.cli.inventory._load_components_from_path")
    @patch("jbom.cli.inventory.ProjectInventoryGenerator")
    @patch("jbom.cli.inventory._output_inventory")
    def test_items_without_component_id_always_included(
        self, mock_output, mock_gen_cls, mock_load
    ):
        """Items with empty ComponentID are never deduplicated — always included."""
        comp = _make_component()
        mock_load.return_value = _make_load_result([comp])

        item_no_id_1 = _make_item("", value="unknown-1")
        item_no_id_2 = _make_item("", value="unknown-2")

        mock_gen_instance = MagicMock()
        mock_gen_instance.load.side_effect = [
            ([item_no_id_1], ["ComponentID", "Value"]),
            ([item_no_id_2], ["ComponentID", "Value"]),
        ]
        mock_gen_cls.return_value = mock_gen_instance
        mock_output.return_value = 0

        args = _make_args()
        _handle_batch_inventory(["projA", "projB"], args)

        items_passed = mock_output.call_args[0][0]
        assert (
            len(items_passed) == 2
        ), "Both items without ComponentID should be included"


# ---------------------------------------------------------------------------
# _handle_batch_inventory — field union
# ---------------------------------------------------------------------------


class TestBatchInventoryFieldUnion:
    @patch("jbom.cli.inventory._load_components_from_path")
    @patch("jbom.cli.inventory.ProjectInventoryGenerator")
    @patch("jbom.cli.inventory._output_inventory")
    def test_field_names_unioned_across_projects(
        self, mock_output, mock_gen_cls, mock_load
    ):
        """Field names from all projects are unioned in the output."""
        comp = _make_component()
        mock_load.return_value = _make_load_result([comp])

        mock_gen_instance = MagicMock()
        mock_gen_instance.load.side_effect = [
            ([_make_item("A")], ["ComponentID", "Value", "Resistance"]),
            ([_make_item("B")], ["ComponentID", "Value", "Capacitance"]),
        ]
        mock_gen_cls.return_value = mock_gen_instance
        mock_output.return_value = 0

        args = _make_args()
        _handle_batch_inventory(["projA", "projB"], args)

        fields_passed = mock_output.call_args[0][1]
        assert "Resistance" in fields_passed
        assert "Capacitance" in fields_passed
        assert "ComponentID" in fields_passed


# ---------------------------------------------------------------------------
# _handle_batch_inventory — error handling
# ---------------------------------------------------------------------------


class TestBatchInventoryErrorHandling:
    @patch("jbom.cli.inventory._load_components_from_path")
    @patch("jbom.cli.inventory.ProjectInventoryGenerator")
    @patch("jbom.cli.inventory._output_inventory")
    def test_failed_project_skipped_by_default(
        self, mock_output, mock_gen_cls, mock_load
    ):
        """By default, a failed project is skipped and others continue."""
        comp = _make_component()

        # First project fails, second succeeds
        mock_load.side_effect = [None, _make_load_result([comp], "ProjB")]

        mock_gen_instance = MagicMock()
        mock_gen_instance.load.return_value = ([_make_item("X")], ["ComponentID"])
        mock_gen_cls.return_value = mock_gen_instance
        mock_output.return_value = 0

        args = _make_args()
        result = _handle_batch_inventory(["projA", "projB"], args)

        assert result == 0, "Should succeed when at least one project produces output"
        assert (
            mock_output.called
        ), "Output should be written from the successful project"

    @patch("jbom.cli.inventory._load_components_from_path")
    def test_stop_on_error_aborts_on_first_failure(self, mock_load):
        """--stop-on-error causes immediate abort after first project failure."""
        mock_load.return_value = None  # All projects fail

        args = _make_args(stop_on_error=True)
        result = _handle_batch_inventory(["projA", "projB"], args)

        assert result == 1
        # Should have only tried the first project
        assert mock_load.call_count == 1

    @patch("jbom.cli.inventory._load_components_from_path")
    def test_all_projects_fail_returns_error(self, mock_load):
        """Returns error code when all projects fail."""
        mock_load.return_value = None

        args = _make_args()
        result = _handle_batch_inventory(["projA", "projB"], args)

        assert result == 1


# ---------------------------------------------------------------------------
# handle_inventory — argument routing
# ---------------------------------------------------------------------------


class TestHandleInventoryRouting:
    """Verify that handle_inventory routes to batch vs single correctly."""

    @patch("jbom.cli.inventory._handle_batch_inventory")
    @patch("jbom.cli.inventory._handle_generate_inventory")
    def test_single_input_uses_single_path(self, mock_single, mock_batch):
        """One input → single-project handler."""
        mock_single.return_value = 0
        args = _make_args(input=["myproject"])
        handle_inventory(args)
        mock_single.assert_called_once_with("myproject", args)
        mock_batch.assert_not_called()

    @patch("jbom.cli.inventory._handle_batch_inventory")
    @patch("jbom.cli.inventory._handle_generate_inventory")
    def test_empty_input_defaults_to_current_dir(self, mock_single, mock_batch):
        """No input → defaults to current directory, single-project path."""
        mock_single.return_value = 0
        args = _make_args(input=[])
        handle_inventory(args)
        mock_single.assert_called_once_with(".", args)
        mock_batch.assert_not_called()

    @patch("jbom.cli.inventory._handle_batch_inventory")
    @patch("jbom.cli.inventory._handle_generate_inventory")
    def test_none_input_defaults_to_current_dir(self, mock_single, mock_batch):
        """None input (argparse default) → defaults to current directory."""
        mock_single.return_value = 0
        args = _make_args(input=None)
        handle_inventory(args)
        mock_single.assert_called_once_with(".", args)
        mock_batch.assert_not_called()

    @patch("jbom.cli.inventory._handle_batch_inventory")
    @patch("jbom.cli.inventory._handle_generate_inventory")
    def test_multiple_inputs_uses_batch_path(self, mock_single, mock_batch):
        """Multiple inputs → batch handler."""
        mock_batch.return_value = 0
        args = _make_args(input=["projA", "projB", "projC"])
        handle_inventory(args)
        mock_batch.assert_called_once_with(["projA", "projB", "projC"], args)
        mock_single.assert_not_called()
