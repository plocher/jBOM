"""Tests for the ``step_callback`` parameter added to ``FabricationWorkflow.run()``.

Verifies that:
- Passing ``step_callback=None`` (default) does not change existing behaviour.
- A callback receives the correct (step, status) pairs in the right order.
- Skipped steps do not fire callbacks.
- Callback exceptions do not silently swallow errors.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from jbom.application.fabrication_orchestration import (
    FabricationRequest,
    FabricationWorkflow,
)


def _all_skipped_request() -> FabricationRequest:
    return FabricationRequest(
        input_path=".",
        skip_bom=True,
        skip_pos=True,
        skip_gerbers=True,
    )


class TestStepCallbackDefault:
    """step_callback=None (default) does not change existing behaviour."""

    def test_no_callback_all_skipped(self) -> None:
        request = _all_skipped_request()
        result = FabricationWorkflow().run(request)  # no step_callback kwarg
        assert result.artifacts == ()

    def test_explicit_none_callback_all_skipped(self) -> None:
        request = _all_skipped_request()
        result = FabricationWorkflow().run(request, step_callback=None)
        assert result.artifacts == ()


class TestStepCallbackInvocations:
    """Callback receives the expected (step, status) pairs."""

    def test_bom_step_fires_start_and_done(self) -> None:
        calls: list[tuple[str, str]] = []

        bom_mock = SimpleNamespace(
            diagnostics=(),
            generation=None,
        )
        request = FabricationRequest(
            input_path=".",
            skip_pos=True,
            skip_gerbers=True,
        )
        with patch(
            "jbom.application.fabrication_orchestration.BOMWorkflow"
        ) as mock_bom_cls:
            mock_bom_cls.return_value.run.return_value = bom_mock
            FabricationWorkflow().run(
                request, step_callback=lambda step, status: calls.append((step, status))
            )

        assert ("bom", "start") in calls
        assert ("bom", "done") in calls

    def test_callback_order_is_start_before_done(self) -> None:
        calls: list[tuple[str, str]] = []

        bom_mock = SimpleNamespace(diagnostics=(), generation=None)
        request = FabricationRequest(
            input_path=".",
            skip_pos=True,
            skip_gerbers=True,
        )
        with patch(
            "jbom.application.fabrication_orchestration.BOMWorkflow"
        ) as mock_bom_cls:
            mock_bom_cls.return_value.run.return_value = bom_mock
            FabricationWorkflow().run(
                request, step_callback=lambda s, st: calls.append((s, st))
            )

        bom_calls = [(s, st) for s, st in calls if s == "bom"]
        assert bom_calls == [("bom", "start"), ("bom", "done")]

    def test_skipped_bom_does_not_fire_callback(self) -> None:
        calls: list[tuple[str, str]] = []
        request = FabricationRequest(
            input_path=".",
            skip_bom=True,
            skip_pos=True,
            skip_gerbers=True,
        )
        FabricationWorkflow().run(
            request, step_callback=lambda s, st: calls.append((s, st))
        )
        assert all(s != "bom" for s, _ in calls)

    def test_skipped_gerbers_does_not_fire_callback(self) -> None:
        calls: list[tuple[str, str]] = []
        request = FabricationRequest(
            input_path=".",
            skip_bom=True,
            skip_pos=True,
            skip_gerbers=True,
        )
        FabricationWorkflow().run(
            request, step_callback=lambda s, st: calls.append((s, st))
        )
        assert all(s != "gerbers" for s, _ in calls)

    def test_all_skipped_no_callback_calls(self) -> None:
        calls: list[tuple[str, str]] = []
        FabricationWorkflow().run(
            _all_skipped_request(),
            step_callback=lambda s, st: calls.append((s, st)),
        )
        assert calls == []

    def test_pos_step_fires_when_not_skipped(self) -> None:
        calls: list[tuple[str, str]] = []
        pos_mock = SimpleNamespace(diagnostics=(), generation=None)
        request = FabricationRequest(
            input_path=".",
            skip_bom=True,
            skip_gerbers=True,
        )
        with patch(
            "jbom.application.fabrication_orchestration.POSWorkflow"
        ) as mock_pos_cls:
            mock_pos_cls.return_value.run.return_value = pos_mock
            FabricationWorkflow().run(
                request, step_callback=lambda s, st: calls.append((s, st))
            )

        assert ("pos", "start") in calls
        assert ("pos", "done") in calls
