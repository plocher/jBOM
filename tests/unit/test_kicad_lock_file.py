"""Unit tests for KiCad lock file detection and write guard (issue #213).

Covers:
- ProjectContext.lock_file path derivation
- ProjectContext.is_locked filesystem check
- check_write_permitted: pass, raise, warn, plugin-mode bypass
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from jbom.common.kicad_runtime import check_write_permitted, is_running_inside_kicad
from jbom.services.project_context import ProjectContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_project(tmp_path: Path, name: str = "myboard") -> Path:
    """Create a minimal KiCad project directory containing a .kicad_pro file."""
    project_dir = tmp_path / name
    project_dir.mkdir()
    (project_dir / f"{name}.kicad_pro").write_text("{}", encoding="utf-8")
    return project_dir


# ---------------------------------------------------------------------------
# ProjectContext.lock_file / is_locked
# ---------------------------------------------------------------------------


class TestProjectContextLockFile:
    def test_lock_file_path_uses_project_base_name(self, tmp_path: Path) -> None:
        """lock_file path is <project_dir>/<project_name>.lck."""
        project_dir = _make_project(tmp_path, "widget")
        ctx = ProjectContext(project_dir)
        assert ctx.lock_file == project_dir / "widget.lck"

    def test_is_locked_false_when_no_lock_file(self, tmp_path: Path) -> None:
        """is_locked returns False when the lock file does not exist."""
        project_dir = _make_project(tmp_path)
        ctx = ProjectContext(project_dir)
        assert ctx.is_locked is False

    def test_is_locked_true_when_lock_file_present(self, tmp_path: Path) -> None:
        """is_locked returns True when the lock file exists."""
        project_dir = _make_project(tmp_path, "open_in_kicad")
        (project_dir / "open_in_kicad.lck").write_text("", encoding="utf-8")
        ctx = ProjectContext(project_dir)
        assert ctx.is_locked is True

    def test_is_locked_reflects_runtime_filesystem_state(self, tmp_path: Path) -> None:
        """is_locked is evaluated fresh on each access (not cached at init)."""
        project_dir = _make_project(tmp_path)
        ctx = ProjectContext(project_dir)
        lock_path = project_dir / "myboard.lck"

        assert ctx.is_locked is False
        lock_path.write_text("", encoding="utf-8")
        assert ctx.is_locked is True
        lock_path.unlink()
        assert ctx.is_locked is False


# ---------------------------------------------------------------------------
# is_running_inside_kicad
# ---------------------------------------------------------------------------


class TestIsRunningInsideKicad:
    def test_returns_false_outside_kicad(self) -> None:
        """In the test environment pcbnew is not importable → False."""
        # Guard: if the test machine somehow has pcbnew installed this test is
        # vacuously True; skip it rather than fail spuriously.
        try:
            import pcbnew  # noqa: F401

            pytest.skip("pcbnew is installed on this machine")
        except ImportError:
            pass
        assert is_running_inside_kicad() is False

    def test_returns_true_when_pcbnew_importable(self) -> None:
        """Simulate plugin mode by patching pcbnew into sys.modules."""
        import types

        fake_pcbnew = types.ModuleType("pcbnew")
        with patch.dict(sys.modules, {"pcbnew": fake_pcbnew}):
            assert is_running_inside_kicad() is True


# ---------------------------------------------------------------------------
# check_write_permitted
# ---------------------------------------------------------------------------


class TestCheckWritePermitted:
    def test_passes_silently_when_not_locked(self, tmp_path: Path) -> None:
        """No exception or output when project is not locked."""
        project_dir = _make_project(tmp_path)
        ctx = ProjectContext(project_dir)
        # Should complete without raising
        check_write_permitted(ctx, dry_run=False)

    def test_raises_permission_error_when_locked(self, tmp_path: Path) -> None:
        """Raises PermissionError when locked and dry_run=False."""
        project_dir = _make_project(tmp_path, "locked_proj")
        (project_dir / "locked_proj.lck").write_text("", encoding="utf-8")
        ctx = ProjectContext(project_dir)

        with pytest.raises(PermissionError) as exc_info:
            check_write_permitted(ctx, dry_run=False)

        msg = str(exc_info.value)
        assert "locked_proj.lck" in msg
        assert "KiCad lock file detected" in msg
        assert "--dry-run" in msg

    def test_warns_but_does_not_raise_on_dry_run(self, tmp_path: Path, capsys) -> None:
        """dry_run=True emits a WARNING to stderr but does not raise."""
        project_dir = _make_project(tmp_path, "open_proj")
        (project_dir / "open_proj.lck").write_text("", encoding="utf-8")
        ctx = ProjectContext(project_dir)

        # Must not raise
        check_write_permitted(ctx, dry_run=True)

        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        assert "open_proj.lck" in captured.err

    def test_plugin_mode_bypasses_lock_check(self, tmp_path: Path) -> None:
        """Plugin mode silently bypasses the write guard even when locked."""
        project_dir = _make_project(tmp_path, "kicad_open")
        (project_dir / "kicad_open.lck").write_text("", encoding="utf-8")
        ctx = ProjectContext(project_dir)
        assert ctx.is_locked is True

        import types

        fake_pcbnew = types.ModuleType("pcbnew")
        with patch.dict(sys.modules, {"pcbnew": fake_pcbnew}):
            # Must not raise even though project is locked
            check_write_permitted(ctx, dry_run=False)

    def test_plugin_mode_bypasses_dry_run_warning_too(
        self, tmp_path: Path, capsys
    ) -> None:
        """Plugin mode produces no output even with dry_run=True and a lock present."""
        project_dir = _make_project(tmp_path, "kicad_open2")
        (project_dir / "kicad_open2.lck").write_text("", encoding="utf-8")
        ctx = ProjectContext(project_dir)

        import types

        fake_pcbnew = types.ModuleType("pcbnew")
        with patch.dict(sys.modules, {"pcbnew": fake_pcbnew}):
            check_write_permitted(ctx, dry_run=True)

        captured = capsys.readouterr()
        assert captured.err == ""
