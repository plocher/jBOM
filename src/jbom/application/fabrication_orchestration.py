"""Adapter-neutral fabrication workflow orchestration.

Sequences three fabrication steps in order:

1. BOM generation — delegates to :class:`~jbom.application.bom_orchestration.BOMOrchestrationService`.
2. POS (placement) generation — delegates to :class:`~jbom.application.pos_orchestration.POSOrchestrationService`.
3. Gerber/drill/netlist export — delegates to :class:`~jbom.services.gerber_service.GerberExporter`.

Each step is independently skip-able.  If Gerbers cannot be generated
(``kicad-cli`` absent, PCB file missing, or ``dry_run=True``) the workflow
still succeeds and returns BOM/POS results — the ``gerber_result`` payload
carries a diagnostic and ``skipped=True``.

The :class:`FabricationWorkflow` is an adapter-neutral application service:
it contains no CLI concerns (no argparse, no stdout, no exit codes).  Adapter
layers (CLI, plugin) are responsible for rendering results and writing CSV
files from the BOM/POS payloads.

Naming convention:
  New code in this module follows the naming convention established in #224:
  class names reflect the *promise* (what is produced), not the mechanism.
  The existing ``BOMOrchestrationService`` / ``POSOrchestrationService`` names
  are unchanged here — renaming them is tracked in issue #237.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from jbom.application.bom_orchestration import (
    BOMOrchestrationRequest,
    BOMOrchestrationResult,
    BOMOrchestrationService,
)
from jbom.application.pos_orchestration import (
    POSOrchestrationRequest,
    POSOrchestrationResult,
    POSOrchestrationService,
)
from jbom.services.gerber_service import GerberExporter, GerberRequest, GerberResult

__all__ = [
    "FabricationArtifact",
    "FabricationRequest",
    "FabricationResult",
    "FabricationWorkflow",
]


def _freeze_mapping(values: Mapping[str, Any] | None) -> Mapping[str, Any]:
    """Return an immutable copy of a metadata mapping."""
    return MappingProxyType(dict(values or {}))


def _normalize_text(value: str, *, field_name: str) -> str:
    """Validate and normalise a required non-empty text field."""
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty")
    return normalized


@dataclass(frozen=True)
class FabricationRequest:
    """Adapter-neutral request for the fabrication workflow.

    Attributes:
        input_path: Path to the KiCad project directory, ``.kicad_pro``,
            ``.kicad_pcb``, or ``.kicad_sch`` file.  Passed unchanged to
            BOM and POS orchestration services.
        fabricator: Fabricator profile identifier (e.g. ``"jlc"``, ``"generic"``).
            Controls default field sets for both BOM and POS outputs.
            Field customisation beyond fabricator defaults requires using
            ``jbom bom`` and ``jbom pos`` individually.
        output_directory: If non-empty, Gerbers are written to
            ``<output_directory>/gerbers/``.  BOM/POS default output paths
            come from their respective orchestration results; adapter layers
            may override them.
        skip_bom: When ``True`` skip BOM generation entirely.
        skip_pos: When ``True`` skip POS generation entirely.
        skip_gerbers: When ``True`` skip Gerber/drill/netlist generation.
        verbose: Forward verbose flag to sub-services.
        dry_run: When ``True`` generate BOM/POS data but skip Gerber file
            generation (no filesystem writes for Gerbers).
        inventory_files: Inventory CSV paths forwarded to BOM generation.
        smd_only: Forward SMD-only filter to POS generation.
        pos_layer: Forward layer filter (``"TOP"`` / ``"BOTTOM"``) to POS.
        pos_origin: Forward origin reference (``"board"`` / ``"aux"``) to POS.
    """

    input_path: str
    fabricator: str = "generic"
    output_directory: str = ""
    skip_bom: bool = False
    skip_pos: bool = False
    skip_gerbers: bool = False
    verbose: bool = False
    dry_run: bool = False
    inventory_files: tuple[str, ...] = field(default_factory=tuple)
    smd_only: bool = False
    pos_layer: str = ""
    pos_origin: str = "board"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "input_path",
            _normalize_text(self.input_path, field_name="input_path"),
        )
        object.__setattr__(
            self,
            "fabricator",
            _normalize_text(self.fabricator or "generic", field_name="fabricator"),
        )
        object.__setattr__(
            self, "output_directory", str(self.output_directory or "").strip()
        )
        object.__setattr__(self, "skip_bom", bool(self.skip_bom))
        object.__setattr__(self, "skip_pos", bool(self.skip_pos))
        object.__setattr__(self, "skip_gerbers", bool(self.skip_gerbers))
        object.__setattr__(self, "verbose", bool(self.verbose))
        object.__setattr__(self, "dry_run", bool(self.dry_run))
        object.__setattr__(
            self,
            "inventory_files",
            tuple(str(p) for p in self.inventory_files),
        )
        object.__setattr__(self, "smd_only", bool(self.smd_only))
        object.__setattr__(self, "pos_layer", str(self.pos_layer or "").strip())
        object.__setattr__(
            self,
            "pos_origin",
            _normalize_text(self.pos_origin or "board", field_name="pos_origin"),
        )


@dataclass(frozen=True)
class FabricationArtifact:
    """Descriptor for one fabrication artifact produced by the workflow.

    Attributes:
        artifact_type: Semantic type token: ``"bom"``, ``"pos"``,
            ``"gerber"``, ``"drill"``, or ``"netlist"``.
        path: Filesystem path where the artifact resides.  For BOM/POS this
            is the orchestration default path; adapter layers may redirect
            actual writes to a different location.  For Gerbers this is the
            actual written path (Gerber generation is handled inside the
            workflow).
        media_type: MIME type string (e.g. ``"text/csv"``).
    """

    artifact_type: str
    path: Path | None
    media_type: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "artifact_type",
            _normalize_text(self.artifact_type, field_name="artifact_type"),
        )
        if self.path is not None:
            object.__setattr__(self, "path", Path(self.path))
        object.__setattr__(self, "media_type", str(self.media_type or "").strip())


@dataclass(frozen=True)
class FabricationResult:
    """Result produced by :class:`FabricationWorkflow`.

    Attributes:
        artifacts: All artifact descriptors produced during the workflow.
            BOM/POS entries carry default output paths; Gerber entries carry
            actual written paths.
        diagnostics: Ordered human-readable messages from all sub-services.
        bom_result: Full BOM orchestration result (``None`` when skipped).
        pos_result: Full POS orchestration result (``None`` when skipped).
        gerber_result: Gerber generation result (``None`` when skipped).
    """

    artifacts: tuple[FabricationArtifact, ...]
    diagnostics: tuple[str, ...]
    bom_result: BOMOrchestrationResult | None = None
    pos_result: POSOrchestrationResult | None = None
    gerber_result: GerberResult | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifacts", tuple(self.artifacts))
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))


class FabricationWorkflow:
    """Adapter-neutral fabrication workflow: sequences BOM → POS → Gerbers.

    Calls existing orchestration services and ``GerberExporter`` in order.
    Each step is gated by its ``skip_*`` flag.  Failures in one step are
    captured as diagnostics and do not abort subsequent steps (except that a
    missing PCB file prevents Gerber generation).

    This class contains no CLI or UI concerns.
    """

    def run(self, request: FabricationRequest) -> FabricationResult:
        """Execute the fabrication workflow and return all results.

        Args:
            request: Options governing which steps to run and with what inputs.

        Returns:
            :class:`FabricationResult` aggregating BOM, POS, and Gerber outputs.
        """
        diagnostics: list[str] = []
        artifacts: list[FabricationArtifact] = []
        bom_result: BOMOrchestrationResult | None = None
        pos_result: POSOrchestrationResult | None = None
        gerber_result: GerberResult | None = None

        # ------------------------------------------------------------------
        # Step 1: BOM
        # ------------------------------------------------------------------
        if not request.skip_bom:
            bom_result, bom_diagnostics = self._run_bom(request)
            diagnostics.extend(bom_diagnostics)
            if bom_result is not None and bom_result.generation is not None:
                artifacts.append(
                    FabricationArtifact(
                        artifact_type="bom",
                        path=bom_result.generation.default_output_path,
                        media_type="text/csv",
                    )
                )

        # ------------------------------------------------------------------
        # Step 2: POS
        # ------------------------------------------------------------------
        if not request.skip_pos:
            pos_result, pos_diagnostics = self._run_pos(request)
            diagnostics.extend(pos_diagnostics)
            if pos_result is not None and pos_result.generation is not None:
                artifacts.append(
                    FabricationArtifact(
                        artifact_type="pos",
                        path=pos_result.generation.default_output_path,
                        media_type="text/csv",
                    )
                )

        # ------------------------------------------------------------------
        # Step 3: Gerbers (skipped in dry_run mode)
        # ------------------------------------------------------------------
        if not request.skip_gerbers:
            if request.dry_run:
                diagnostics.append(
                    "Dry run: Gerber generation skipped (no files written)."
                )
            else:
                gerber_result, gerber_diagnostics = self._run_gerbers(request)
                diagnostics.extend(gerber_diagnostics)
                if gerber_result is not None and not gerber_result.skipped:
                    for artifact_path in gerber_result.artifacts:
                        # Infer type from extension; default to "gerber"
                        ext = artifact_path.suffix.lower()
                        artifact_type = (
                            "drill"
                            if ext == ".drl"
                            else "netlist"
                            if ext == ".ipc"
                            else "gerber"
                        )
                        artifacts.append(
                            FabricationArtifact(
                                artifact_type=artifact_type,
                                path=artifact_path,
                                media_type=_media_type_for(artifact_type),
                            )
                        )

        return FabricationResult(
            artifacts=tuple(artifacts),
            diagnostics=tuple(diagnostics),
            bom_result=bom_result,
            pos_result=pos_result,
            gerber_result=gerber_result,
        )

    # ------------------------------------------------------------------
    # Private step runners
    # ------------------------------------------------------------------

    def _run_bom(
        self, request: FabricationRequest
    ) -> tuple[BOMOrchestrationResult | None, list[str]]:
        """Run BOM orchestration and return result + diagnostics."""
        diagnostics: list[str] = []
        try:
            bom_request = BOMOrchestrationRequest(
                input_path=request.input_path,
                fabricator=request.fabricator,
                inventory_files=request.inventory_files,
                verbose=request.verbose,
            )
            result = BOMOrchestrationService().orchestrate(bom_request)
            diagnostics.extend(result.diagnostics)
            return result, diagnostics
        except Exception as exc:
            diagnostics.append(f"BOM generation failed: {exc}")
            return None, diagnostics

    def _run_pos(
        self, request: FabricationRequest
    ) -> tuple[POSOrchestrationResult | None, list[str]]:
        """Run POS orchestration and return result + diagnostics."""
        diagnostics: list[str] = []
        try:
            pos_request = POSOrchestrationRequest(
                input_path=request.input_path,
                fabricator=request.fabricator,
                smd_only=request.smd_only,
                layer=request.pos_layer,
                origin=request.pos_origin,
                verbose=request.verbose,
            )
            result = POSOrchestrationService().orchestrate(pos_request)
            diagnostics.extend(result.diagnostics)
            return result, diagnostics
        except Exception as exc:
            diagnostics.append(f"POS generation failed: {exc}")
            return None, diagnostics

    def _run_gerbers(
        self, request: FabricationRequest
    ) -> tuple[GerberResult | None, list[str]]:
        """Resolve PCB file and run GerberExporter."""
        diagnostics: list[str] = []

        pcb_file, project_dir, resolve_diags = self._resolve_pcb_and_project_dir(
            request
        )
        diagnostics.extend(resolve_diags)

        if pcb_file is None:
            diagnostics.append(
                "Gerber generation skipped: PCB file could not be resolved "
                "from the given input path."
            )
            return None, diagnostics

        gerber_dir = self._resolve_gerber_output_dir(request, project_dir)
        gerber_request = GerberRequest(
            pcb_file=pcb_file,
            output_directory=gerber_dir,
            fabricator=request.fabricator,
        )
        try:
            result = GerberExporter().generate(gerber_request)
            return result, diagnostics
        except Exception as exc:
            diagnostics.append(f"Gerber generation failed unexpectedly: {exc}")
            return None, diagnostics

    def _resolve_pcb_and_project_dir(
        self, request: FabricationRequest
    ) -> tuple[Path | None, Path | None, list[str]]:
        """Resolve PCB file path and project directory from input_path.

        Returns:
            ``(pcb_file, project_directory, diagnostics)``
        """
        diagnostics: list[str] = []
        try:
            from jbom.services.project_file_resolver import ProjectFileResolver

            resolver = ProjectFileResolver(prefer_pcb=True, target_file_type="pcb")
            resolved = resolver.resolve_input(request.input_path)
            if not resolved.is_pcb:
                resolved = resolver.resolve_for_wrong_file_type(resolved, "pcb")
            pcb_file = resolved.resolved_path
            project_dir: Path | None = None
            if resolved.project_context:
                project_dir = resolved.project_context.project_directory
            if project_dir is None:
                project_dir = pcb_file.parent
            return pcb_file, project_dir, diagnostics
        except Exception as exc:
            if request.verbose:
                diagnostics.append(f"Note: could not resolve PCB file: {exc}")
            return None, None, diagnostics

    def _resolve_gerber_output_dir(
        self, request: FabricationRequest, project_dir: Path | None
    ) -> Path:
        """Return the directory where Gerber files should be written."""
        if request.output_directory:
            return Path(request.output_directory) / "gerbers"
        if project_dir is not None:
            return project_dir / "gerbers"
        return Path("gerbers")


def _media_type_for(artifact_type: str) -> str:
    """Return MIME type string for a fabrication artifact type token."""
    mapping = {
        "bom": "text/csv",
        "pos": "text/csv",
        "gerber": "application/x-gerber",
        "drill": "application/x-excellon",
        "netlist": "text/plain",
    }
    return mapping.get(artifact_type, "application/octet-stream")
