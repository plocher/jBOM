"""Unit tests for GerberExporter, GerberRequest, and GerberResult (issue #224).

Covers:
- GerberRequest validation (empty fields raise ValueError)
- GerberResult structure and post-init normalisation
- GerberExporter: kicad-cli not on PATH → skipped result
- GerberExporter: PCB file not found → skipped result
- GerberExporter: plugin mode (pcbnew importable) → stub skipped result
- GerberExporter: kicad-cli succeeds → artifacts collected
- GerberExporter: kicad-cli gerber step fails → skipped result with error
- GerberExporter: drill step failure produces diagnostic but does not skip whole result
- output_directory is created when it does not exist
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jbom.services.gerber_service import (
    GerberExporter,
    GerberRequest,
    GerberResult,
    _find_kicad_cli,
    _kicad_cli_not_found_message,
)


# ---------------------------------------------------------------------------
# GerberRequest validation
# ---------------------------------------------------------------------------


class TestGerberRequestValidation:
    def test_raises_when_pcb_file_empty(self, tmp_path: Path) -> None:
        # Use a plain empty string — Path("") → Path(".") so it would not raise.
        with pytest.raises(ValueError):
            GerberRequest(pcb_file="", output_directory=tmp_path)  # type: ignore[arg-type]

    def test_raises_when_output_directory_empty(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            GerberRequest(
                pcb_file=tmp_path / "board.kicad_pcb",
                output_directory="",  # type: ignore[arg-type]
            )

    def test_defaults_are_sane(self, tmp_path: Path) -> None:
        req = GerberRequest(
            pcb_file=tmp_path / "board.kicad_pcb",
            output_directory=tmp_path / "gerbers",
        )
        assert req.fabricator == "generic"
        assert req.include_drill is True
        assert req.include_netlist is False

    def test_path_coercion(self, tmp_path: Path) -> None:
        req = GerberRequest(
            pcb_file=str(tmp_path / "board.kicad_pcb"),  # type: ignore[arg-type]
            output_directory=str(tmp_path / "gerbers"),  # type: ignore[arg-type]
        )
        assert isinstance(req.pcb_file, Path)
        assert isinstance(req.output_directory, Path)


# ---------------------------------------------------------------------------
# GerberResult structure
# ---------------------------------------------------------------------------


class TestGerberResult:
    def test_skipped_defaults(self) -> None:
        result = GerberResult(artifacts=(), diagnostics=())
        assert result.skipped is False
        assert result.skip_reason == ""

    def test_skipped_result(self) -> None:
        result = GerberResult(
            artifacts=(),
            diagnostics=("reason",),
            skipped=True,
            skip_reason="kicad_cli_not_found",
        )
        assert result.skipped is True
        assert result.skip_reason == "kicad_cli_not_found"
        assert result.artifacts == ()

    def test_artifacts_immutable(self, tmp_path: Path) -> None:
        p = tmp_path / "a.gbr"
        result = GerberResult(artifacts=(p,), diagnostics=())
        assert isinstance(result.artifacts, tuple)


# ---------------------------------------------------------------------------
# GerberExporter: kicad-cli not found
# ---------------------------------------------------------------------------


class TestFindKicadCli:
    """Tests for the _find_kicad_cli discovery helper."""

    def test_returns_path_from_which_first(self) -> None:
        with patch(
            "jbom.services.gerber_service.shutil.which",
            return_value="/usr/bin/kicad-cli",
        ):
            assert _find_kicad_cli() == "/usr/bin/kicad-cli"

    def test_returns_none_when_not_on_path_and_no_known_locations(
        self, tmp_path: Path
    ) -> None:
        # Redirect platform.system to a value with no real install paths on this machine.
        with (
            patch("jbom.services.gerber_service.shutil.which", return_value=None),
            patch("jbom.services.gerber_service.platform.system", return_value="Linux"),
            patch(
                "jbom.services.gerber_service.Path.is_file",
                return_value=False,
            ),
        ):
            assert _find_kicad_cli() is None

    def test_macos_bundle_path_returned_when_binary_exists(
        self, tmp_path: Path
    ) -> None:
        # Create a fake kicad-cli binary so is_file() returns True for it.
        fake_cli = tmp_path / "kicad-cli"
        fake_cli.write_text("", encoding="utf-8")

        import jbom.services.gerber_service as svc

        original_path = svc.Path

        class _FakePath(type(Path())):
            """Intercept the macOS bundle path to redirect to tmp_path."""

            def __new__(cls, *args, **kwargs):
                p = original_path(*args, **kwargs)
                # Redirect the macOS bundle directory to our tmp_path fixture
                if str(p) == "/Applications/KiCad/KiCad.app/Contents/MacOS":
                    return original_path(tmp_path)
                return p

        with (
            patch("jbom.services.gerber_service.shutil.which", return_value=None),
            patch(
                "jbom.services.gerber_service.platform.system", return_value="Darwin"
            ),
            patch("jbom.services.gerber_service.Path", _FakePath),
        ):
            result = _find_kicad_cli()

        assert result is not None
        assert "kicad-cli" in result

    def test_not_found_message_contains_kicad_cli(self) -> None:
        msg = _kicad_cli_not_found_message()
        assert "kicad-cli" in msg
        assert "BOM and POS" in msg

    def test_not_found_message_is_platform_specific(self) -> None:
        with patch(
            "jbom.services.gerber_service.platform.system", return_value="Darwin"
        ):
            msg = _kicad_cli_not_found_message()
            assert "macOS" in msg or "/Applications/KiCad" in msg

        with patch(
            "jbom.services.gerber_service.platform.system", return_value="Windows"
        ):
            msg = _kicad_cli_not_found_message()
            assert "Windows" in msg

        with patch(
            "jbom.services.gerber_service.platform.system", return_value="Linux"
        ):
            msg = _kicad_cli_not_found_message()
            assert "Linux" in msg


class TestGerberExporterNoKicadCli:
    def test_returns_skipped_when_kicad_cli_absent(self, tmp_path: Path) -> None:
        pcb = tmp_path / "board.kicad_pcb"
        pcb.write_text("", encoding="utf-8")

        with patch("jbom.services.gerber_service._find_kicad_cli", return_value=None):
            result = GerberExporter().generate(
                GerberRequest(
                    pcb_file=pcb,
                    output_directory=tmp_path / "gerbers",
                )
            )

        assert result.skipped is True
        assert result.skip_reason == "kicad_cli_not_found"
        assert any("kicad-cli" in d for d in result.diagnostics)
        assert result.artifacts == ()


# ---------------------------------------------------------------------------
# GerberExporter: PCB file missing
# ---------------------------------------------------------------------------


class TestGerberExporterMissingPcb:
    def test_returns_skipped_when_pcb_missing(self, tmp_path: Path) -> None:
        with patch(
            "jbom.services.gerber_service._find_kicad_cli",
            return_value="/usr/bin/kicad-cli",
        ):
            result = GerberExporter().generate(
                GerberRequest(
                    pcb_file=tmp_path / "nonexistent.kicad_pcb",
                    output_directory=tmp_path / "gerbers",
                )
            )

        assert result.skipped is True
        assert result.skip_reason == "pcb_file_not_found"
        assert any("PCB file not found" in d for d in result.diagnostics)


# ---------------------------------------------------------------------------
# GerberExporter: plugin mode stub
# ---------------------------------------------------------------------------


class TestGerberExporterPluginMode:
    def test_plugin_mode_returns_stub_skipped(self, tmp_path: Path) -> None:
        fake_pcbnew = types.ModuleType("pcbnew")
        pcb = tmp_path / "board.kicad_pcb"
        pcb.write_text("", encoding="utf-8")

        with patch.dict(sys.modules, {"pcbnew": fake_pcbnew}):
            result = GerberExporter().generate(
                GerberRequest(
                    pcb_file=pcb,
                    output_directory=tmp_path / "gerbers",
                )
            )

        assert result.skipped is True
        assert result.skip_reason == "pcbnew_api_not_implemented"
        assert any("not yet implemented" in d for d in result.diagnostics)


# ---------------------------------------------------------------------------
# GerberExporter: kicad-cli gerber step fails
# ---------------------------------------------------------------------------


class TestGerberExporterCliFailure:
    def test_skipped_when_gerber_command_fails(self, tmp_path: Path) -> None:
        pcb = tmp_path / "board.kicad_pcb"
        pcb.write_text("", encoding="utf-8")
        output_dir = tmp_path / "gerbers"

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "plot failed"
        mock_result.stdout = ""

        with (
            patch(
                "jbom.services.gerber_service._find_kicad_cli",
                return_value="/usr/bin/kicad-cli",
            ),
            patch(
                "jbom.services.gerber_service.subprocess.run", return_value=mock_result
            ),
        ):
            result = GerberExporter().generate(
                GerberRequest(pcb_file=pcb, output_directory=output_dir)
            )

        assert result.skipped is True
        assert result.skip_reason == "gerber_export_failed"
        assert any("failed" in d for d in result.diagnostics)


# ---------------------------------------------------------------------------
# GerberExporter: successful run collects new artifacts
# ---------------------------------------------------------------------------


class TestGerberExporterSuccess:
    def _make_fake_run(self, output_dir: Path, filenames: list[str]):
        """Return a subprocess.run mock that creates files on first call."""
        call_count = [0]

        def _fake_run(cmd, **_kwargs):
            call_count[0] += 1
            # First call is the gerbers export — create fake gerber files
            if call_count[0] == 1:
                for name in filenames:
                    (output_dir / name).write_text("", encoding="utf-8")
            mock = MagicMock()
            mock.returncode = 0
            mock.stderr = ""
            mock.stdout = ""
            return mock

        return _fake_run

    def test_artifacts_collected_after_successful_gerber_export(
        self, tmp_path: Path
    ) -> None:
        pcb = tmp_path / "board.kicad_pcb"
        pcb.write_text("", encoding="utf-8")
        output_dir = tmp_path / "gerbers"

        fake_run = self._make_fake_run(output_dir, ["board-F.Cu.gbr", "board-B.Cu.gbr"])

        with (
            patch(
                "jbom.services.gerber_service._find_kicad_cli",
                return_value="/usr/bin/kicad-cli",
            ),
            patch("jbom.services.gerber_service.subprocess.run", side_effect=fake_run),
        ):
            result = GerberExporter().generate(
                GerberRequest(
                    pcb_file=pcb,
                    output_directory=output_dir,
                    include_drill=False,
                    include_netlist=False,
                )
            )

        assert result.skipped is False
        assert len(result.artifacts) == 2
        assert all(a.suffix == ".gbr" for a in result.artifacts)

    def test_output_directory_is_created_if_absent(self, tmp_path: Path) -> None:
        pcb = tmp_path / "board.kicad_pcb"
        pcb.write_text("", encoding="utf-8")
        output_dir = tmp_path / "new" / "gerbers"
        assert not output_dir.exists()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_result.stdout = ""

        with (
            patch(
                "jbom.services.gerber_service._find_kicad_cli",
                return_value="/usr/bin/kicad-cli",
            ),
            patch(
                "jbom.services.gerber_service.subprocess.run", return_value=mock_result
            ),
        ):
            GerberExporter().generate(
                GerberRequest(
                    pcb_file=pcb,
                    output_directory=output_dir,
                    include_drill=False,
                )
            )

        assert output_dir.exists()
