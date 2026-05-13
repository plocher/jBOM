"""Guard-behaviour tests for ``jbom.plugin``.

These tests verify that:

1. ``import jbom.plugin`` succeeds in a CLI/test environment (no ``pcbnew``
   present) and is completely inert — no ActionPlugin is registered and no
   KiCad-specific imports are triggered.

2. The core ``jbom`` package remains importable independently of KiCad.

3. The plugin's inner modules (``plugin.py``, ``dialog.py``) are **not**
   imported when running outside KiCad; they are only loaded by the guard
   branch that checks for ``pcbnew`` in ``sys.modules``.
"""

from __future__ import annotations

import sys


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _ensure_pcbnew_absent() -> None:
    """Guard: fail fast if the test environment somehow has pcbnew loaded."""
    assert "pcbnew" not in sys.modules, (
        "pcbnew is loaded in sys.modules — tests must run outside KiCad. "
        "The guard tests would be meaningless in this environment."
    )


# ---------------------------------------------------------------------------
# Guard importability
# ---------------------------------------------------------------------------


class TestPluginGuard:
    """The plugin package is importable without KiCad installed."""

    def test_jbom_plugin_importable_without_pcbnew(self) -> None:
        """``import jbom.plugin`` must succeed in a non-KiCad environment."""
        _ensure_pcbnew_absent()
        # Fresh import — may already be cached from a prior test run.
        import jbom.plugin  # noqa: F401 — side-effect import; success is the assertion

    def test_jbom_plugin_does_not_pull_in_pcbnew(self) -> None:
        """Importing jbom.plugin must not add pcbnew to sys.modules."""
        _ensure_pcbnew_absent()
        import jbom.plugin  # noqa: F401

        assert (
            "pcbnew" not in sys.modules
        ), "jbom.plugin caused pcbnew to be imported — the guard is broken."

    def test_jbom_plugin_inner_modules_not_imported_outside_kicad(self) -> None:
        """plugin.py and dialog.py must remain unimported outside KiCad."""
        _ensure_pcbnew_absent()
        import jbom.plugin  # noqa: F401

        # These modules import pcbnew / wx at the top level and must only be
        # loaded by the guarded branch inside KiCad.
        assert "jbom.plugin.plugin" not in sys.modules, (
            "jbom.plugin.plugin was imported outside KiCad — "
            "the import guard is not working."
        )
        assert "jbom.plugin.dialog" not in sys.modules, (
            "jbom.plugin.dialog was imported outside KiCad — "
            "the import guard is not working."
        )

    def test_jbom_plugin_is_standalone_flag_true_outside_kicad(self) -> None:
        """The ``_is_standalone`` sentinel must be True in test environments."""
        _ensure_pcbnew_absent()
        import jbom.plugin as _mod

        assert (
            _mod._is_standalone is True
        ), "_is_standalone should be True when pcbnew is absent."


# ---------------------------------------------------------------------------
# CLI independence
# ---------------------------------------------------------------------------


class TestCLIIndependenceFromKiCad:
    """Core jbom package is importable without KiCad or the plugin."""

    def test_jbom_importable(self) -> None:
        """``import jbom`` must work without KiCad installed."""
        _ensure_pcbnew_absent()
        import jbom

        assert jbom.__version__, "jbom.__version__ must be non-empty"

    def test_fabrication_workflow_importable(self) -> None:
        """``FabricationWorkflow`` must be importable from jbom.application."""
        from jbom.application.fabrication_orchestration import (
            FabricationRequest,
            FabricationWorkflow,
        )

        assert FabricationWorkflow is not None
        assert FabricationRequest is not None

    def test_job_contracts_importable(self) -> None:
        """Job contracts must be importable without KiCad."""
        from jbom.application.jobs.contracts import JobOutcome

        assert JobOutcome.SUCCEEDED.value == "succeeded"


# ---------------------------------------------------------------------------
# options.py independent importability
# ---------------------------------------------------------------------------


class TestOptionsModuleImportable:
    """options.py is importable without pcbnew or wx."""

    def test_options_importable_without_kicad(self) -> None:
        """``from jbom.plugin.options import PluginOptions`` must not raise."""
        _ensure_pcbnew_absent()
        from jbom.plugin.options import (
            PluginOptions,
            load_options,
            save_options,
        )  # noqa: F401

        assert PluginOptions is not None
        assert load_options is not None
        assert save_options is not None


# ---------------------------------------------------------------------------
# Vendor-folder tag selector (platform-aware bootstrap)
# ---------------------------------------------------------------------------


import pytest  # noqa: E402 — grouped with class below intentionally
import types  # noqa: E402


