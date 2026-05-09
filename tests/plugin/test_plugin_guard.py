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
