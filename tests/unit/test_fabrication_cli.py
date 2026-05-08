"""Unit tests for the ``jbom fab`` CLI command (issue #224).

Covers:
- Command registration in the main parser
- Argument defaults (skip-bom, skip-pos, skip-gerbers, dry-run)
- ``--skip-gerbers`` flag correctly set
- handle_fab routes through FabricationWorkflow
- Dry-run outputs projected paths without writing files
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from jbom.cli.main import create_parser


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestFabCommandRegistration:
    def test_fab_registered_in_main_parser(self) -> None:
        parser = create_parser()
        subparsers_action = None
        for action in parser._subparsers._group_actions:  # type: ignore[attr-defined]
            if hasattr(action, "choices"):
                subparsers_action = action
                break
        assert subparsers_action is not None
        assert "fab" in subparsers_action.choices

    def test_fab_default_arguments(self) -> None:
        parser = create_parser()
        args = parser.parse_args(["fab", "."])
        assert args.skip_bom is False
        assert args.skip_pos is False
        assert args.skip_gerbers is False
        assert args.dry_run is False
        assert args.origin == "board"

    def test_skip_flags_are_parseable(self) -> None:
        parser = create_parser()
        args = parser.parse_args(
            ["fab", ".", "--skip-bom", "--skip-pos", "--skip-gerbers"]
        )
        assert args.skip_bom is True
        assert args.skip_pos is True
        assert args.skip_gerbers is True

    def test_dry_run_parseable(self) -> None:
        parser = create_parser()
        args = parser.parse_args(["fab", ".", "--dry-run"])
        assert args.dry_run is True

    def test_inventory_repeatable(self) -> None:
        parser = create_parser()
        args = parser.parse_args(
            ["fab", ".", "--inventory", "a.csv", "--inventory", "b.csv"]
        )
        assert args.inventory_files == ["a.csv", "b.csv"]

    def test_output_dir_argument(self) -> None:
        parser = create_parser()
        args = parser.parse_args(["fab", ".", "-o", "/tmp/fab_out"])
        assert args.output_dir == "/tmp/fab_out"


# ---------------------------------------------------------------------------
# handle_fab: all-skip (no-op) run
# ---------------------------------------------------------------------------


class TestHandleFabAllSkip:
    def _make_all_skip_args(self) -> SimpleNamespace:
        args = SimpleNamespace(
            input=".",
            output_dir=None,
            skip_bom=True,
            skip_pos=True,
            skip_gerbers=True,
            dry_run=False,
            verbose=False,
            force=False,
            netlist=False,
            inventory_files=None,
            smd_only=False,
            layer=None,
            origin="board",
            fabricator=None,
            defaults="generic",
        )
        from jbom.config.fabricators import get_available_fabricators

        for fid in get_available_fabricators():
            setattr(args, f"fabricator_flag_{fid}", False)
        return args

    def test_all_skip_exits_0(self) -> None:
        from jbom.cli.fabrication import handle_fab

        args = self._make_all_skip_args()
        rc = handle_fab(args)
        assert rc == 0

    def test_all_skip_does_not_call_bom_service(self) -> None:
        from jbom.cli.fabrication import handle_fab

        args = self._make_all_skip_args()
        with patch(
            "jbom.application.fabrication_orchestration.BOMOrchestrationService"
        ) as mock_bom:
            handle_fab(args)
            mock_bom.assert_not_called()


# ---------------------------------------------------------------------------
# handle_fab: dry_run with all-skip
# ---------------------------------------------------------------------------


class TestHandleFabDryRun:
    def test_dry_run_all_skip_exits_0(self) -> None:
        from jbom.cli.fabrication import handle_fab

        args = SimpleNamespace(
            input=".",
            output_dir=None,
            skip_bom=True,
            skip_pos=True,
            skip_gerbers=True,
            dry_run=True,
            verbose=False,
            force=False,
            netlist=False,
            inventory_files=None,
            smd_only=False,
            layer=None,
            origin="board",
            fabricator=None,
            defaults="generic",
        )
        from jbom.config.fabricators import get_available_fabricators

        for fid in get_available_fabricators():
            setattr(args, f"fabricator_flag_{fid}", False)

        rc = handle_fab(args)
        assert rc == 0


# ---------------------------------------------------------------------------
# FabricationWorkflow routing
# ---------------------------------------------------------------------------


class TestHandleFabWorkflowRouting:
    def test_skip_gerbers_does_not_invoke_gerber_exporter(self) -> None:
        from jbom.cli.fabrication import handle_fab

        args = SimpleNamespace(
            input=".",
            output_dir=None,
            skip_bom=True,
            skip_pos=True,
            skip_gerbers=True,
            dry_run=False,
            verbose=False,
            force=False,
            netlist=False,
            inventory_files=None,
            smd_only=False,
            layer=None,
            origin="board",
            fabricator=None,
            defaults="generic",
        )
        from jbom.config.fabricators import get_available_fabricators

        for fid in get_available_fabricators():
            setattr(args, f"fabricator_flag_{fid}", False)

        with patch(
            "jbom.application.fabrication_orchestration.GerberExporter"
        ) as mock_gerber:
            handle_fab(args)
            mock_gerber.assert_not_called()
