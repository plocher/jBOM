"""Unit tests for the ``jbom gerbers`` CLI command (issue #224).

Covers:
- Command registration in the main parser
- ``--no-drill`` / ``--no-netlist`` / ``--netlist`` argument defaults
- Graceful degradation when kicad-cli is unavailable (exit code 1, no crash)
- Dry-run output when PCB file cannot be resolved
- ``_render_gerber_result`` rendering for skipped and success states
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from jbom.cli.gerbers import _render_gerber_result
from jbom.cli.main import create_parser
from jbom.services.gerber_service import GerberResult


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestGerbersCommandRegistration:
    def test_gerbers_registered_in_main_parser(self) -> None:
        parser = create_parser()
        # Triggers SystemExit(0) with help text; use parse_known_args to probe
        subparsers_action = None
        for action in parser._subparsers._group_actions:  # type: ignore[attr-defined]
            if hasattr(action, "choices"):
                subparsers_action = action
                break
        assert subparsers_action is not None
        assert "gerbers" in subparsers_action.choices

    def test_gerbers_has_expected_arguments(self) -> None:
        parser = create_parser()
        args = parser.parse_args(
            ["gerbers", "--no-drill", "--netlist", "--dry-run", "."]
        )
        assert args.no_drill is True
        assert args.netlist is True
        assert args.dry_run is True

    def test_no_drill_default_is_false(self) -> None:
        parser = create_parser()
        args = parser.parse_args(["gerbers", "."])
        assert args.no_drill is False

    def test_netlist_default_is_false(self) -> None:
        parser = create_parser()
        args = parser.parse_args(["gerbers", "."])
        assert args.netlist is False


# ---------------------------------------------------------------------------
# _render_gerber_result
# ---------------------------------------------------------------------------


class TestRenderGerberResult:
    def test_skipped_result_returns_exit_1(self, capsys) -> None:
        result = GerberResult(
            artifacts=(),
            diagnostics=("kicad-cli not found",),
            skipped=True,
            skip_reason="kicad_cli_not_found",
        )
        rc = _render_gerber_result(result, verbose=False)
        assert rc == 1
        captured = capsys.readouterr()
        assert "kicad_cli_not_found" in captured.err

    def test_success_result_returns_exit_0(self, tmp_path: Path, capsys) -> None:
        gbr = tmp_path / "board-F.Cu.gbr"
        gbr.write_text("", encoding="utf-8")
        result = GerberResult(artifacts=(gbr,), diagnostics=(), skipped=False)
        rc = _render_gerber_result(result, verbose=False)
        assert rc == 0
        captured = capsys.readouterr()
        assert "Written:" in captured.out

    def test_verbose_prints_count(self, tmp_path: Path, capsys) -> None:
        gbr = tmp_path / "board-F.Cu.gbr"
        gbr.write_text("", encoding="utf-8")
        result = GerberResult(artifacts=(gbr,), diagnostics=(), skipped=False)
        _render_gerber_result(result, verbose=True)
        captured = capsys.readouterr()
        assert "1 fabrication file" in captured.out

    def test_empty_artifacts_returns_exit_1(self, capsys) -> None:
        result = GerberResult(artifacts=(), diagnostics=(), skipped=False)
        rc = _render_gerber_result(result, verbose=False)
        assert rc == 1
        assert "no output files" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# handle_gerbers: graceful degradation without kicad-cli
# ---------------------------------------------------------------------------


class TestHandleGerbersNoCli:
    def test_handle_gerbers_returns_1_when_pcb_unresolvable(self, capsys) -> None:
        """When PCB resolution fails, handle_gerbers must exit 1 not crash."""
        from jbom.cli.gerbers import handle_gerbers

        args = SimpleNamespace(
            input="nonexistent_project_xyz",
            output_dir=None,
            no_drill=False,
            no_netlist=False,
            netlist=False,
            dry_run=False,
            verbose=False,
            fabricator=None,
        )
        # Patch fabricator resolution flags
        for fid in ["jlc", "pcbway", "seeed", "generic"]:
            setattr(args, f"fabricator_flag_{fid}", False)

        rc = handle_gerbers(args)
        assert rc == 1

    def test_handle_gerbers_kicad_cli_absent_exits_1(
        self, tmp_path: Path, capsys
    ) -> None:
        """When kicad-cli is not installed, command exits 1 with diagnostic."""
        from jbom.cli.gerbers import handle_gerbers

        pcb = tmp_path / "board.kicad_pcb"
        pcb.write_text("", encoding="utf-8")
        (tmp_path / "board.kicad_pro").write_text("{}", encoding="utf-8")

        args = SimpleNamespace(
            input=str(tmp_path),
            output_dir=None,
            no_drill=False,
            no_netlist=False,
            netlist=False,
            dry_run=False,
            verbose=False,
            fabricator=None,
        )
        for fid in ["jlc", "pcbway", "seeed", "generic"]:
            setattr(args, f"fabricator_flag_{fid}", False)

        with patch("jbom.services.gerber_service.shutil.which", return_value=None):
            rc = handle_gerbers(args)

        assert rc == 1
        captured = capsys.readouterr()
        assert "kicad-cli" in captured.err
