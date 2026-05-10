"""Adapter-neutral fabrication workflow orchestration.

Sequences three fabrication steps in order:

1. BOM generation — delegates to :class:`~jbom.application.bom_workflow.BOMWorkflow`.
2. POS (placement) generation — delegates to :class:`~jbom.application.pos_workflow.POSWorkflow`.
3. Gerber/drill/netlist export — delegates to :class:`~jbom.services.gerber_service.GerberExporter`.

Each step is independently skip-able.  If Gerbers cannot be generated
(``kicad-cli`` absent, PCB file missing, or ``dry_run=True``) the workflow
still succeeds and returns BOM/POS results — the ``gerber_result`` payload
carries a diagnostic and ``skipped=True``.

The :class:`FabricationWorkflow` is an adapter-neutral application service:
it contains no CLI concerns (no argparse, no stdout, no exit codes).  File I/O
for BOM and POS artifacts is handled inside the workflow via friend serializers
(``BOMWriter``, ``POSWriter``).  Adapter layers (CLI, plugin) receive the result
and render paths and diagnostics.

Naming convention:
  New code in this module follows the naming convention established in #224:
  class names reflect the *promise* (what is produced), not the mechanism.
  The existing ``BOMWorkflow`` / ``POSWorkflow`` names
  are unchanged here — renaming them is tracked in issue #237.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping

from jbom.application.bom_workflow import (
    BOMRequest,
    BOMResult,
    BOMWorkflow,
)
from jbom.application.pos_workflow import (
    POSRequest,
    POSResult,
    POSWorkflow,
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
        output_directory: Legacy option; kept for backward compatibility.
            Deprecated in favor of ``production_root``.
        production_root: Parent directory for the ``production/`` folder.
            When set, takes precedence over ``output_directory``.  If empty,
            defaults to the project directory.
        skip_bom: When ``True`` skip BOM generation entirely.
        skip_pos: When ``True`` skip POS generation entirely.
        skip_gerbers: When ``True`` skip Gerber/drill/netlist generation.
        verbose: Forward verbose flag to sub-services.
        dry_run: When ``True`` generate BOM/POS data but skip all file writes.
        inventory_files: Inventory CSV paths forwarded to BOM generation.
        smd_only: Forward SMD-only filter to POS generation.
        pos_layer: Forward layer filter (``"TOP"`` / ``"BOTTOM"``) to POS.
        pos_origin: Forward origin reference (``"board"`` / ``"aux"``) to POS.
        skip_backup: When ``True`` skip backup archive creation even when
            artifacts are present.  Defaults to ``False`` (backup is created).
        debug: When ``True`` preserve intermediate gerber directory after
            packaging for inspection.
        archive_stem: Pre-expanded archive base name (e.g. ``"MyBoard_1.0"``)
            used as the stem for the gerber zip and backup archives.  When
            non-empty, the workflow uses this value directly without reading
            the project metadata from disk.  Adapters that have access to the
            live board (e.g. the KiCad plugin) should pre-expand text variables
            and pass the result here; CLI adapters may leave this empty to let
            the workflow derive it from ``ProjectMetadata``.
    """

    input_path: str
    fabricator: str = "generic"
    output_directory: str = ""
    production_root: str = ""
    skip_bom: bool = False
    skip_pos: bool = False
    skip_gerbers: bool = False
    verbose: bool = False
    dry_run: bool = False
    inventory_files: tuple[str, ...] = field(default_factory=tuple)
    smd_only: bool = False
    pos_layer: str = ""
    pos_origin: str = "board"
    skip_backup: bool = False
    debug: bool = False
    archive_stem: str = ""

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
        object.__setattr__(
            self, "production_root", str(self.production_root or "").strip()
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
        object.__setattr__(self, "skip_backup", bool(self.skip_backup))
        object.__setattr__(self, "debug", bool(self.debug))
        object.__setattr__(self, "archive_stem", str(self.archive_stem or "").strip())


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
            Includes BOM, POS, packaged Gerbers, and backups written to
            the production folder.
        diagnostics: Ordered human-readable messages from all sub-services.
        bom_result: Full BOM orchestration result (``None`` when skipped).
        pos_result: Full POS orchestration result (``None`` when skipped).
        gerber_result: Gerber generation result (``None`` when skipped).
        production_dir: Path to the ``production/`` directory that was
            created and populated, or ``None`` if skipped/failed.
        backup_archive: Path to the dated backup archive created under
            ``production/backups/``, or ``None`` if none was created.
    """

    artifacts: tuple[FabricationArtifact, ...]
    diagnostics: tuple[str, ...]
    bom_result: BOMResult | None = None
    pos_result: POSResult | None = None
    gerber_result: GerberResult | None = None
    production_dir: Path | None = None
    backup_archive: Path | None = None

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

    def run(
        self,
        request: FabricationRequest,
        *,
        step_callback: Callable[[str, str], None] | None = None,
    ) -> FabricationResult:
        """Execute the fabrication workflow and return all results.

        Args:
            request: Options governing which steps to run and with what inputs.
            step_callback: Optional notification sink invoked at each step
                boundary.  Signature: ``callback(step: str, status: str)``
                where *step* is one of ``"bom"``, ``"pos"``, ``"gerbers"``,
                ``"backup"`` and *status* is ``"start"`` or ``"done"``.

                This is a naked ``Callable`` — the workflow has no knowledge of
                wx, asyncio, or any specific event loop.  Each adapter is
                responsible for its own dispatch:

                - **Plugin adapter** passes a lambda that calls
                  ``wx.CallAfter(dialog.on_step, step, status)`` so that UI
                  updates are safely dispatched to the main thread.
                - **CLI adapter** currently passes ``None``.  A future
                  ``--verbose`` / ``--progress`` flag would pass
                  ``lambda step, status: print(f"{step}: {status}")``
                  instead — the contract already supports this without any
                  changes to this method.

                The callback is invoked from the **same thread** that calls
                :meth:`run`; callers in a background thread must dispatch
                UI updates themselves (e.g. via ``wx.CallAfter``).

        Returns:
            :class:`FabricationResult` aggregating BOM, POS, and Gerber outputs,
            with all files written to the production/ directory when appropriate.
        """
        diagnostics: list[str] = []
        artifacts: list[FabricationArtifact] = []
        bom_result: BOMResult | None = None
        pos_result: POSResult | None = None
        gerber_result: GerberResult | None = None
        production_dir: Path | None = None
        backup_archive: Path | None = None

        # Resolve project directory for production folder location
        _, project_dir, resolve_diags = self._resolve_pcb_and_project_dir(request)
        diagnostics.extend(resolve_diags)

        # Determine production root and create production directory
        production_root = self._resolve_production_root(request, project_dir)
        if not request.dry_run:
            production_dir = production_root / "production"
            try:
                production_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                diagnostics.append(f"Failed to create production directory: {exc}")
                return FabricationResult(
                    artifacts=tuple(artifacts),
                    diagnostics=tuple(diagnostics),
                    bom_result=bom_result,
                    pos_result=pos_result,
                    gerber_result=gerber_result,
                    production_dir=None,
                    backup_archive=None,
                )

        # ------------------------------------------------------------------
        # Step 1: BOM
        # ------------------------------------------------------------------
        if not request.skip_bom:
            if step_callback:
                step_callback("bom", "start")
            bom_result, bom_diagnostics = self._run_bom(request)
            diagnostics.extend(bom_diagnostics)
            if step_callback:
                step_callback("bom", "done")
            if bom_result is not None and bom_result.generation is not None:
                bom_path = None
                if not request.dry_run and production_dir is not None:
                    # Write BOM to production/jbom.csv
                    bom_path = production_dir / "jbom.csv"
                    try:
                        from jbom.services.bom_writer import BOMWriter

                        BOMWriter.write(bom_result.generation, bom_path, force=True)
                    except Exception as exc:
                        diagnostics.append(f"BOM write failed: {exc}")
                        bom_path = None
                else:
                    bom_path = bom_result.generation.default_output_path

                if bom_path is not None:
                    artifacts.append(
                        FabricationArtifact(
                            artifact_type="bom",
                            path=bom_path,
                            media_type="text/csv",
                        )
                    )

        # ------------------------------------------------------------------
        # Step 2: POS
        # ------------------------------------------------------------------
        if not request.skip_pos:
            if step_callback:
                step_callback("pos", "start")
            pos_result, pos_diagnostics = self._run_pos(request)
            diagnostics.extend(pos_diagnostics)
            if step_callback:
                step_callback("pos", "done")
            if pos_result is not None and pos_result.generation is not None:
                pos_path = None
                if not request.dry_run and production_dir is not None:
                    # Write POS to production/cpl.csv
                    pos_path = production_dir / "cpl.csv"
                    try:
                        from jbom.services.pos_writer import POSWriter

                        POSWriter.write(pos_result.generation, pos_path, force=True)
                    except Exception as exc:
                        diagnostics.append(f"POS write failed: {exc}")
                        pos_path = None
                else:
                    pos_path = pos_result.generation.default_output_path

                if pos_path is not None:
                    artifacts.append(
                        FabricationArtifact(
                            artifact_type="pos",
                            path=pos_path,
                            media_type="text/csv",
                        )
                    )

        # ------------------------------------------------------------------
        # Step 3: Gerbers (skipped in dry_run mode)
        # ------------------------------------------------------------------
        if not request.skip_gerbers:
            if step_callback:
                step_callback("gerbers", "start")
            if request.dry_run:
                diagnostics.append(
                    "Dry run: Gerber generation skipped (no files written)."
                )
            else:
                (
                    gerber_artifacts,
                    gerber_result,
                    gerber_packaging_diags,
                ) = self._run_gerbers_with_packaging(request, production_dir)
                diagnostics.extend(gerber_packaging_diags)
                artifacts.extend(gerber_artifacts)
            if step_callback:
                step_callback("gerbers", "done")

        # ------------------------------------------------------------------
        # Step 4: Backup (if any files were written and not skipped by caller)
        # ------------------------------------------------------------------
        if (
            not request.skip_backup
            and not request.dry_run
            and production_dir is not None
            and artifacts
        ):
            artifact_paths = [a.path for a in artifacts if a.path is not None]
            if artifact_paths:
                if step_callback:
                    step_callback("backup", "start")
                backup_archive, backup_diags = self._create_backup(
                    request, artifact_paths, production_dir
                )
                diagnostics.extend(backup_diags)
                if step_callback:
                    step_callback("backup", "done")
                if backup_archive is not None:
                    artifacts.append(
                        FabricationArtifact(
                            artifact_type="backup",
                            path=backup_archive,
                            media_type="application/zip",
                        )
                    )

        return FabricationResult(
            artifacts=tuple(artifacts),
            diagnostics=tuple(diagnostics),
            bom_result=bom_result,
            pos_result=pos_result,
            gerber_result=gerber_result,
            production_dir=production_dir,
            backup_archive=backup_archive,
        )

    # ------------------------------------------------------------------
    # Private step runners
    # ------------------------------------------------------------------

    def _run_bom(
        self, request: FabricationRequest
    ) -> tuple[BOMResult | None, list[str]]:
        """Run BOM orchestration and return result + diagnostics."""
        diagnostics: list[str] = []
        try:
            bom_request = BOMRequest(
                input_path=request.input_path,
                fabricator=request.fabricator,
                inventory_files=request.inventory_files,
                verbose=request.verbose,
            )
            result = BOMWorkflow().run(bom_request)
            diagnostics.extend(result.diagnostics)
            return result, diagnostics
        except Exception as exc:
            diagnostics.append(f"BOM generation failed: {exc}")
            return None, diagnostics

    def _run_pos(
        self, request: FabricationRequest
    ) -> tuple[POSResult | None, list[str]]:
        """Run POS orchestration and return result + diagnostics."""
        diagnostics: list[str] = []
        try:
            pos_request = POSRequest(
                input_path=request.input_path,
                fabricator=request.fabricator,
                smd_only=request.smd_only,
                layer=request.pos_layer,
                origin=request.pos_origin,
                verbose=request.verbose,
            )
            result = POSWorkflow().run(pos_request)
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

    def _resolve_archive_stem(
        self,
        request: FabricationRequest,
        project_dir: Path | None,
        pcb_file: Path | None,
    ) -> str:
        """Return the archive base name for gerber zip and backup archives.

        When ``request.archive_stem`` is non-empty it is used directly (caller
        has pre-expanded any text variables).  Otherwise the stem is derived
        from :func:`~jbom.services.project_metadata.create_metadata` using the
        project directory and PCB file.
        """
        if request.archive_stem:
            return request.archive_stem
        try:
            from jbom.services.project_metadata import (
                create_metadata,
                normalize_archive_stem,
            )

            effective_project_dir = project_dir or (
                pcb_file.parent if pcb_file else None
            )
            if effective_project_dir is None:
                return "jbom-production"
            project_file = (
                effective_project_dir / f"{effective_project_dir.name}.kicad_pro"
            )
            metadata = create_metadata(project_file, pcb_file=pcb_file)
            return normalize_archive_stem(metadata.project_name) or "jbom-production"
        except Exception:
            return "jbom-production"

    def _resolve_production_root(
        self, request: FabricationRequest, project_dir: Path | None
    ) -> Path:
        """Determine the parent directory for the production/ folder.

        production_root takes precedence over output_directory; both default
        to the project directory.
        """
        if request.production_root:
            return Path(request.production_root)
        if request.output_directory:
            return Path(request.output_directory)
        if project_dir is not None:
            return project_dir
        return Path(".")

    def _run_gerbers_with_packaging(
        self,
        request: FabricationRequest,
        production_dir: Path | None,
    ) -> tuple[list[FabricationArtifact], GerberResult | None, list[str]]:
        """Generate Gerbers to temp dir, package to production/, return artifacts.

        Returns:
            ``(artifacts, gerber_result, diagnostics)`` where artifacts are
            FabricationArtifacts for the packaged gerber archive and
            gerber_result carries the raw GerberExporter result for diagnostics.
        """
        artifacts: list[FabricationArtifact] = []
        diagnostics: list[str] = []
        gerber_result: GerberResult | None = None

        if production_dir is None:
            diagnostics.append("Production dir not available for gerber packaging.")
            return artifacts, gerber_result, diagnostics

        # Generate gerbers to a temporary directory
        pcb_file, project_dir, resolve_diags = self._resolve_pcb_and_project_dir(
            request
        )
        diagnostics.extend(resolve_diags)

        if pcb_file is None:
            return artifacts, gerber_result, diagnostics

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_gerber_dir = Path(temp_dir) / "gerbers"
                gerber_request = GerberRequest(
                    pcb_file=pcb_file,
                    output_directory=temp_gerber_dir,
                    fabricator=request.fabricator,
                )
                gerber_result = GerberExporter().generate(gerber_request)

                if gerber_result is None or gerber_result.skipped:
                    diagnostics.append(
                        "Gerber generation skipped or failed; no artifacts to package."
                    )
                    return artifacts, gerber_result, diagnostics

                # Resolve archive stem (honours request.archive_stem override)
                archive_stem = self._resolve_archive_stem(
                    request, project_dir, pcb_file
                )

                # Package gerbers with GerberPackager
                from jbom.services.gerber_packager import GerberPackager

                packager = GerberPackager()
                gerber_zip = production_dir / f"{archive_stem}.zip"
                try:
                    packager.package(
                        gerber_result.artifacts,
                        gerber_zip,
                        debug=request.debug,
                    )
                    artifacts.append(
                        FabricationArtifact(
                            artifact_type="gerber",
                            path=gerber_zip,
                            media_type="application/zip",
                        )
                    )
                except Exception as exc:
                    diagnostics.append(f"Gerber packaging failed: {exc}")

        except Exception as exc:
            diagnostics.append(f"Gerber generation or packaging failed: {exc}")

        return artifacts, gerber_result, diagnostics

    def _create_backup(
        self,
        request: FabricationRequest,
        artifact_paths: list[Path],
        production_dir: Path,
    ) -> tuple[Path | None, list[str]]:
        """Create a dated backup archive of all production artifacts.

        Returns:
            ``(backup_archive_path, diagnostics)`` where backup_archive_path
            is None if backup creation failed.
        """
        diagnostics: list[str] = []

        try:
            from jbom.services.backup_service import BackupService

            # Resolve project files for archive naming
            pcb_file, project_dir, resolve_diags = self._resolve_pcb_and_project_dir(
                request
            )
            diagnostics.extend(resolve_diags)

            if project_dir is None:
                project_dir = production_dir.parent

            archive_stem = self._resolve_archive_stem(request, project_dir, pcb_file)

            backup_service = BackupService()
            backup_dir = production_dir / "backups"
            backup_archive = backup_service.backup(
                artifact_paths,
                backup_dir,
                archive_stem,
            )
            return backup_archive, diagnostics

        except Exception as exc:
            diagnostics.append(f"Backup creation failed: {exc}")
            return None, diagnostics

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
