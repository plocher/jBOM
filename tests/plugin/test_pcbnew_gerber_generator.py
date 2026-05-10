"""Unit tests for ``jbom.plugin.gerber_generator.PcbnewGerberGenerator``.

These tests run in a CLI/test environment where ``pcbnew`` is absent.
All KiCad API objects are replaced by :class:`unittest.mock.MagicMock` so
that the module-level import succeeds and ``generate()`` can be tested with
controlled pcbnew mock behaviour.

Coverage targets:
- Module importable without pcbnew
- ``_load_gerber_policy`` reads fabricator config layers / falls back to defaults
- ``generate()`` skips layers where ``board.GetLayerID()`` returns UNDEFINED_LAYER
- ``generate()`` skips disabled layers (``board.IsLayerEnabled`` returns False)
- ``generate()`` collects written artifacts from the output directory
- Drill generation failure returns the gerber-only artifact list
- Output directory creation failure returns a skipped result
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch


# ---------------------------------------------------------------------------
# Guard: confirm pcbnew is absent in the test environment
# ---------------------------------------------------------------------------


def _ensure_pcbnew_absent() -> None:
    assert (
        "pcbnew" not in sys.modules
    ), "pcbnew is present — these tests must run outside KiCad."


# ---------------------------------------------------------------------------
# Importability
# ---------------------------------------------------------------------------


class TestImportability:
    """PcbnewGerberGenerator is importable without pcbnew."""

    def test_module_importable_without_pcbnew(self) -> None:
        _ensure_pcbnew_absent()
        from jbom.plugin.gerber_generator import PcbnewGerberGenerator  # noqa: F401

        assert PcbnewGerberGenerator is not None

    def test_module_does_not_pull_in_pcbnew(self) -> None:
        _ensure_pcbnew_absent()
        import jbom.plugin.gerber_generator  # noqa: F401

        assert "pcbnew" not in sys.modules


# ---------------------------------------------------------------------------
# _load_gerber_policy
# ---------------------------------------------------------------------------


class TestLoadGerberPolicy:
    """_load_gerber_policy reads fabricator config and falls back gracefully."""

    def _make_generator(self) -> object:
        from jbom.plugin.gerber_generator import PcbnewGerberGenerator

        return PcbnewGerberGenerator(board=MagicMock())

    def test_returns_default_layers_when_fabricator_not_found(self) -> None:
        from jbom.common.types import Diagnostic

        gen = self._make_generator()
        diagnostics: list[Diagnostic] = []
        with patch(
            "jbom.plugin.gerber_generator.PcbnewGerberGenerator._load_gerber_policy",
            wraps=gen._load_gerber_policy,
        ):
            # Patch load_fabricator to raise so we exercise the fallback path.
            with patch(
                "jbom.config.fabricators.load_fabricator",
                side_effect=ValueError("unknown fabricator"),
            ):
                layers, protel, drill_cfg = gen._load_gerber_policy(
                    "nonexistent", diagnostics
                )

        assert "F.Cu" in layers
        assert "Edge.Cuts" in layers
        assert protel is True
        assert drill_cfg == {}
        assert any("nonexistent" in d.message for d in diagnostics)

    def test_returns_fabricator_config_layers_for_jlc(self) -> None:
        from jbom.common.types import Diagnostic

        gen = self._make_generator()
        diagnostics: list[Diagnostic] = []
        layers, protel, drill_cfg = gen._load_gerber_policy("jlc", diagnostics)

        # jlc.fab.yaml specifies 9 standard layers
        assert "F.Cu" in layers
        assert "B.Cu" in layers
        assert "Edge.Cuts" in layers
        assert len(layers) >= 9
        assert protel is True  # jlc uses protel extensions
        assert diagnostics == []

    def test_returns_default_layers_when_gerbers_stanza_empty(self) -> None:
        from jbom.common.types import Diagnostic
        from jbom.plugin.gerber_generator import _DEFAULT_LAYERS

        gen = self._make_generator()
        diagnostics: list[Diagnostic] = []

        fake_config = MagicMock()
        fake_config.gerbers = {}  # empty stanza

        with patch("jbom.config.fabricators.load_fabricator", return_value=fake_config):
            layers, protel, drill_cfg = gen._load_gerber_policy("generic", diagnostics)

        assert layers == _DEFAULT_LAYERS
        assert protel is True
        assert drill_cfg == {}


# ---------------------------------------------------------------------------
# generate() — output directory handling
# ---------------------------------------------------------------------------


class TestGenerateOutputDir:
    """generate() handles output directory creation failures."""

    def _make_generator_with_mock_pcbnew(self) -> tuple:
        from jbom.plugin.gerber_generator import PcbnewGerberGenerator

        mock_board = MagicMock()
        gen = PcbnewGerberGenerator(board=mock_board)
        return gen, mock_board

    def test_returns_skipped_when_mkdir_fails(self, tmp_path: Path) -> None:
        gen, _ = self._make_generator_with_mock_pcbnew()

        fake_pcbnew = MagicMock()
        fake_pcbnew.UNDEFINED_LAYER = -1
        fake_pcbnew.PLOT_FORMAT_GERBER = 1

        bad_dir = tmp_path / "readonly_parent" / "gerbers"
        # Patch Path.mkdir to raise OSError
        with patch(
            "jbom.plugin.gerber_generator.PcbnewGerberGenerator._load_gerber_policy",
            return_value=(["F.Cu"], True, {}),
        ):
            with patch(
                "builtins.__import__",
                side_effect=lambda name, *a, **kw: (
                    fake_pcbnew if name == "pcbnew" else __import__(name, *a, **kw)
                ),
            ):
                with patch.object(
                    Path, "mkdir", side_effect=OSError("permission denied")
                ):
                    result = gen.generate(bad_dir, fabricator="jlc")

        assert result.skipped is True
        assert result.skip_reason == "output_dir_error"


# ---------------------------------------------------------------------------
# generate() — layer iteration, UNDEFINED_LAYER, disabled layers
# ---------------------------------------------------------------------------


class TestGenerateLayerIteration:
    """generate() iterates the layer list and skips undefined/disabled layers."""

    def _build_mock_pcbnew(
        self,
        *,
        layer_ids: dict[str, int] | None = None,
        enabled_layers: set[int] | None = None,
        undefined: int = -1,
    ) -> MagicMock:
        """Return a mock pcbnew module with configurable board.GetLayerID() behaviour."""
        if layer_ids is None:
            layer_ids = {"F.Cu": 0, "B.Cu": 31, "Edge.Cuts": 44}
        if enabled_layers is None:
            enabled_layers = set(layer_ids.values())

        pcb = MagicMock()
        pcb.UNDEFINED_LAYER = undefined
        pcb.PLOT_FORMAT_GERBER = 1
        pcb.FromMM = MagicMock(return_value=100)

        board = MagicMock()
        board.GetLayerID = MagicMock(
            side_effect=lambda name: layer_ids.get(name, undefined)
        )
        board.IsLayerEnabled = MagicMock(side_effect=lambda lid: lid in enabled_layers)
        board.GetDesignSettings.return_value.GetAuxOrigin.return_value = (0, 0)

        plot_ctrl = MagicMock()
        pcb.PLOT_CONTROLLER = MagicMock(return_value=plot_ctrl)

        drill_writer = MagicMock()
        pcb.EXCELLON_WRITER = MagicMock(return_value=drill_writer)

        pcb._mock_board = board
        pcb._mock_plot_ctrl = plot_ctrl
        pcb._mock_drill_writer = drill_writer
        return pcb

    def _run_generate(
        self,
        tmp_path: Path,
        layers: list[str],
        mock_pcbnew: MagicMock,
    ):
        from jbom.plugin.gerber_generator import PcbnewGerberGenerator

        gen = PcbnewGerberGenerator(board=mock_pcbnew._mock_board)

        with patch(
            "jbom.plugin.gerber_generator.PcbnewGerberGenerator._load_gerber_policy",
            return_value=(layers, True, {}),
        ):
            with patch(
                "builtins.__import__",
                side_effect=lambda name, *a, **kw: (
                    mock_pcbnew if name == "pcbnew" else __import__(name, *a, **kw)
                ),
            ):
                result = gen.generate(tmp_path / "gerbers", fabricator="jlc")
        return result

    def test_undefined_layer_is_skipped_with_diagnostic(self, tmp_path: Path) -> None:
        """A layer not on the board (UNDEFINED_LAYER) adds a diagnostic and is skipped."""
        pcb = self._build_mock_pcbnew(
            layer_ids={"F.Cu": 0},  # B.Cu absent → UNDEFINED_LAYER
        )
        result = self._run_generate(tmp_path, ["F.Cu", "B.Cu"], pcb)

        # SetLayer should only have been called once (for F.Cu)
        set_layer_calls = pcb._mock_plot_ctrl.SetLayer.call_args_list
        assert len(set_layer_calls) == 1
        assert set_layer_calls[0] == call(0)

        # Diagnostic must mention the skipped layer
        assert any("B.Cu" in d.message for d in result.diagnostics)

    def test_disabled_layer_is_silently_skipped(self, tmp_path: Path) -> None:
        """An explicitly disabled layer is skipped without a diagnostic."""
        pcb = self._build_mock_pcbnew(
            layer_ids={"F.Cu": 0, "B.Cu": 31},
            enabled_layers={0},  # B.Cu (31) disabled
        )
        result = self._run_generate(tmp_path, ["F.Cu", "B.Cu"], pcb)

        set_layer_calls = pcb._mock_plot_ctrl.SetLayer.call_args_list
        assert len(set_layer_calls) == 1
        assert set_layer_calls[0] == call(0)
        # No diagnostic for disabled layers
        assert not any("B.Cu" in d.message for d in result.diagnostics)

    def test_plot_controller_closed_after_loop(self, tmp_path: Path) -> None:
        """ClosePlot() is called regardless of how many layers were plotted."""
        pcb = self._build_mock_pcbnew(layer_ids={"F.Cu": 0})
        self._run_generate(tmp_path, ["F.Cu"], pcb)

        pcb._mock_plot_ctrl.ClosePlot.assert_called_once()

    def test_returns_skipped_when_plot_controller_raises(self, tmp_path: Path) -> None:
        """A crash inside the plot loop yields skipped=True."""
        from jbom.plugin.gerber_generator import PcbnewGerberGenerator

        pcb = self._build_mock_pcbnew(layer_ids={"F.Cu": 0})
        pcb.PLOT_CONTROLLER.side_effect = RuntimeError("pcbnew exploded")

        gen = PcbnewGerberGenerator(board=pcb._mock_board)
        with patch(
            "jbom.plugin.gerber_generator.PcbnewGerberGenerator._load_gerber_policy",
            return_value=(["F.Cu"], True, {}),
        ):
            with patch(
                "builtins.__import__",
                side_effect=lambda name, *a, **kw: (
                    pcb if name == "pcbnew" else __import__(name, *a, **kw)
                ),
            ):
                result = gen.generate(tmp_path / "gerbers", fabricator="jlc")

        assert result.skipped is True
        assert result.skip_reason == "plot_error"
        assert any("plotting" in d.message.lower() for d in result.diagnostics)


# ---------------------------------------------------------------------------
# generate() — artifact collection
# ---------------------------------------------------------------------------


class TestGenerateArtifacts:
    """generate() collects all files written to the output directory."""

    def test_returns_files_present_in_output_dir(self, tmp_path: Path) -> None:
        """Any files in the output dir after plotting are returned as artifacts."""
        from jbom.plugin.gerber_generator import PcbnewGerberGenerator

        gerber_dir = tmp_path / "gerbers"
        gerber_dir.mkdir()

        # Pre-create fake "gerber" files that the mock plot controller would write
        (gerber_dir / "board-F_Cu.gtl").write_bytes(b"gerber data")
        (gerber_dir / "board-Edge_Cuts.gko").write_bytes(b"gerber data")
        (gerber_dir / "board.drl").write_bytes(b"drill data")

        pcb = MagicMock()
        pcb.UNDEFINED_LAYER = -1
        pcb.PLOT_FORMAT_GERBER = 1
        pcb.FromMM = MagicMock(return_value=100)

        board = MagicMock()
        board.GetLayerID = MagicMock(return_value=0)
        board.IsLayerEnabled = MagicMock(return_value=True)
        board.GetDesignSettings.return_value.GetAuxOrigin.return_value = (0, 0)
        pcb.PLOT_CONTROLLER = MagicMock(return_value=MagicMock())
        pcb.EXCELLON_WRITER = MagicMock(return_value=MagicMock())

        gen = PcbnewGerberGenerator(board=board)
        with patch(
            "jbom.plugin.gerber_generator.PcbnewGerberGenerator._load_gerber_policy",
            return_value=(["F.Cu"], True, {}),
        ):
            with patch(
                "builtins.__import__",
                side_effect=lambda name, *a, **kw: (
                    pcb if name == "pcbnew" else __import__(name, *a, **kw)
                ),
            ):
                result = gen.generate(gerber_dir, fabricator="jlc")

        assert result.skipped is False
        assert len(result.artifacts) == 3
        artifact_names = {p.name for p in result.artifacts}
        assert "board-F_Cu.gtl" in artifact_names
        assert "board.drl" in artifact_names

    def test_returns_skipped_when_no_files_written(self, tmp_path: Path) -> None:
        """An empty output directory yields skipped=True / no_artifacts."""
        from jbom.plugin.gerber_generator import PcbnewGerberGenerator

        gerber_dir = tmp_path / "gerbers"
        gerber_dir.mkdir()  # empty — mock won't write any files

        pcb = MagicMock()
        pcb.UNDEFINED_LAYER = -1
        pcb.PLOT_FORMAT_GERBER = 1
        pcb.FromMM = MagicMock(return_value=100)

        board = MagicMock()
        board.GetLayerID = MagicMock(return_value=0)
        board.IsLayerEnabled = MagicMock(return_value=True)
        board.GetDesignSettings.return_value.GetAuxOrigin.return_value = (0, 0)
        pcb.PLOT_CONTROLLER = MagicMock(return_value=MagicMock())
        pcb.EXCELLON_WRITER = MagicMock(return_value=MagicMock())

        gen = PcbnewGerberGenerator(board=board)
        with patch(
            "jbom.plugin.gerber_generator.PcbnewGerberGenerator._load_gerber_policy",
            return_value=(["F.Cu"], True, {}),
        ):
            with patch(
                "builtins.__import__",
                side_effect=lambda name, *a, **kw: (
                    pcb if name == "pcbnew" else __import__(name, *a, **kw)
                ),
            ):
                result = gen.generate(gerber_dir, fabricator="jlc")

        assert result.skipped is True
        assert result.skip_reason == "no_artifacts"
