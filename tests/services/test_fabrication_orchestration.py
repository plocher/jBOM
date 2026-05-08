"""Service-level tests for FabricationWorkflow (issue #224).

Covers:
- FabricationRequest validation (empty input_path raises)
- FabricationWorkflow.run with all steps skipped → empty result
- BOM step skipped when skip_bom=True
- POS step skipped when skip_pos=True
- Gerber step skipped when skip_gerbers=True
- Gerber step skipped in dry_run mode with diagnostic
- Fabricator propagated to BOM and POS sub-services
- Sub-service failures captured as diagnostics, not exceptions
- FabricationResult structure: artifacts, diagnostics, sub-results
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from jbom.application.fabrication_orchestration import (
    FabricationRequest,
    FabricationResult,
    FabricationWorkflow,
)


# ---------------------------------------------------------------------------
# FabricationRequest validation
# ---------------------------------------------------------------------------


class TestFabricationRequestValidation:
    def test_raises_when_input_path_empty(self) -> None:
        with pytest.raises(ValueError, match="input_path"):
            FabricationRequest(input_path="")

    def test_raises_when_input_path_whitespace(self) -> None:
        with pytest.raises(ValueError, match="input_path"):
            FabricationRequest(input_path="   ")

    def test_defaults_are_sane(self) -> None:
        req = FabricationRequest(input_path=".")
        assert req.fabricator == "generic"
        assert req.skip_bom is False
        assert req.skip_pos is False
        assert req.skip_gerbers is False
        assert req.dry_run is False
        assert req.inventory_files == ()
        assert req.pos_origin == "board"

    def test_inventory_files_coerced_to_tuple(self) -> None:
        req = FabricationRequest(
            input_path=".",
            inventory_files=["a.csv", "b.csv"],  # type: ignore[arg-type]
        )
        assert req.inventory_files == ("a.csv", "b.csv")
        assert isinstance(req.inventory_files, tuple)


# ---------------------------------------------------------------------------
# All-skipped: empty result
# ---------------------------------------------------------------------------


class TestFabricationWorkflowAllSkipped:
    def test_all_skipped_returns_empty_artifacts(self) -> None:
        request = FabricationRequest(
            input_path=".",
            skip_bom=True,
            skip_pos=True,
            skip_gerbers=True,
        )
        result = FabricationWorkflow().run(request)
        assert result.artifacts == ()
        assert result.bom_result is None
        assert result.pos_result is None
        assert result.gerber_result is None

    def test_all_skipped_returns_empty_diagnostics(self) -> None:
        request = FabricationRequest(
            input_path=".",
            skip_bom=True,
            skip_pos=True,
            skip_gerbers=True,
        )
        result = FabricationWorkflow().run(request)
        assert result.diagnostics == ()


# ---------------------------------------------------------------------------
# Skip flags gate their respective services
# ---------------------------------------------------------------------------


class TestFabricationWorkflowSkipFlags:
    def test_skip_bom_does_not_call_bom_service(self) -> None:
        request = FabricationRequest(
            input_path=".",
            skip_bom=True,
            skip_pos=True,
            skip_gerbers=True,
        )
        with patch(
            "jbom.application.fabrication_orchestration.BOMWorkflow"
        ) as mock_bom:
            FabricationWorkflow().run(request)
            mock_bom.assert_not_called()

    def test_skip_pos_does_not_call_pos_service(self) -> None:
        request = FabricationRequest(
            input_path=".",
            skip_bom=True,
            skip_pos=True,
            skip_gerbers=True,
        )
        with patch(
            "jbom.application.fabrication_orchestration.POSWorkflow"
        ) as mock_pos:
            FabricationWorkflow().run(request)
            mock_pos.assert_not_called()

    def test_skip_gerbers_does_not_call_gerber_exporter(self) -> None:
        request = FabricationRequest(
            input_path=".",
            skip_bom=True,
            skip_pos=True,
            skip_gerbers=True,
        )
        with patch(
            "jbom.application.fabrication_orchestration.GerberExporter"
        ) as mock_gerber:
            FabricationWorkflow().run(request)
            mock_gerber.assert_not_called()


# ---------------------------------------------------------------------------
# dry_run skips Gerbers with a diagnostic
# ---------------------------------------------------------------------------


class TestFabricationWorkflowDryRun:
    def test_dry_run_skips_gerbers(self) -> None:
        request = FabricationRequest(
            input_path=".",
            skip_bom=True,
            skip_pos=True,
            dry_run=True,
        )
        with patch(
            "jbom.application.fabrication_orchestration.GerberExporter"
        ) as mock_gerber:
            result = FabricationWorkflow().run(request)
            mock_gerber.assert_not_called()

        assert result.gerber_result is None
        assert any("Dry run" in d for d in result.diagnostics)

    def test_dry_run_still_processes_bom(self) -> None:
        """dry_run=True should NOT block BOM generation (only Gerbers)."""
        bom_mock_result = SimpleNamespace(
            diagnostics=(),
            generation=SimpleNamespace(
                default_output_path=Path("/tmp/proj.bom.csv"),
                bom_data=SimpleNamespace(entries=[]),
                selected_fields=("reference",),
            ),
        )
        request = FabricationRequest(
            input_path=".",
            skip_pos=True,
            skip_gerbers=False,
            dry_run=True,
        )
        with (
            patch(
                "jbom.application.fabrication_orchestration.BOMWorkflow"
            ) as mock_bom_cls,
            patch(
                "jbom.application.fabrication_orchestration.GerberExporter"
            ) as mock_gerber,
        ):
            mock_bom_cls.return_value.run.return_value = bom_mock_result
            result = FabricationWorkflow().run(request)

        mock_bom_cls.return_value.run.assert_called_once()
        mock_gerber.assert_not_called()
        assert result.bom_result is bom_mock_result


# ---------------------------------------------------------------------------
# Fabricator propagation
# ---------------------------------------------------------------------------


class TestFabricationWorkflowFabricatorPropagation:
    def test_fabricator_forwarded_to_bom(self) -> None:
        bom_mock_result = SimpleNamespace(diagnostics=(), generation=None)
        pos_mock_result = SimpleNamespace(diagnostics=(), generation=None)

        request = FabricationRequest(
            input_path=".",
            fabricator="jlc",
            skip_gerbers=True,
        )
        captured_bom_requests = []
        captured_pos_requests = []

        def _capture_bom(req):
            captured_bom_requests.append(req)
            return bom_mock_result

        def _capture_pos(req):
            captured_pos_requests.append(req)
            return pos_mock_result

        with (
            patch(
                "jbom.application.fabrication_orchestration.BOMWorkflow"
            ) as mock_bom_cls,
            patch(
                "jbom.application.fabrication_orchestration.POSWorkflow"
            ) as mock_pos_cls,
        ):
            mock_bom_cls.return_value.run.side_effect = _capture_bom
            mock_pos_cls.return_value.run.side_effect = _capture_pos
            FabricationWorkflow().run(request)

        assert len(captured_bom_requests) == 1
        assert captured_bom_requests[0].fabricator == "jlc"
        assert len(captured_pos_requests) == 1
        assert captured_pos_requests[0].fabricator == "jlc"


# ---------------------------------------------------------------------------
# Sub-service failure captured as diagnostic
# ---------------------------------------------------------------------------


class TestFabricationWorkflowSubServiceFailure:
    def test_bom_failure_captured_as_diagnostic(self) -> None:
        request = FabricationRequest(
            input_path=".",
            skip_pos=True,
            skip_gerbers=True,
        )
        with patch(
            "jbom.application.fabrication_orchestration.BOMWorkflow"
        ) as mock_bom_cls:
            mock_bom_cls.return_value.run.side_effect = RuntimeError(
                "schematic not found"
            )
            result = FabricationWorkflow().run(request)

        assert result.bom_result is None
        assert any("BOM generation failed" in d for d in result.diagnostics)

    def test_pos_failure_captured_as_diagnostic(self) -> None:
        request = FabricationRequest(
            input_path=".",
            skip_bom=True,
            skip_gerbers=True,
        )
        with patch(
            "jbom.application.fabrication_orchestration.POSWorkflow"
        ) as mock_pos_cls:
            mock_pos_cls.return_value.run.side_effect = RuntimeError("pcb not found")
            result = FabricationWorkflow().run(request)

        assert result.pos_result is None
        assert any("POS generation failed" in d for d in result.diagnostics)


# ---------------------------------------------------------------------------
# FabricationResult structure
# ---------------------------------------------------------------------------


class TestFabricationResultStructure:
    def test_result_is_frozen(self) -> None:
        result = FabricationResult(artifacts=(), diagnostics=())
        with pytest.raises(Exception):
            result.diagnostics = ("mutated",)  # type: ignore[misc]

    def test_artifacts_tuple_coercion(self) -> None:
        from jbom.application.fabrication_orchestration import FabricationArtifact

        artifact = FabricationArtifact(
            artifact_type="bom",
            path=Path("/tmp/test.bom.csv"),
            media_type="text/csv",
        )
        result = FabricationResult(
            artifacts=[artifact],  # type: ignore[arg-type]
            diagnostics=(),
        )
        assert isinstance(result.artifacts, tuple)
        assert len(result.artifacts) == 1
