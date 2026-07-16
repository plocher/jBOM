"""Lifecycle regression tests for ``JBOMFabricationPlugin`` reinvocation.

These tests validate plugin-side dialog ownership semantics without requiring
KiCad or wxPython:

- A created dialog is retained by the plugin until dialog teardown callback.
- Re-clicking while a dialog is still active raises/focuses that dialog instead
  of creating a second one.
- A stale wrapped-object reference is tolerated and replaced on next Run().
"""

from __future__ import annotations

import importlib
import sys
import types
import pytest


class _FakeActionPlugin:
    """Minimal stand-in for ``pcbnew.ActionPlugin``."""

    def register(self) -> None:
        """No-op registration for test-only plugin imports."""


class _FakeBoard:
    """Minimal stand-in for the active PCB board object."""

    def __init__(self, file_name: str = "") -> None:
        self._file_name = file_name

    def GetFileName(self) -> str:  # noqa: N802 — mirrors KiCad API
        """Return configured fake board filename."""
        return self._file_name


class _FakeDialog:
    """Fake dialog capturing lifecycle signals from ``plugin.py``."""

    created_instances: list["_FakeDialog"] = []

    def __init__(
        self,
        *,
        pcb_path: str = "",
        archive_name: str = "",
        on_destroy: object | None = None,
    ) -> None:
        self.pcb_path = pcb_path
        self.archive_name = archive_name
        self.on_destroy = on_destroy
        self.show_calls = 0
        self.raise_calls = 0
        self.user_attention_calls = 0
        self._shown = True
        _FakeDialog.created_instances.append(self)

    def Show(self) -> None:
        """Record modeless Show invocation."""
        self.show_calls += 1

    def Raise(self) -> None:
        """Record raise/focus request."""
        self.raise_calls += 1

    def RequestUserAttention(self) -> None:
        """Record optional user-attention request."""
        self.user_attention_calls += 1

    def IsShownOnScreen(self) -> bool:
        """Report current visibility state."""
        return self._shown

    def IsShown(self) -> bool:
        """Fallback visibility API used by plugin guard path."""
        return self._shown


class _StaleDialogRef:
    """Simulate a stale wx wrapped object that raises on visibility check."""

    def IsShownOnScreen(self) -> bool:
        """Raise runtime error to emulate dead wrapped C++ dialog object."""
        raise RuntimeError("wrapped C/C++ object has been deleted")


def _load_plugin_module_with_fake_pcbnew(
    monkeypatch: pytest.MonkeyPatch,
) -> types.ModuleType:
    """Import ``jbom.plugin.plugin`` with a fake ``pcbnew`` module present."""
    fake_pcbnew = types.ModuleType("pcbnew")
    fake_pcbnew.ActionPlugin = _FakeActionPlugin
    board = _FakeBoard("")
    fake_pcbnew.GetBoard = lambda: board
    monkeypatch.setitem(sys.modules, "pcbnew", fake_pcbnew)

    # Force a fresh import path each test so module-level state does not leak.
    sys.modules.pop("jbom.plugin.dialog", None)
    sys.modules.pop("jbom.plugin.plugin", None)
    sys.modules.pop("jbom.plugin", None)

    module = importlib.import_module("jbom.plugin.plugin")
    return module


def _install_fake_dialog_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install fake dialog module consumed by plugin Run() path."""
    _FakeDialog.created_instances.clear()
    fake_dialog_module = types.ModuleType("jbom.plugin.dialog")
    fake_dialog_module.JBOMFabricationDialog = _FakeDialog
    monkeypatch.setitem(sys.modules, "jbom.plugin.dialog", fake_dialog_module)


class TestPluginReinvokeLifecycle:
    """Regression tests for repeated ActionPlugin invocations."""

    def test_active_dialog_reference_cleared_on_teardown_callback(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Plugin should clear retained dialog reference when teardown fires."""
        plugin_module = _load_plugin_module_with_fake_pcbnew(monkeypatch)
        _install_fake_dialog_module(monkeypatch)

        plugin = plugin_module.JBOMFabricationPlugin()
        plugin.Run()

        assert len(_FakeDialog.created_instances) == 1
        first = _FakeDialog.created_instances[0]
        assert plugin._active_dialog is first
        assert first.show_calls == 1

        assert callable(first.on_destroy)
        first.on_destroy()
        assert plugin._active_dialog is None

        plugin.Run()
        assert len(_FakeDialog.created_instances) == 2
        assert plugin._active_dialog is _FakeDialog.created_instances[1]

    def test_second_run_raises_existing_visible_dialog(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Second click should focus the active dialog instead of creating new."""
        plugin_module = _load_plugin_module_with_fake_pcbnew(monkeypatch)
        _install_fake_dialog_module(monkeypatch)

        plugin = plugin_module.JBOMFabricationPlugin()
        plugin.Run()
        plugin.Run()

        assert len(_FakeDialog.created_instances) == 1
        assert _FakeDialog.created_instances[0].raise_calls == 1
        assert plugin._active_dialog is _FakeDialog.created_instances[0]

    def test_stale_dialog_reference_is_replaced(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A stale wrapped-object reference should be cleared and replaced."""
        plugin_module = _load_plugin_module_with_fake_pcbnew(monkeypatch)
        _install_fake_dialog_module(monkeypatch)

        plugin = plugin_module.JBOMFabricationPlugin()
        plugin._active_dialog = _StaleDialogRef()
        plugin.Run()

        assert len(_FakeDialog.created_instances) == 1
        assert plugin._active_dialog is _FakeDialog.created_instances[0]