def _fake_version_info(major: int, minor: int, micro: int = 0) -> types.SimpleNamespace:
    """Build a stand-in for ``sys.version_info`` that exposes major/minor.

    ``sys.version_info`` is a ``structseq`` and cannot be constructed via the
    normal type call, so tests substitute a ``SimpleNamespace`` with the
    attributes our bootstrap actually reads.
    """
    return types.SimpleNamespace(major=major, minor=minor, micro=micro)


class TestVendorFolderTagSelector:
    """`_vendor_folder_tag` selects the right `<py>-<plat>` directory."""

    @pytest.mark.parametrize(
        "platform_name, machine, version_info, expected",
        [
            ("darwin", "arm64", (3, 9, 13), "cp39-macosx_arm64"),
            ("darwin", "x86_64", (3, 9, 13), "cp39-macosx_x86_64"),
            ("darwin", "arm64", (3, 12, 1), "cp312-macosx_arm64"),
            ("linux", "x86_64", (3, 9, 18), "cp39-manylinux_x86_64"),
            ("linux", "aarch64", (3, 12, 2), "cp312-manylinux_aarch64"),
            ("win32", "AMD64", (3, 9, 13), "cp39-win_amd64"),
            ("win32", "AMD64", (3, 12, 1), "cp312-win_amd64"),
        ],
    )
    def test_known_targets_select_expected_folder(
        self,
        monkeypatch: pytest.MonkeyPatch,
        platform_name: str,
        machine: str,
        version_info: tuple[int, int, int],
        expected: str,
    ) -> None:
        """Each supported (py, os, arch) combo maps to its vendor folder."""
        import platform as _platform

        import jbom.plugin as _mod

        monkeypatch.setattr(_mod.sys, "platform", platform_name)
        monkeypatch.setattr(_mod.sys, "version_info", _fake_version_info(*version_info))
        monkeypatch.setattr(_platform, "machine", lambda: machine)
        assert _mod._vendor_folder_tag() == expected

    def test_unsupported_platform_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Solaris/BSD/etc. are not in the supported matrix and return None."""
        import platform as _platform

        import jbom.plugin as _mod

        monkeypatch.setattr(_mod.sys, "platform", "sunos5")
        monkeypatch.setattr(_platform, "machine", lambda: "sparc")
        assert _mod._vendor_folder_tag() is None

    def test_pydantic_core_path_returns_none_when_vendor_missing(
        self, tmp_path
    ) -> None:
        """Absent ``_vendor/`` directory yields None, not a crash."""
        import jbom.plugin as _mod

        assert _mod._vendor_pydantic_core_path(tmp_path) is None

    def test_pydantic_core_path_prefers_exact_tag_match(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Exact `<tag>` directory wins over the fallback scan."""
        import platform as _platform

        import jbom.plugin as _mod

        monkeypatch.setattr(_mod.sys, "platform", "darwin")
        monkeypatch.setattr(_mod.sys, "version_info", _fake_version_info(3, 9, 13))
        monkeypatch.setattr(_platform, "machine", lambda: "arm64")

        vendor = tmp_path / "_vendor" / "pydantic_core"
        good = vendor / "cp39-macosx_arm64" / "pydantic_core"
        good.mkdir(parents=True)
        (good / "__init__.py").write_text("", encoding="utf-8")
        # A wrong-target dir must NOT be picked when the exact tag exists.
        wrong = vendor / "cp312-win_amd64" / "pydantic_core"
        wrong.mkdir(parents=True)
        (wrong / "__init__.py").write_text("", encoding="utf-8")

        result = _mod._vendor_pydantic_core_path(tmp_path)
        assert result == vendor / "cp39-macosx_arm64"

    def test_pydantic_core_path_falls_back_to_local_dir(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`--skip-binary-fetch` builds use a ``local_*`` folder; we still pick it."""
        import platform as _platform

        import jbom.plugin as _mod

        monkeypatch.setattr(_mod.sys, "platform", "darwin")
        monkeypatch.setattr(_mod.sys, "version_info", _fake_version_info(3, 9, 13))
        # Force tag lookup to miss by reporting an arch we did not vendor.
        monkeypatch.setattr(_platform, "machine", lambda: "riscv64")

        local = (
            tmp_path
            / "_vendor"
            / "pydantic_core"
            / "cp39-local_darwin"
            / "pydantic_core"
        )
        local.mkdir(parents=True)
        (local / "__init__.py").write_text("", encoding="utf-8")
        result = _mod._vendor_pydantic_core_path(tmp_path)
        assert result == local.parent
